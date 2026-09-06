@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  NEXUS - FULL STACK STARTER (FastAPI + Spring + React)
echo ============================================================

where python >nul 2>&1 || (echo [ERROR] Python missing.& pause & exit /b 1)
where npm >nul 2>&1 || (echo [ERROR] Node/npm missing.& pause & exit /b 1)
where mvn >nul 2>&1 || (echo [ERROR] Maven missing. Use start_demo.bat if Java gateway is not required.& pause & exit /b 1)

if not exist ".env" copy /Y ".env.example" ".env" >nul
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\pip.exe" install -q -r backend-ai\requirements.txt || exit /b 1

if not exist "frontend\node_modules" (
  pushd frontend
  call npm install || (popd & exit /b 1)
  popd
)

start "NEXUS FastAPI" cmd /k "cd /d "%CD%\backend-ai" ^&^& "%CD%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul

start "NEXUS Spring Gateway" cmd /k "cd /d "%CD%\backend-java" ^&^& mvn spring-boot:run"
timeout /t 3 /nobreak >nul

set "VITE_USE_JAVA_GATEWAY=true"
start "NEXUS Frontend" cmd /k "cd /d "%CD%\frontend" ^&^& set VITE_USE_JAVA_GATEWAY=true ^&^& npm run dev"
timeout /t 3 /nobreak >nul

start "" http://127.0.0.1:5173

echo UI:      http://127.0.0.1:5173
echo FastAPI: http://127.0.0.1:8000/docs
echo Gateway: http://127.0.0.1:8080/api/gateway/health
exit /b 0
