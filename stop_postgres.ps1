# PowerShell script to stop local PostgreSQL
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$PgCtl = Join-Path $PSScriptRoot ".postgres\bin\pg_ctl.exe"
$DataDir = Join-Path $PSScriptRoot ".postgres\data"

Write-Host "Stopping PostgreSQL..." -ForegroundColor Yellow
& $PgCtl -D $DataDir stop
