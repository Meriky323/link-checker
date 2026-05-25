param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $AppDir

$bundledPython = "C:\Users\patpat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path $bundledPython) {
  $python = $bundledPython
} else {
  $python = "python"
}

$env:HOST = "0.0.0.0"
$env:PORT = "$Port"

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "PatPat Link Checker - Local Deploy" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Local URL:" -ForegroundColor Cyan
Write-Host "  http://127.0.0.1:$Port/" -ForegroundColor White
Write-Host ""
Write-Host "LAN URLs, share one with IT/teammates on the same network:" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
  ForEach-Object { Write-Host ("  http://" + $_.IPAddress + ":$Port/") -ForegroundColor White }
Write-Host ""
Write-Host "Keep this window open while testing. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""
Start-Process "http://127.0.0.1:$Port/"
& $python "$AppDir\link_checker_app.py"
