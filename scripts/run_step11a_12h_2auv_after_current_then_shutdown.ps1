$ErrorActionPreference = "Continue"

$RepoRoot = "C:\Users\E713181\Documents\Dados"
$LogRoot = Join-Path $RepoRoot "FILIPA_DADOS\results\step11a_queued_12h_2auv_then_shutdown_logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $LogRoot "step11a_12h_2auv_queue_$timestamp.log"
$statusFile = Join-Path $LogRoot "step11a_12h_2auv_queue_$timestamp.status.json"
$currentStep11Pid = 19312

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $logFile -Value $line
}

Write-Log "Queue started."
Write-Log "Waiting for current 12h single-AUV Step11A PID $currentStep11Pid if it is still running."

try {
    $proc = Get-Process -Id $currentStep11Pid -ErrorAction SilentlyContinue
    if ($null -ne $proc) {
        Wait-Process -Id $currentStep11Pid
        Write-Log "Current Step11A PID $currentStep11Pid finished."
    } else {
        Write-Log "Current Step11A PID $currentStep11Pid was not running; continuing."
    }

    Set-Location -LiteralPath $RepoRoot
    $cmd = @(
        ".\FILIPA_DADOS\scripts\11a_run_minimal_boundary_planner_comparison.py",
        "--mission-duration-hours", "12",
        "--auv-number", "2",
        "--timeout-s", "1800"
    )
    Write-Log "Starting 12h 2-AUV Step11A: python $($cmd -join ' ')"
    & python @cmd *>> $logFile
    $exitCode = $LASTEXITCODE
    Write-Log "12h 2-AUV Step11A finished with exit code $exitCode."

    $status = [ordered]@{
        queued_at = $timestamp
        finished_at = (Get-Date -Format o)
        waited_for_pid = $currentStep11Pid
        command = "python $($cmd -join ' ')"
        exit_code = $exitCode
        log_file = $logFile
        shutdown_requested = $true
    }
    $status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusFile -Encoding UTF8
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    $status = [ordered]@{
        queued_at = $timestamp
        finished_at = (Get-Date -Format o)
        waited_for_pid = $currentStep11Pid
        error = $_.Exception.Message
        log_file = $logFile
        shutdown_requested = $true
    }
    $status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusFile -Encoding UTF8
}
finally {
    Write-Log "Scheduling shutdown in 120 seconds."
    shutdown.exe /s /t 120 /c "Step11A 12h 2-AUV run finished. Shutting down as requested."
}
