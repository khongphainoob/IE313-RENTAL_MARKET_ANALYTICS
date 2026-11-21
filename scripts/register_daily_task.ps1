# Registers the Windows scheduled task "IE313_DailySnapshot":
# - daily at 21:00 as the current user, from today until $EndDate (end of the analysis window);
# - if the computer is off/asleep at 21:00 it runs as soon as possible afterwards (StartWhenAvailable);
# - retries/validation are handled inside daily_snapshot.ps1 (up to ~1h), so the limit is 2h.
#
# Change the end date: edit $EndDate below and run this script again (it overwrites the task).
# Remove the task:     Unregister-ScheduledTask -TaskName IE313_DailySnapshot -Confirm:$false

$ErrorActionPreference = "Stop"
$EndDate = "2026-12-06T23:59:59"   # last day of week-2 analysis (see reports/KE_HOACH_3_TUAN.md)
$Script = Join-Path $PSScriptRoot "daily_snapshot.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 21:00
$trigger.EndBoundary = $EndDate
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName "IE313_DailySnapshot" -Action $action -Trigger $trigger -Settings $settings `
    -Description "IE313 - daily Cho Tot rental snapshot crawl (panel data), self-validating with retries" -Force | Out-Null

Get-ScheduledTask -TaskName "IE313_DailySnapshot" | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName "IE313_DailySnapshot" | Select-Object NextRunTime
