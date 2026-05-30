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
        uv run --extra desktop --extra build python -m PyInstaller ..\build\wingman.spec --noconfirm --distpath $distPath --workpath $workPath
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

    Invoke-Step "Verify reply generation endpoint" {
        $statusBody = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$Port/onboarding/status" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not $statusBody.has_default_profile) {
            $presetsBody = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$Port/onboarding/style-presets" | Select-Object -ExpandProperty Content | ConvertFrom-Json
            $profilePayload = @{
                name = "Default profile"
                selected_preset_ids = @($presetsBody.presets[0].id)
                avoid_patterns = @("Do not sound like AI")
            } | ConvertTo-Json
            Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post -ContentType "application/json" -Body $profilePayload "http://127.0.0.1:$Port/onboarding/default-profile" | Out-Null
        }

        $targetPayload = @{
            name = "Xia"
            relationship = "friend"
            preferences = "Prefers low-pressure messages."
            taboos = "Do not send repeated questions."
            strategy_guideline = "Acknowledge emotion and leave space."
        } | ConvertTo-Json
        $targetBody = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post -ContentType "application/json" -Body $targetPayload "http://127.0.0.1:$Port/targets" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        $targetId = $targetBody.target.id

        $screenshotPayload = @{
            filename = "chat.png"
            mime_type = "image/png"
            image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        } | ConvertTo-Json
        $parseBody = Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 -Method Post -ContentType "application/json" -Body $screenshotPayload "http://127.0.0.1:$Port/multimodal/parse-chat-screenshot" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not $parseBody.messages -or -not $parseBody.messages[0].content) {
            throw "Screenshot parse did not return messages."
        }

        $replyPayload = @{
            chat_text = "Target: $($parseBody.messages[0].content)"
            target_id = $targetId
            reply_goal = "comfort and leave room to continue later"
            tone = "natural and gentle"
            length = "short"
            proactivity = 0.35
            risk_level = "safe"
            candidate_count = 3
        } | ConvertTo-Json
        $reply = Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 -Method Post -ContentType "application/json" -Body $replyPayload "http://127.0.0.1:$Port/reply/generate"
        if ($reply.StatusCode -ne 200) {
            throw "Unexpected reply generation response: $($reply.StatusCode)"
        }
        if ($reply.Content -notmatch "event: done" -or $reply.Content -notmatch "event: candidate") {
            throw "Reply generation SSE did not include candidate and done events."
        }
        $doneLine = ($reply.Content -split "`n" | Where-Object { $_ -like "data: *conversation_id*" } | Select-Object -Last 1)
        $donePayload = $doneLine.Substring(6) | ConvertFrom-Json
        $favoritePayload = @{ candidate_index = 0; note = "package verification favorite" } | ConvertTo-Json
        $favorite = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post -ContentType "application/json" -Body $favoritePayload "http://127.0.0.1:$Port/history/conversations/$($donePayload.conversation_id)/favorite" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not $favorite.saved_reply.id) {
            throw "Favorite reply endpoint did not return a saved reply."
        }
        $history = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$Port/history/conversations?query=Target" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not $history.conversations -or $history.conversations.Count -lt 1) {
            throw "History search did not return the generated conversation."
        }
        Write-Host "Reply generation SSE verified."
    }

    Invoke-Step "Verify memory lifecycle endpoints" {
        $memTargetPayload = @{
            name = "MemTarget"
            relationship = "friend"
        } | ConvertTo-Json
        $memTargetBody = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post -ContentType "application/json" -Body $memTargetPayload "http://127.0.0.1:$Port/targets" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        $memTargetId = $memTargetBody.target.id

        $memReplyPayload = @{
            chat_text = "Target: I am under a lot of pressure and do not want to be pushed."
            target_id = $memTargetId
            candidate_count = 1
        } | ConvertTo-Json
        $memReply = Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 -Method Post -ContentType "application/json" -Body $memReplyPayload "http://127.0.0.1:$Port/reply/generate"
        if ($memReply.Content -notmatch "event: done") {
            throw "Memory-triggering reply generation did not complete."
        }

        $pending = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$Port/targets/$memTargetId/memories?status=pending" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not $pending.memories -or $pending.memories.Count -lt 1) {
            throw "Auto extraction did not create any pending memory."
        }

        $createMemPayload = @{
            content = "Target dislikes being pushed for quick replies."
            memory_type = "warning"
            confidence = 0.8
        } | ConvertTo-Json
        $createdMem = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post -ContentType "application/json" -Body $createMemPayload "http://127.0.0.1:$Port/targets/$memTargetId/memories" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        $memId = $createdMem.memory.id

        $approved = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post "http://127.0.0.1:$Port/memories/$memId/approve" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if ($approved.memory.status -ne "approved") {
            throw "Memory approval did not update status."
        }

        $approvedList = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$Port/targets/$memTargetId/memories?status=approved" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not ($approvedList.memories | Where-Object { $_.id -eq $memId })) {
            throw "Approved memory was not listed for the target."
        }
        Write-Host "Memory lifecycle verified."
    }

    Invoke-Step "Verify style test endpoint" {
        $sessionPayload = @{
            target_type = "friend"
            scenario = "The target is tired and does not want a long conversation."
            simulated_target_profile = "Slow to warm up and dislikes repeated questions under pressure."
        } | ConvertTo-Json
        $sessionBody = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post -ContentType "application/json" -Body $sessionPayload "http://127.0.0.1:$Port/style-test/sessions" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        $sessionId = $sessionBody.session.id

        $messagePayload = @{ content = "Take a rest first. No need to reply quickly." } | ConvertTo-Json
        $message = Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 -Method Post -ContentType "application/json" -Body $messagePayload "http://127.0.0.1:$Port/style-test/sessions/$sessionId/message"
        if ($message.StatusCode -ne 200) {
            throw "Unexpected style test message response: $($message.StatusCode)"
        }
        if ($message.Content -notmatch "event: done" -or $message.Content -notmatch "event: token") {
            throw "Style test SSE did not include token and done events."
        }

        $analysis = Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 -Method Post "http://127.0.0.1:$Port/style-test/sessions/$sessionId/analysis"
        if ($analysis.StatusCode -ne 200) {
            throw "Unexpected style test analysis response: $($analysis.StatusCode)"
        }
        Write-Host "Style test SSE and analysis verified."
    }

    Invoke-Step "Verify privacy data export" {
        $summary = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$Port/privacy/data-summary" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        if (-not $summary.data_path -or $summary.table_counts.style_presets -lt 1) {
            throw "Privacy data summary did not return expected data."
        }

        $exportStart = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Method Post "http://127.0.0.1:$Port/privacy/export" | Select-Object -ExpandProperty Content | ConvertFrom-Json
        $exportJobId = $exportStart.job_id
        $exportDeadline = (Get-Date).AddSeconds(20)
        $exportJob = $null
        while ((Get-Date) -lt $exportDeadline) {
            $exportJob = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$Port/jobs/$exportJobId" | Select-Object -ExpandProperty Content | ConvertFrom-Json
            if ($exportJob.status -in @("success", "failed")) { break }
            Start-Sleep -Milliseconds 250
        }
        if ($null -eq $exportJob -or $exportJob.status -ne "success") {
            throw "Privacy export job did not succeed. Status=$($exportJob.status) Error=$($exportJob.error_message)"
        }
        $exportResult = $exportJob.result | ConvertFrom-Json
        if (-not $exportResult.backup_path -or $exportResult.backup_size_bytes -le 0) {
            throw "Privacy export result did not include a usable backup file."
        }
        Write-Host "Privacy data export verified."
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