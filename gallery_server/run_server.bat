@echo off
setlocal

set "SHOW_CONSOLE="
if /i "%1"=="--console" set "SHOW_CONSOLE=1"

echo Starting ComfyUI Gallery Server...
echo.

cd /d "%~dp0"

if defined SHOW_CONSOLE (
    "c:\ComfyUI_windev\python_embeded\python.exe" -u "ascii_server.py"
) else (
    start /b "" "c:\ComfyUI_windev\python_embeded\pythonw" "ascii_server.py"
)

if errorlevel 1 (
    echo.
    echo Server failed to start
    echo Press any key to exit...
    pause >nul
) else (
    echo Server is running in background
    echo To view console, run with --show-console parameter
    timeout /t 3 >nul
)
