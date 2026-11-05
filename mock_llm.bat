@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1

cd /d "%~dp0"

set "PY="

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PY=py -3"
    goto :run
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PY=python"
    goto :run
)

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PY=python3"
    goto :run
)

echo Python 3.9 or newer was not found on your system.
if "%~1"=="" pause
exit /b 1

:run
%PY% mock_llm.py %*
if %ERRORLEVEL% neq 0 (
    if "%~1"=="" pause
)
