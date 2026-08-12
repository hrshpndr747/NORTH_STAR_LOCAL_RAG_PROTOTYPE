@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or 3.12, then run this file again.
  exit /b 1
)

if not exist .venv (
  py -m venv .venv
  if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m pip install -r requirements-media.txt
if errorlevel 1 exit /b 1

where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama was not found. Install it from https://ollama.com/download and rerun this file.
  exit /b 1
)

ollama pull qwen3.5:4b
if errorlevel 1 exit /b 1
ollama pull qwen3-embedding:0.6b
if errorlevel 1 exit /b 1

if not exist .env copy .env.example .env >nul
echo.
echo Setup complete. Double-click run_windows.bat next.
