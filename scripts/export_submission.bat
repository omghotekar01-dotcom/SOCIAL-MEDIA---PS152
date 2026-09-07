@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

echo ============================================================
echo   NEXUS / SIH26152 - CLEAN SUBMISSION ZIP EXPORT

echo   This exports TRACKED Git files only.
echo   Local .env, .venv, node_modules and untracked secrets are excluded.
echo ============================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed or not available in PATH.
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Run this script from the cloned NEXUS repository.
  exit /b 1
)

for /f %%S in ('git rev-parse --short HEAD') do set "SHA=%%S"
for /f %%B in ('git branch --show-current') do set "BRANCH=%%B"

set "OUT=NEXUS_SIH26152_SUBMISSION_%SHA%.zip"

if exist "%OUT%" del /q "%OUT%"

echo [INFO] Branch : %BRANCH%
echo [INFO] Commit : %SHA%
echo [INFO] Output : %OUT%
echo.

git archive --format=zip --output="%OUT%" HEAD
if errorlevel 1 (
  echo [ERROR] Git archive failed.
  exit /b 1
)

if not exist "%OUT%" (
  echo [ERROR] ZIP was not created.
  exit /b 1
)

echo [PASS] Clean project ZIP created successfully.
echo [SAFE] .env and other untracked local secrets were not included.
echo.
echo File: %CD%\%OUT%
endlocal
