@echo off
setlocal

cd /d "%~dp0"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="help" goto :help
if /I "%~1"=="/?" goto :help

where powershell.exe >nul 2>nul
if errorlevel 1 (
    echo PowerShell is required to start AI Chat Wingman.
    echo Please install or enable Windows PowerShell and try again.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" desktop
if errorlevel 1 (
    echo.
    echo Failed to start AI Chat Wingman.
    pause
    exit /b %errorlevel%
)

exit /b 0

:help
echo AI Chat Wingman click-to-start launcher
echo.
echo Double-click start_app.bat to start the full desktop app.
echo It opens the Vite frontend and the PyWebView desktop shell.
echo.
echo Command line:
echo   start_app.bat
echo   start_app.bat --help
exit /b 0