@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  NEXUS - SIH26152 DEMO STARTER
echo ============================================================

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 3.11+ is required and was not found in PATH.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js/npm is required and was not found in PATH.
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [INFO] Created .env from .env.example. Live API credentials are optional.
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

set "PY=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

echo [2/5] Installing/checking Python dependencies...
"%PIP%" install -q -r backend-ai\requirements.txt
if errorlevel 1 goto :fail

if not exist "frontend\node_modules" (
  echo [3/5] Installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    goto :fail
  )
  popd
) else (
  echo [3/5] Frontend dependencies already installed.
)

echo [4/5] Starting FastAPI analytics service...
start "NEXUS FastAPI" cmd /k "cd /d "%CD%\backend-ai" ^&^& "%CD%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

call :wait_for_api
if errorlevel 1 goto :fail

echo [INFO] Seeding deterministic fictional jury dataset...
powershell -NoProfile -Command "$body='{""reset"":true}'; Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/demo/seed' -Method POST -ContentType 'application/json' -Body $body | Out-Null" >nul 2>&1

echo [5/5] Starting React analyst console...
start "NEXUS Frontend" cmd /k "cd /d "%CD%\frontend" ^&^& npm run dev"

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173

echo.
echo ============================================================
echo  NEXUS demo is starting.
echo  UI:      http://127.0.0.1:5173
echo  API:     http://127.0.0.1:8000/docs
echo  Dataset: fictional replay data is clearly labelled REPLAY.
echo ============================================================
exit /b 0

:wait_for_api
for /L %%i in (1,1,30) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
echo [ERROR] FastAPI did not become ready within 30 seconds.
exit /b 1

:fail
echo.
echo [ERROR] Startup failed. Read the message above, fix it, then run this file again.
pause
exit /b 1
