@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title LLM Benchmark

:: Change directory to script folder
cd /d "%~dp0"

set "PY="

:: 1. Try Python Launcher (py -3)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PY=py -3"
    goto :check_file
)

:: 2. Try python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PY=python"
    goto :check_file
)

:: 3. Try python3
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PY=python3"
    goto :check_file
)

:: Check if python is installed but version is older than 3.9
python -V >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo Python was detected but version is older than 3.9:
    python -V
    echo Please upgrade to Python 3.9 or newer from https://www.python.org/
    goto :pause_if_double_clicked
)

echo Python 3.9 or newer was not found on this Windows system.
echo.
echo Installation Guide:
echo   1. Download Python from https://www.python.org/downloads/
echo   2. During installation, CHECK "Add python.exe to PATH"
echo   3. Reopen your terminal or Command Prompt once installation completes.
echo.

:pause_if_double_clicked
if "%~1"=="" pause
exit /b 1

:check_file
if not exist "llmload.py" (
    echo File llmload.py was not found in: %CD%
    if "%~1"=="" pause
    exit /b 1
)

:: If first argument is a valid subcommand (menu/baseline/ramp/rate/soak/compare/report), pass through directly.
:: Otherwise, launch the default interactive menu.
set "MODE=%~1"
if /i "%MODE%"=="menu" goto :run_direct
if /i "%MODE%"=="baseline" goto :run_direct
if /i "%MODE%"=="ramp" goto :run_direct
if /i "%MODE%"=="soak" goto :run_direct
if /i "%MODE%"=="rate" goto :run_direct
if /i "%MODE%"=="compare" goto :run_direct
if /i "%MODE%"=="report" goto :run_direct

%PY% llmload.py menu %*
goto :finish

:run_direct
%PY% llmload.py %*

:finish
set "EXIT_CODE=%ERRORLEVEL%"
if %EXIT_CODE% neq 0 (
    if "%~1"=="" pause
)
exit /b %EXIT_CODE%
