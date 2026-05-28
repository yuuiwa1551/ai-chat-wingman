param(
    [int]$Port = 18991,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendRoot = Join-Path $repoRoot "backend"
$frontendRoot = Join-Path $repoRoot "frontend"
$distPath = Join-Path $env:TEMP "ai-chat-wingman-dist-verify"
$workPath = Join-Path $env:TEMP "ai-chat-wingman-build-verify"
$dataPath = Join-Path $env:TEMP "ai-chat-wingman-data-verify"
$exePath = Join-Path $distPath "ai-chat-wingman.exe"

function Invoke-Step($Message, [scriptblock]$Action) {
    Write-Host "==> $Message"
    & $Action
}

function Stop-WingmanProcesses {
    Get-Process ai-chat-wingman -ErrorAction SilentlyContinue | Stop-Process -Force
}

Stop-WingmanProcesses
if (Test-Path $distPath) { Remove-Item -Recurse -Force $distPath }
if (Test-Path $workPath) { Remove-Item -Recurse -Force $workPath }
if (Test-Path $dataPath) { Remove-Item -Recurse -Force $dataPath }

$previousDataDir = $env:AI_CHAT_WINGMAN_DATA_DIR
$env:AI_CHAT_WINGMAN_DATA_DIR = $dataPath
$process = $null

try {
    Invoke-Step "Build frontend" {
        Push-Location $frontendRoot
        npm run build
        Pop-Location
    }

    Invoke-Step "Build desktop exe" {
        Push-Location $backendRoot
        uv run --extra desktop --extra build pyinstaller ..\build\wingman.spec --noconfirm --distpath $distPath --workpath $workPath
        Pop-Location
    }

    if (-not (Test-Path $exePath)) {
        throw "Packaged exe was not created: $exePath"
    }

    Invoke-Step "Start packaged exe" {
        $script:process = Start-Process -FilePath $exePath -ArgumentList "--api-port", "$Port" -PassThru
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $health = $null
    $lastError = $null
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            throw "Packaged exe exited before health check passed. ExitCode=$($process.ExitCode)"
        }
        try {
            $health = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$Port/healthz"
            if ($health.StatusCode -eq 200) { break }
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Milliseconds 500
    }

    if ($null -eq $health -or $health.StatusCode -ne 200) {
        $logPath = Join-Path $dataPath "logs\desktop-launcher.log"
        if (Test-Path $logPath) {
            Write-Host "Launcher log:"
            Get-Content $logPath
        }
        throw "Packaged exe did not become healthy. LastError=$lastError"
    }

    Invoke-Step "Verify onboarding endpoint" {
        $status = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$Port/onboarding/status"
        if ($status.StatusCode -ne 200) {
            throw "Unexpected onboarding status response: $($status.StatusCode)"
        }
        Write-Host $status.Content
    }

    Write-Host "Desktop package verification passed."
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    Stop-WingmanProcesses
    if ($null -eq $previousDataDir) {
        Remove-Item Env:AI_CHAT_WINGMAN_DATA_DIR -ErrorAction SilentlyContinue
    } else {
        $env:AI_CHAT_WINGMAN_DATA_DIR = $previousDataDir
    }
}