@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  NEXUS - SIH26152 DEMO STARTER v0.3
echo ============================================================

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 3.11+ is required and was not found in PATH.
  pause
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js is required and was not found in PATH.
  pause
  exit /b 1
)
node -e "const [M,m]=process.versions.node.split('.').map(Number);process.exit(((M===20&&m>=19)||(M===22&&m>=12)||M>22)?0:1)"
if errorlevel 1 (
  echo [ERROR] Vite 8 requires Node.js 20.19+ or 22.12+. Current version:
  node --version
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm is required and was not found in PATH.
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [INFO] Created .env from .env.example. Live API credentials are optional.
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/7] Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

set "PY=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

echo [2/7] Installing/checking Python dependencies...
"%PIP%" install -q -r backend-ai\requirements.txt pytest
if errorlevel 1 goto :fail

if not exist "frontend\node_modules" (
  echo [3/7] Installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    goto :fail
  )
  popd
) else (
  echo [3/7] Frontend dependencies already installed.
)

echo [4/7] Running source, backend-test and frontend-build preflight...
"%PY%" scripts\preflight.py
if errorlevel 1 (
  echo [ERROR] Preflight found a blocking project issue. NEXUS will not launch an unverified demo build.
  goto :fail
)

echo [5/7] Starting FastAPI analytics service...
start "NEXUS FastAPI" cmd /k "cd /d "%CD%\backend-ai" ^&^& "%CD%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

call :wait_for_api
if errorlevel 1 goto :fail

echo [6/7] Seeding deterministic fictional jury dataset...
powershell -NoProfile -Command "$body='{""reset"":true}'; Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/demo/seed' -Method POST -ContentType 'application/json' -Body $body | Out-Null" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] FastAPI started but demo seed failed.
  goto :fail
)

echo [7/7] Starting React analyst console...
start "NEXUS Frontend" cmd /k "cd /d "%CD%\frontend" ^&^& npm run dev"

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173

echo.
echo ============================================================
echo  NEXUS demo is ready.
echo  UI:           http://127.0.0.1:5173
echo  API docs:     http://127.0.0.1:8000/docs
echo  Health:       http://127.0.0.1:8000/health
echo  Evidence API: http://127.0.0.1:8000/api/certificates
echo.
echo  Seed data is fictional and explicitly labelled REPLAY.
echo  FREE SOURCE LAB can add real LIVE public evidence.
echo ============================================================
exit /b 0

:wait_for_api
for /L %%i in (1,1,45) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
echo [ERROR] FastAPI did not become ready within 45 seconds.
exit /b 1

:fail
echo.
echo [ERROR] Startup failed. Read the message above, fix it, then run scripts\start_demo.bat again.
pause
exit /b 1
