INKFORGE STUDIO CO-OP (Windows)
================================

1. Install Python 3.10 or later from https://www.python.org/downloads/
   Select 'Add Python to PATH' during installation.
2. Double-click START_SERVER.bat. It installs the websocket dependency,
   opens the drawing program, and starts the local room server.
3. On the host PC, click Co-op, choose a name and a room code, and Join.
4. On your friend's PC, open the HOST PC's address in Chrome or Edge:
     http://HOST-LAN-IP:8000
   Then click Co-op and enter the SAME room code.

To determine the host LAN IP on Windows, open Command Prompt and run ipconfig;
look for 'IPv4 Address'. LAN friends must use the same local network.
Windows Firewall may request permission for Python on private networks.

FRIENDS IN DIFFERENT HOUSES
---------------------------
Use a secure private network like Tailscale (install on BOTH PCs).
Both sign in, host starts the server, friend opens:
     http://HOST-TAILSCALE-IP:8000
Use the same room code. Allow local TCP ports 8000 and 8000 on the host.
Do not expose these unauthenticated ports directly to the public internet.

FEATURES
--------
- Live colored cursors with names and drawing indicators.
- Live remote brush preview every ~20 ms (network permitting).
- Wacom pressure-size and pressure-opacity via browser Pointer Events.
- Shared room artwork that persists in the host's 'rooms' directory.
- Each artist has their own layer; undo and redo control personal strokes.
- Export PNG or editable .inkforge file as a manual backup.

LIMITATIONS
-----------
- Host PC and the server process must stay online for live co-op.
- Eraser only erases within your own layer, not your friend's layers.
- Canvas is fixed at 2400 x 1600 for a new co-op room.
- Joining a room replaces your current local canvas, so save first.
- Collaboration is not encrypted over ordinary HTTP/WS on LAN. Use Tailscale
  to protect traffic across the internet.
- Your friend does not need Python: only the host does.

TIPS
----
For a Wacom Cintiq 16 or Intuos, install up-to-date Wacom drivers and enable
Windows Ink for pen pressure in Chrome or Edge. Test pen-pressure size on.
To restart a room, re-open START_SERVER.bat; artwork is in rooms/CODE.json.

VERSION 1.2 — BRUSH & UNDO UPDATE
- Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y undo and redo only your own co-op strokes.
- Room server enforces per-artist stroke removal; other artists' layers are protected.
- Strokes are drawn with quadratic midpoint interpolation plus pressure-aware spacing.
- You see a preview ring matching your brush diameter (adjust with [ and ]).
- Friends see your colored brush ring, which follows your pressure and brush size.
- For Wacom hover, preview keeps the most recent non-zero pen pressure,
  since pressure generally reads zero when the pen is above the display.
- Refresh browser after upgrading the server (or restart START_SERVER.bat).

VERSION 1.3 — WACOM PEN ERASER
- Flip a compatible Wacom pen to its eraser end to erase only while using that end.
- Turning the pen back leaves your selected brush/preset unchanged.
- The regular Eraser tool (E) remains available.
- The brush cursor becomes a dashed circle during pen-eraser contact.
- In co-op, pen erasing affects only your own layer and can be undone with Ctrl+Z.
- Uses Pointer Events pen eraser button 5 / buttons flag 32; proper Windows Ink
  Wacom driver support is required. Not all pen models have an eraser end.


VERSION 1.4 - CLOUDFARE QUICK TUNNEL FIX
---------------------------------------
Both the drawing website and real-time WebSocket now run through ONE port (8000).
The browser connects WebSockets to the same host it was loaded from, at /ws.
This works behind a single Cloudflare Quick Tunnel with HTTPS/WSS.

Start START_SERVER.bat, check http://127.0.0.1:8000, then in a new PowerShell:
  & "$env:USERPROFILE\Downloads\cloudflared-windows-amd64.exe" tunnel --url http://127.0.0.1:8000

Share the generated https://...trycloudflare.com link with your friend.
Both enter the same room code. Keep server and tunnel windows open.
The Quick Tunnel URL is public; use a private room code and share links only with trusted people.
Existing rooms: copy your old rooms folder into this new version before starting.
NOTE: Other people who learn the room code can view or modify that room.
