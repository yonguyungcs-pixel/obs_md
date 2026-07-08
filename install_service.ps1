# PowerShell 脚本：一键注册 Windows 计划任务
# 以当前用户身份在登录时自动启动 sync_daemon
# 运行方式：右键以管理员身份运行，或在 PowerShell 中执行

param(
    [string]$PythonPath = "",
    [string]$ProjectDir = "D:\tools\bicv_obsidian\.obsidian\doc-sync",
    [string]$ConfigPath = "",
    [switch]$Uninstall
)

$TaskName = "ObsidianDocSync"

# ---- 卸载 ----
if ($Uninstall) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[OK] 已删除计划任务: $TaskName" -ForegroundColor Green
    } else {
        Write-Host "[INFO] 计划任务不存在: $TaskName" -ForegroundColor Yellow
    }
    exit 0
}

# ---- 自动查找 Python ----
if (-not $PythonPath) {
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue)?.Source,
        (Get-Command python3 -ErrorAction SilentlyContinue)?.Source,
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python311\python.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }
    
    if ($candidates.Count -eq 0) {
        Write-Host "[ERROR] 未找到 Python，请通过 -PythonPath 参数手动指定" -ForegroundColor Red
        exit 1
    }
    $PythonPath = $candidates[0]
}

# ---- 配置路径 ----
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $ProjectDir "config.yaml"
}

$DaemonScript = Join-Path $ProjectDir "sync_daemon.py"

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host " Obsidian Doc Sync — 计划任务安装" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Python:  $PythonPath"
Write-Host "  脚本:    $DaemonScript"
Write-Host "  配置:    $ConfigPath"
Write-Host ""

# ---- 创建计划任务 ----
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$DaemonScript`" start --config `"$ConfigPath`"" `
    -WorkingDirectory $ProjectDir

# 登录时触发
$TriggerLogin = New-ScheduledTaskTrigger -AtLogOn

# 注册
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $TriggerLogin `
    -Settings $Settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "[OK] 计划任务已注册: $TaskName" -ForegroundColor Green
Write-Host "     触发条件: 用户登录时自动启动" -ForegroundColor Gray
Write-Host ""
Write-Host "其他操作:" -ForegroundColor Yellow
Write-Host "  立即启动:   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  查看状态:   Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  卸载任务:   .\install_service.ps1 -Uninstall"
