@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo Could not install Python dependency. Install Python 3.10+ from python.org first.
  pause
  exit /b 1
)
start "" http://localhost:8000
%PY% server.py
pause
