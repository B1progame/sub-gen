@echo off
setlocal
cd /d "%~dp0"
title Caption Forge

if not exist ".venv\Scripts\python.exe" (
  echo [Caption Forge] Creating local Python environment...
  py -3 -m venv .venv || python -m venv .venv
)

echo [Caption Forge] Checking studio dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Could not install dependencies. Please check your internet connection and Python 3.10+ installation.
  pause
  exit /b 1
)

echo [Caption Forge] Starting local studio at http://127.0.0.1:8878
start "Caption Forge Server" /b ".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port 8878 --log-level warning --no-access-log
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8878
echo Studio is running. Keep this window open while editing.
pause
