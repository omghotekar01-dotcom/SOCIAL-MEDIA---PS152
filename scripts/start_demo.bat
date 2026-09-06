@echo off
setlocal
cd /d "%~dp0.."

if not exist .venv\Scripts\python.exe (
  echo First run detected - installing NEXUS dependencies...
  call scripts\setup_windows.bat
  if errorlevel 1 exit /b 1
)

if not exist frontend\node_modules (
  call scripts\setup_windows.bat
  if errorlevel 1 exit /b 1
)

if not exist .env copy .env.example .env >nul

echo Starting NEXUS FastAPI on http://127.0.0.1:8000
start "NEXUS API" cmd /k "cd /d %CD% && .venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend-ai --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo Starting NEXUS analyst console on http://127.0.0.1:5173
start "NEXUS UI" cmd /k "cd /d %CD%\frontend && npm run dev -- --host 127.0.0.1 --port 5173"

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173

echo.
echo NEXUS launched. The dashboard automatically seeds clearly-labelled REPLAY data if the local database is empty.
echo Add API credentials to .env only for the live connectors you want to enable.
endlocal
