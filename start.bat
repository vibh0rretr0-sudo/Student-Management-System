@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)

echo Installing dependencies...
.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example
)

echo Preparing demo database...
.venv\Scripts\python.exe -m app.seed

echo Starting portal at http://127.0.0.1:5000
.venv\Scripts\python.exe run.py
