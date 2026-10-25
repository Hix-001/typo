@echo off
title TYPO - Precision Typing Automation
cd /d "%~dp0"

echo ========================================================
echo   TYPO - Precision Typing Automation (v1.0)
echo   Global Trigger: Alt + Z + T   ^|   Emergency Stop: Esc
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

python main.py
if %errorlevel% neq 0 (
    echo.
    echo [INFO] An error occurred while running TYPO.
    pause
)
