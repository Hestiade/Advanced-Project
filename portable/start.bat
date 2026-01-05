@echo off
REM AI Mail Redirection Agent - Windows Client Launcher
REM This script starts the web dashboard client

cd /d "%~dp0"

echo.
echo ========================================
echo   AI Mail Redirection Agent
echo ========================================
echo.

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Check for .env file
if not exist ".env" (
    echo Creating .env from template...
    if exist ".env.example" (
        copy .env.example .env
    ) else (
        echo ERROR: .env.example not found
        pause
        exit /b 1
    )
    echo.
    echo Please edit .env with your mail server settings:
    echo   IMAP_HOST, IMAP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD
    echo.
    notepad .env
)

REM Check for virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting web dashboard...
echo Open http://localhost:5000 in your browser
echo.

python web_dashboard.py

pause
