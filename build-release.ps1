$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "EDGPT public release build" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host "Building without third-party tunnel binaries." -ForegroundColor Yellow

& powershell -ExecutionPolicy Bypass -File (Join-Path $Root "build-standalone.ps1")
if ($LASTEXITCODE -ne 0) { throw "Standalone/installer build failed." }

$Stage = Join-Path $Root "release\EDGPT"
$Installer = Join-Path $Root "release\installer\EDGPT-Setup-0.2.0-beta.exe"
$Portable = Join-Path $Root "release\EDGPT-Portable.zip"
$Checksums = Join-Path $Root "release\SHA256SUMS.txt"

if (-not (Test-Path $Stage)) { throw "Missing staged app folder." }
if (-not (Test-Path $Installer)) { throw "Missing installer." }

$ForbiddenNames = @(
    "github_secret.bin", "openai_secret.bin", "github_token.bin",
    "launcher_secret.bin", "launcher_config.json", "config.json",
    "edgpt_history.db", "edgpt_history.db-shm", "edgpt_history.db-wal"
)
$Bad = Get-ChildItem $Stage -Recurse -File | Where-Object {
    $ForbiddenNames -contains $_.Name -or $_.FullName -match "\\data\\"
}
if ($Bad) {
    $Bad | ForEach-Object { Write-Host "FORBIDDEN: $($_.FullName)" -ForegroundColor Red }
    throw "Release safety scan failed."
}

foreach ($Name in @("tunnel-client.exe", "cloudflared.exe")) {
    if (Test-Path (Join-Path $Stage "bin\$Name")) {
        throw "Public stage unexpectedly contains $Name. Remove it or verify redistribution rights first."
    }
}

Remove-Item $Portable -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Portable -CompressionLevel Optimal

$Assets = @($Installer, $Portable)
$Lines = foreach ($Asset in $Assets) {
    $Hash = (Get-FileHash $Asset -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $([IO.Path]::GetFileName($Asset))"
}
$Lines | Set-Content $Checksums -Encoding ASCII

Write-Host ""
Write-Host "RELEASE ASSETS READY" -ForegroundColor Green
Write-Host "  $Installer"
Write-Host "  $Portable"
Write-Host "  $Checksums"
Write-Host ""
Write-Host "Before publishing: test EDGPT-Setup.exe on a clean Windows account/PC." -ForegroundColor Yellow
