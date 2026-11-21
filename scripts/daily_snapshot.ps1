# Daily Cho Tot snapshot crawl for the IE313 panel dataset (self-checking).
#
# - Runs `python -m src.crawler --snapshot` (writes data/raw/snapshots/YYYY-MM-DD.jsonl.gz)
# - The crawler validates its own output; a bad crawl never overwrites a good snapshot
# - Retries up to 3 attempts, 15 minutes apart, on network errors / failed validation
# - On final failure shows a Windows notification
# - After a successful crawl refreshes the merged dataset (python -m src.merge_snapshots)
# - After every run writes a status report to data/raw/snapshots/logs/YYYY-MM-DD.status.log
#
# Logs:   data/raw/snapshots/crawl.log           (one line per attempt)
#         data/raw/snapshots/logs/YYYY-MM-DD.*   (full crawler output + status report)
# Status: python -m src.snapshot_monitor
#
# Register once:  powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1
# Run by hand:    powershell -ExecutionPolicy Bypass -File scripts\daily_snapshot.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$SnapDir = Join-Path $ProjectRoot "data\raw\snapshots"
$LogDir = Join-Path $SnapDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Summary = Join-Path $SnapDir "crawl.log"
$day = Get-Date -Format "yyyy-MM-dd"

$MaxAttempts = 3
$RetryWaitSeconds = 900

$env:PYTHONIOENCODING = "utf-8"
$Python = (Get-Command python -ErrorAction Stop).Source

function Write-Summary([string]$text) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $Summary -Value "[$stamp] $text" -Encoding utf8
}

function Invoke-Python([string[]]$PyArgs, [string]$OutFile, [string]$ErrFile) {
    # Python logging writes to stderr; Start-Process keeps PowerShell 5.1 from treating it as an error.
    $p = Start-Process -FilePath $Python -ArgumentList $PyArgs -WorkingDirectory $ProjectRoot `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile
    return $p.ExitCode
}

function Show-FailureNotice([string]$message) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $icon = New-Object System.Windows.Forms.NotifyIcon
        $icon.Icon = [System.Drawing.SystemIcons]::Warning
        $icon.BalloonTipTitle = "IE313 crawl FAILED"
        $icon.BalloonTipText = $message
        $icon.Visible = $true
        $icon.ShowBalloonTip(15000)
        Start-Sleep -Seconds 16
        $icon.Dispose()
    } catch { }
}

$code = -1
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $out = Join-Path $LogDir "$day.attempt$attempt.out.log"
    $err = Join-Path $LogDir "$day.attempt$attempt.err.log"
    $code = Invoke-Python @("-W", "ignore", "-m", "src.crawler", "--snapshot", "--max-per-area", "300", "--delay", "0.35") $out $err

    switch ($code) {
        0 { Write-Summary "snapshot $day attempt $attempt/$MaxAttempts OK" }
        2 { Write-Summary "snapshot $day attempt $attempt/$MaxAttempts FAILED VALIDATION (previous data kept)" }
        3 { Write-Summary "snapshot $day attempt $attempt/$MaxAttempts SKIPPED (another crawl running)" }
        default { Write-Summary "snapshot $day attempt $attempt/$MaxAttempts CRASHED exit_code=$code (see logs\$day.attempt$attempt.err.log)" }
    }
    if ($code -eq 0 -or $code -eq 3) { break }
    if ($attempt -lt $MaxAttempts) { Start-Sleep -Seconds $RetryWaitSeconds }
}

# Refresh the merged dataset (data/raw/merged/) after a successful crawl
if ($code -eq 0) {
    $mergeCode = Invoke-Python @("-W", "ignore", "-m", "src.merge_snapshots") `
        (Join-Path $LogDir "$day.merge.out.log") (Join-Path $LogDir "$day.merge.err.log")
    Write-Summary "merge all crawls -> data\raw\merged\ exit_code=$mergeCode"
}

# Status report after every run (healthy = exit 0)
$statusOut = Join-Path $LogDir "$day.status.log"
$statusCode = Invoke-Python @("-W", "ignore", "-m", "src.snapshot_monitor") $statusOut (Join-Path $LogDir "$day.status.err.log")
Write-Summary "status report: $(if ($statusCode -eq 0) { 'healthy' } else { 'NEEDS ATTENTION' }) -> logs\$day.status.log"

if ($code -ne 0 -and $code -ne 3) {
    Show-FailureNotice "Snapshot $day failed after $MaxAttempts attempts. Run: python -m src.snapshot_monitor"
}
exit $code
