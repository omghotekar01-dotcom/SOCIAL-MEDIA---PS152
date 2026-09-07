@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  NEXUS - FULL STACK STARTER v0.3.3
echo  FastAPI + Spring Gateway + React
echo ============================================================

where python >nul 2>&1
if errorlevel 1 (echo [ERROR] Python 3.11-3.14 missing.& pause& exit /b 1)
python -c "import sys; exit(0 if (3,11) <= sys.version_info[:2] <= (3,14) else 1)"
if errorlevel 1 (echo [ERROR] Unsupported Python version.& python --version& pause& exit /b 1)

where node >nul 2>&1
if errorlevel 1 (echo [ERROR] Node.js missing.& pause& exit /b 1)
node -e "const [M,m]=process.versions.node.split('.').map(Number);process.exit(((M===20&&m>=19)||(M===22&&m>=12)||M>22)?0:1)"
if errorlevel 1 (echo [ERROR] Vite 8 requires Node.js 20.19+ or 22.12+.& node --version& pause& exit /b 1)

where npm >nul 2>&1
if errorlevel 1 (echo [ERROR] npm missing.& pause& exit /b 1)
where mvn >nul 2>&1
if errorlevel 1 (echo [ERROR] Maven missing. Use scripts\start_demo.bat if the Java gateway is not required.& pause& exit /b 1)
where java >nul 2>&1
if errorlevel 1 (echo [ERROR] Java 17+ missing.& pause& exit /b 1)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [INFO] Created .env from .env.example.
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/8] Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

set "PY=.venv\Scripts\python.exe"

echo [2/8] Installing/checking Python dependencies...
"%PY%" -m pip install -q --upgrade pip setuptools wheel
if errorlevel 1 goto :fail
"%PY%" -m pip install -q -r backend-ai\requirements.txt pytest
if errorlevel 1 goto :fail

if not exist "frontend\node_modules" (
  echo [3/8] Installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (popd& goto :fail)
  popd
) else (
  echo [3/8] Frontend dependencies already installed.
)

echo [4/8] Running project preflight...
"%PY%" scripts\preflight.py
if errorlevel 1 goto :fail

echo [5/8] Starting FastAPI analytics service...
start "NEXUS FastAPI" /D "%CD%\backend-ai" "%CD%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
call :wait_fastapi
if errorlevel 1 goto :fail

echo [INFO] Seeding deterministic fictional jury dataset...
"%PY%" scripts\seed_demo.py
if errorlevel 1 goto :fail

echo [6/8] Validating Spring gateway package...
pushd backend-java
call mvn -q -B test package -DskipTests=false
if errorlevel 1 (popd& goto :fail)
popd

echo [7/8] Starting Spring gateway...
start "NEXUS Spring Gateway" /D "%CD%\backend-java" cmd.exe /k mvn spring-boot:run
call :wait_gateway
if errorlevel 1 goto :fail

echo [8/8] Starting React console through Spring gateway...
start "NEXUS Frontend" /D "%CD%\frontend" cmd.exe /k "set VITE_USE_JAVA_GATEWAY=true&&npm run dev"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173

echo.
echo ============================================================
echo  NEXUS FULL STACK READY
echo  UI:           http://127.0.0.1:5173
echo  FastAPI docs: http://127.0.0.1:8000/docs
echo  Gateway:      http://127.0.0.1:8080/api/gateway/health
echo  Evidence API: http://127.0.0.1:8080/api/gateway/api/certificates
echo ============================================================
exit /b 0

:wait_fastapi
for /L %%i in (1,1,45) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
echo [ERROR] FastAPI health check timed out.
exit /b 1

:wait_gateway
for /L %%i in (1,1,60) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/api/gateway/health -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
echo [ERROR] Spring gateway health check timed out.
exit /b 1

:fail
echo.
echo [ERROR] Full-stack startup failed. Use scripts\start_demo.bat for the simpler direct FastAPI jury runtime.
pause
exit /b 1
