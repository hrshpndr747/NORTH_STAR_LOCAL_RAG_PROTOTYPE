@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
call .venv\Scripts\activate.bat
python -m streamlit run app.py

