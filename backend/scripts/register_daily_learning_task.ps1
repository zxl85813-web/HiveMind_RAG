param(
    [string]$TaskName = "HiveMind-Daily-Learning",
    [string]$AtTime = "09:00",
    [string]$PythonExe = "C:\Users\linkage\Desktop\aiproject\.venv\Scripts\python.exe",
    [string]$ScriptPath = "C:\Users\linkage\Desktop\aiproject\backend\scripts\run_daily_learning_cycle_with_retry.py",
    [string]$WorkDir = "C:\Users\linkage\Desktop\aiproject"
)

$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`" --retries 3 --delay-seconds 20" -WorkingDirectory $WorkDir
$trigger = New-ScheduledTaskTrigger -Daily -At $AtTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output "[CL-2] Scheduled task registered: $TaskName at $AtTime"
