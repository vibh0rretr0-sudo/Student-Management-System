@echo off
:: -----------------------------------------------------------------------------
:: JECRC Portal - Admin Launcher
:: This script requests admin privileges, activates the venv, and starts the app.
:: -----------------------------------------------------------------------------

:: Check for Administrative privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :ADMIN_OK
) else (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -FilePath '%0' -Verb RunAs"
    exit /b
)

:ADMIN_OK
echo [!] Running as Administrator.
cd /d "%~dp0"

:: Check for virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment (.venv) not found!
    echo Please create one first: python -m venv .venv
    pause
    exit /b
)

echo [!] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [!] Starting Flask Server...
echo -----------------------------------------------------------------------------
python run.py
echo -----------------------------------------------------------------------------
pause
