# Install Windows Task Scheduler for daily recipe push
# Usage: powershell -ExecutionPolicy Bypass -File install_schedule.ps1

$TaskName = "每日菜谱推送"
$ScriptPath = "D:\Softwares\每次菜谱\daily_runner.py"
$PythonPath = (Get-Command python).Source
$Hour = 10  # Push at 10:00 AM daily

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At "$($Hour):00"
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

# Remove old task if exists
$null = Unregister-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue -Confirm:$false

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "AI 每日菜谱推送：选菜 → 搜索B站视频 → 推送到微信"

Write-Host "✅ 任务已创建: $TaskName"
Write-Host "   时间: 每天 $($Hour):00"
Write-Host "   脚本: $ScriptPath"
Write-Host ""
Write-Host "手动测试: python `"$ScriptPath`" --dry"
Write-Host "立即运行: Start-ScheduledTask -TaskName `"$TaskName`""
Write-Host "查看状态: Get-ScheduledTask -TaskName `"$TaskName`" | Select-Object State"
