param(
    [Parameter(Position = 0)]
    [ValidateSet("web", "desktop", "backend", "frontend", "test", "build", "verify")]
    [string]$Mode = "web",

    [switch]$Help
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Show-Help {
    Write-Host "AI Chat Wingman dev helper"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\dev.ps1             Start backend and frontend in two terminals"
    Write-Host "  .\dev.ps1 web         Same as the default mode"
    Write-Host "  .\dev.ps1 desktop     Start Vite and the PyWebView desktop shell"
    Write-Host "  .\dev.ps1 backend     Run FastAPI backend in this terminal"
    Write-Host "  .\dev.ps1 frontend    Run Vite frontend in this terminal"
    Write-Host "  .\dev.ps1 test        Run backend tests"
    Write-Host "  .\dev.ps1 build       Build the frontend"
    Write-Host "  .\dev.ps1 verify      Run packaged desktop verification"
}

function ConvertTo-PowerShellLiteral {
    param([string]$Value)

    return "'" + $Value.Replace("'", "''") + "'"
}

function Start-DevWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $QuotedDirectory = ConvertTo-PowerShellLiteral $WorkingDirectory
    $QuotedTitle = ConvertTo-PowerShellLiteral $Title
    $WindowCommand = "Set-Location $QuotedDirectory; `$Host.UI.RawUI.WindowTitle = $QuotedTitle; $Command"

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $WindowCommand
    )
}

function Invoke-InDirectory {
    param(
        [string]$WorkingDirectory,
        [scriptblock]$Command
    )

    Push-Location $WorkingDirectory
    try {
        & $Command
    }
    finally {
        Pop-Location
    }
}

if ($Help) {
    Show-Help
    exit 0
}

switch ($Mode) {
    "web" {
        Start-DevWindow "AI Chat Wingman Backend" $BackendDir "uv run uvicorn app.main:app --reload --port 8000"
        Start-DevWindow "AI Chat Wingman Frontend" $FrontendDir "npm run dev"
        Write-Host "Started backend and frontend terminals."
        Write-Host "Open http://127.0.0.1:5173"
    }
    "desktop" {
        Start-DevWindow "AI Chat Wingman Frontend" $FrontendDir "npm run dev"
        Start-DevWindow "AI Chat Wingman Desktop" $BackendDir "uv run --extra desktop python -m app.desktop.launcher --dev-server http://127.0.0.1:5173"
        Write-Host "Started Vite and desktop-shell terminals."
    }
    "backend" {
        Invoke-InDirectory $BackendDir { uv run uvicorn app.main:app --reload --port 8000 }
    }
    "frontend" {
        Invoke-InDirectory $FrontendDir { npm run dev }
    }
    "test" {
        Invoke-InDirectory $BackendDir { uv run python -m pytest -v }
    }
    "build" {
        Invoke-InDirectory $FrontendDir { npm run build }
    }
    "verify" {
        Invoke-InDirectory $RootDir { & (Join-Path $RootDir "scripts\verify_desktop_package.ps1") }
    }
}