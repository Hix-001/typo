@echo off
title TYPO - Precision Typing Automation
cd /d "%~dp0"

echo ========================================================
echo   TYPO - Precision Typing Automation (v1.0)
echo   Global Trigger: Alt + Z + T   ^|   Emergency Stop: Esc
echo ========================================================
echo.

set "PYTHON_CMD=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py"
    ) else (
        echo [ERROR] Python was not found in your system PATH.
        echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
        pause
        exit /b 1
    )
)

%PYTHON_CMD% -c "import PySide6, pynput" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] First-time setup detected: Installing required dependencies...
    echo [INFO] Installing PySide6 and required packages from requirements.txt...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b 1
    )
    echo [OK] All dependencies installed successfully.
    echo.
)

%PYTHON_CMD% main.py
if %errorlevel% neq 0 (
    echo.
    echo [INFO] An error occurred while running TYPO.
    pause
)
