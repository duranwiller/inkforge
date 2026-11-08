"""Inkforge co-op: HTTP host + real-time room server (Python 3.10+, websockets 14+)."""
import asyncio
import json
import os
import re
import secrets
from pathlib import Path
from websockets.asyncio.server import serve
from websockets.http11 import Response
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed

ROOT = Path(__file__).resolve().parent
STORAGE = ROOT / 'rooms'
STORAGE.mkdir(exist_ok=True)
ROOMS = {}
COLORS = ['#b39aff', '#4adbbb', '#ffae65', '#77bbff', '#ff7aa8', '#f7d66c', '#b5dc88', '#e89cfa']
MAX_MESSAGE = 3_000_000

# Single-port HTTP + WebSocket host, compatible with one Cloudflare Tunnel.
# Never expose saved room JSON, the Python server source, or launcher files.
def serve_http(connection, request):
    import urllib.parse
    path = urllib.parse.urlsplit(request.path).path
    if path == '/ws':
        # The browser should send a WebSocket Upgrade request for this endpoint.
        return None
    if path in ('/', '/index.html'):
        body = (ROOT / 'index.html').read_bytes()
        return Response(200, 'OK', Headers([
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff'),
        ]), body)
    if path == '/favicon.ico':
        return Response(204, 'No Content', Headers([('Content-Length', '0')]), b'')
    return Response(404, 'Not Found', Headers([('Content-Type','text/plain; charset=utf-8')]), b'Not found')

def fresh_project():
    return {'width':2400, 'height':1600, 'title':'Shared Inkforge Canvas', 'layers':[]}

def load_room(code):
    if code in ROOMS: return ROOMS[code]
    path = STORAGE / (code + '.json')
    try:
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else fresh_project()
        assert isinstance(data['layers'], list) and len(data['layers']) <= 80
        assert data['width'] in range(64, 6001) and data['height'] in range(64, 6001)
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        data = fresh_project()
    room = {'project':data, 'clients':{}, 'active':{}}
    ROOMS[code] = room
    return room

def save_room(code):
    target = STORAGE / (code + '.json')
    tmp = STORAGE / (code + '.tmp')
    tmp.write_text(json.dumps(ROOMS[code]['project'], separators=(',', ':')), encoding='utf-8')
    os.replace(tmp, target)

def valid_point(p):
    return isinstance(p,dict) and all(isinstance(p.get(k),(float,int)) and abs(p[k])<100000 for k in ('x','y')) and isinstance(p.get('p'),(float,int)) and 0<=p['p']<=1

def valid_head(s):
    return (isinstance(s,dict) and isinstance(s.get('id'),str) and 0<len(s['id'])<=80
            and s.get('brush') in ('ink','pencil','marker','airbrush','paint','calligraphy','eraser')
            and isinstance(s.get('color'),str) and bool(re.fullmatch(r'#[0-9a-fA-F]{6}',s['color']))
            and isinstance(s.get('size'),(int,float)) and 0.1<=s['size']<=180
            and isinstance(s.get('opacity'),(int,float)) and 0<=s['opacity']<=1
            and isinstance(s.get('pressureSize'),bool) and isinstance(s.get('pressureOpacity'),bool))

def valid_stroke(st):
    return valid_head(st) and isinstance(st.get('points'),list) and 1<=len(st['points'])<=15000 and all(valid_point(p) for p in st['points'])

async def send(ws, msg):
    try: await ws.send(json.dumps(msg,separators=(',',':')))
    except ConnectionClosed: pass

async def broadcast(room, msg, skip=None):
    payload = json.dumps(msg,separators=(',',':'))
    clients = [ws for ws in room['clients'] if ws is not skip]
    if clients: await asyncio.gather(*(ws.send(payload) for ws in clients),return_exceptions=True)

def members(room):
    return [{'id':v['id'],'name':v['name'],'color':v['color']} for v in room['clients'].values()]

async def handler(ws):
    room = None
    code = None
    me = None
    try:
        async for raw in ws:
            try: msg = json.loads(raw)
            except (ValueError,TypeError): continue
            if not isinstance(msg,dict): continue
            kind = msg.get('type')
            if room is None:
                if kind != 'join':
                    await send(ws,{'type':'error','message':'Join a room first.'});continue
                code = str(msg.get('room','SKETCH')).upper()[:16]
                if not re.fullmatch(r'[A-Z0-9_-]{1,16}',code):
                    await send(ws,{'type':'error','message':'Invalid room code.'});continue
                room = load_room(code)
                if len(room['clients'])>=8:
                    await send(ws,{'type':'error','message':'Room full (8 artists).'});room=None;continue
                cid = secrets.token_hex(8)
                name = str(msg.get('name','Artist')).strip()[:22] or 'Artist'
                color = COLORS[len(room['project']['layers'])%len(COLORS)]
                me = {'id':cid,'name':name,'color':color,'layerId':'artist-'+cid}
                room['clients'][ws]=me
                layer={'id':me['layerId'],'name':name,'opacity':1,'visible':True,'strokes':[]}
                room['project']['layers'].append(layer)
                save_room(code)
                await send(ws,{'type':'welcome','you':cid,'room':code,'members':members(room),'project':room['project']})
                await broadcast(room,{'type':'layer_joined','layer':layer},skip=ws)
                await broadcast(room,{'type':'members','members':members(room)})
                print(f'{name} joined {code}')
                continue
            layer = next((l for l in room['project']['layers'] if l['id']==me['layerId']),None)
            if layer is None: continue
            if kind=='cursor':
                if all(isinstance(msg.get(k),(int,float)) and abs(msg[k])<100000 for k in ('x','y')):
                    await broadcast(room,{'type':'cursor','from':me['id'],'x':msg['x'],'y':msg['y'],'p':msg.get('p',1),'size':min(180,max(.1,float(msg.get('size',18)))) if isinstance(msg.get('size'),(int,float)) else 18,'pressureSize':msg.get('pressureSize') is True,'drawing':bool(msg.get('drawing')),'erasing':bool(msg.get('erasing'))},skip=ws)
            elif kind=='stroke_start':
                head,p = msg.get('stroke'),msg.get('point')
                if valid_head(head) and valid_point(p) and len(room['active'])<16:
                    room['active'][me['id']]={'head':head,'first':p}
                    await broadcast(room,{'type':'stroke_start','from':me['id'],'stroke':head,'point':p},skip=ws)
            elif kind=='stroke_points':
                pts=msg.get('points')
                if me['id'] in room['active'] and isinstance(pts,list) and len(pts)<=250 and all(valid_point(p) for p in pts):
                    await broadcast(room,{'type':'stroke_points','from':me['id'],'points':pts},skip=ws)
            elif kind=='stroke_end':
                st=msg.get('stroke');active=room['active'].pop(me['id'],None)
                if active and valid_stroke(st) and st['id']==active['head']['id'] and st['id'] not in {s['id'] for s in layer['strokes']} and len(layer['strokes'])<10000:
                    layer['strokes'].append(st)
                    save_room(code)
                    await broadcast(room,{'type':'stroke_end','from':me['id'],'layerId':me['layerId'],'stroke':st},skip=ws)
            elif kind=='stroke_remove':
                stroke_id=msg.get('strokeId')
                if isinstance(stroke_id,str) and any(s['id']==stroke_id for s in layer['strokes']):
                    layer['strokes']=[s for s in layer['strokes'] if s['id']!=stroke_id]
                    save_room(code)
                    await broadcast(room,{'type':'stroke_remove','from':me['id'],'layerId':me['layerId'],'strokeId':stroke_id},skip=ws)
            elif kind=='stroke_restore':
                st=msg.get('stroke')
                if valid_stroke(st) and st['id'] not in {s['id'] for s in layer['strokes']}:
                    layer['strokes'].append(st)
                    save_room(code)
                    await broadcast(room,{'type':'stroke_restore','from':me['id'],'layerId':me['layerId'],'stroke':st},skip=ws)
    except ConnectionClosed: pass
    finally:
        if room and me:
            room['clients'].pop(ws,None)
            room['active'].pop(me['id'],None)
            await broadcast(room,{'type':'members','members':members(room)})
            print(f"{me['name']} left {code}")

async def main():
    print('Inkforge running at http://localhost:8000')
    print('WebSocket co-op running at ws://localhost:8000/ws')
    print('Keep this window open while drawing with friends. Ctrl+C to stop.')
    async with serve(handler,'0.0.0.0',8000,max_size=MAX_MESSAGE,ping_interval=20,process_request=serve_http):
        await asyncio.Future()

if __name__=='__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: print('\nServer stopped.')
