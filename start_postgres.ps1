# PowerShell script to start local PostgreSQL detached
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$Postgres = Join-Path $PSScriptRoot ".postgres\bin\postgres.exe"
$DataDir = Join-Path $PSScriptRoot ".postgres\data"
$PidFile = Join-Path $DataDir "postmaster.pid"
$LogFile = Join-Path $PSScriptRoot ".postgres\postgres.log"

# Clean up stale lock file if it exists but postgres isn't running
if (Test-Path $PidFile) {
    $processes = Get-Process -Name postgres -ErrorAction SilentlyContinue
    if (-not $processes) {
        Write-Host "Removing stale postmaster.pid file..." -ForegroundColor Yellow
        Remove-Item $PidFile -Force
    }
}

Write-Host "Starting PostgreSQL on localhost..." -ForegroundColor Green
cmd.exe /c "start /B `"`" `"$Postgres`" -D `"$DataDir`" >> `"$LogFile`" 2>&1"
