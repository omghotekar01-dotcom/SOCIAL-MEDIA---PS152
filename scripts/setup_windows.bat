@echo off
setlocal
cd /d "%~dp0.."

echo ==============================================
echo   NEXUS - SIH26152 Windows Setup
echo ==============================================

where py >nul 2>nul
if %errorlevel%==0 (
  if not exist .venv\Scripts\python.exe py -3 -m venv .venv
) else (
  if not exist .venv\Scripts\python.exe python -m venv .venv
)

if not exist .venv\Scripts\python.exe (
  echo [ERROR] Python virtual environment could not be created.
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend-ai\requirements.txt
if errorlevel 1 exit /b 1

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js/npm is required for the analyst dashboard.
  exit /b 1
)

pushd frontend
call npm install
if errorlevel 1 (
  popd
  exit /b 1
)
popd

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example. Demo/replay works without adding any API key.
)

echo.
echo Setup complete.
echo Run scripts\start_demo.bat to launch NEXUS.
endlocal
