# PowerShell launcher for Windows
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$python = Join-Path $scriptDir '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  $python = 'python'
}
& $python (Join-Path $scriptDir 'start.py') @args
