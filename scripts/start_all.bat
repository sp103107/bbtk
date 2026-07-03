@echo off
setlocal
cd /d "%~dp0.."
if not exist "VERSION" (
  echo ERROR: Run scripts\start_all.bat from the Best Buds Time Clock repo root.
  exit /b 1
)
set PORT=8080
set HOST=0.0.0.0
echo Best Buds Time Clock - local dev start-all
echo Starting backend on http://127.0.0.1:%PORT% ...
start "BBTC Kiosk Server" /MIN python scripts\start_kiosk_server.py --host %HOST% --port %PORT%
set /a TRIES=0
:wait_health
set /a TRIES+=1
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%PORT%/api/health', timeout=2)" >nul 2>&1
if %ERRORLEVEL%==0 goto open_browser
if %TRIES% GEQ 30 (
  echo ERROR: Backend did not become healthy on port %PORT%.
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_health
:open_browser
echo Backend healthy. Opening operator console...
start "" "http://127.0.0.1:%PORT%/"
echo Owner console: http://127.0.0.1:%PORT%/
echo Employee portal: http://127.0.0.1:%PORT%/employee
echo Local dev convenience only. Not a production deployment claim.
exit /b 0
