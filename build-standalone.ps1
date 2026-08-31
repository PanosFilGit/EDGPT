param(
    [switch]$IncludeThirdParty,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Developer .venv not found. Create it first and install requirements."
}

Write-Host ""
Write-Host "EDGPT standalone release builder" -ForegroundColor Cyan
Write-Host "================================"

& $Python -m pip install --disable-pip-version-check --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Could not install/update PyInstaller." }

& $Python -m pip install --disable-pip-version-check -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install EDGPT requirements." }

$PyBuild = Join-Path $Root "build\pyinstaller"
$PyDist  = Join-Path $Root "build\pyinstaller-dist"
$Stage   = Join-Path $Root "release\EDGPT"
$InstallerOut = Join-Path $Root "release\installer"

Remove-Item $PyBuild -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $PyDist  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $Stage   -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $PyBuild, $PyDist, $Stage, (Join-Path $Stage "bin"), $InstallerOut | Out-Null

function Run-PyInstaller {
    param([string[]]$Arguments)
    & $Python -m PyInstaller @Arguments
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
}

Write-Host ""
Write-Host "[1/4] Building EDGPT.exe..." -ForegroundColor Cyan
Run-PyInstaller @(
    "--noconfirm", "--clean",
    "--windowed",
    "--onedir",
    "--name", "EDGPT",
    "--distpath", $PyDist,
    "--workpath", (Join-Path $PyBuild "launcher"),
    "--specpath", (Join-Path $PyBuild "specs"),
    (Join-Path $Root "launcher.py")
)

Write-Host "[2/4] Building state helper..." -ForegroundColor Cyan
Run-PyInstaller @(
    "--noconfirm", "--clean",
    "--console",
    "--onefile",
    "--paths", (Join-Path $Root "bin"),
    "--name", "edgpt-state",
    "--distpath", (Join-Path $PyDist "helpers"),
    "--workpath", (Join-Path $PyBuild "state"),
    "--specpath", (Join-Path $PyBuild "specs"),
    (Join-Path $Root "bin\server.py")
)

Write-Host "[3/4] Building GitHub helper..." -ForegroundColor Cyan
Run-PyInstaller @(
    "--noconfirm", "--clean",
    "--console",
    "--onefile",
    "--paths", (Join-Path $Root "bin"),
    "--name", "edgpt-uploader",
    "--distpath", (Join-Path $PyDist "helpers"),
    "--workpath", (Join-Path $PyBuild "uploader"),
    "--specpath", (Join-Path $PyBuild "specs"),
    (Join-Path $Root "bin\uploader.py")
)

Write-Host "[4/4] Building MCP helper..." -ForegroundColor Cyan
Run-PyInstaller @(
    "--noconfirm", "--clean",
    "--console",
    "--onefile",
    "--paths", (Join-Path $Root "bin"),
    "--name", "edgpt-mcp",
    "--collect-all", "mcp",
    "--distpath", (Join-Path $PyDist "helpers"),
    "--workpath", (Join-Path $PyBuild "mcp"),
    "--specpath", (Join-Path $PyBuild "specs"),
    (Join-Path $Root "bin\mcp_server.py")
)

Copy-Item (Join-Path $PyDist "EDGPT\*") $Stage -Recurse -Force
Copy-Item (Join-Path $PyDist "helpers\edgpt-state.exe")    (Join-Path $Stage "bin\edgpt-state.exe") -Force
Copy-Item (Join-Path $PyDist "helpers\edgpt-uploader.exe") (Join-Path $Stage "bin\edgpt-uploader.exe") -Force
Copy-Item (Join-Path $PyDist "helpers\edgpt-mcp.exe")      (Join-Path $Stage "bin\edgpt-mcp.exe") -Force

if (Test-Path (Join-Path $Root "README.md")) { Copy-Item (Join-Path $Root "README.md") $Stage -Force }
if (Test-Path (Join-Path $Root "LICENSE")) { Copy-Item (Join-Path $Root "LICENSE") $Stage -Force }

if ($IncludeThirdParty) {
    foreach ($Name in @("tunnel-client.exe", "cloudflared.exe")) {
        $Source = Join-Path $Root "bin\$Name"
        if (Test-Path $Source) {
            Copy-Item $Source (Join-Path $Stage "bin\$Name") -Force
            Write-Host "Included third-party binary for local test: $Name" -ForegroundColor Yellow
        }
    }
}

Remove-Item (Join-Path $Stage "data") -Recurse -Force -ErrorAction SilentlyContinue
$ForbiddenNames = @(
    "launcher_secret.bin",
    "github_token.bin",
    "launcher_config.json",
    "openai_secret.bin",
    "github_secret.bin"
)
Get-ChildItem $Stage -Recurse -File | Where-Object { $ForbiddenNames -contains $_.Name } | Remove-Item -Force

Write-Host ""
Write-Host "Standalone folder built:" -ForegroundColor Green
Write-Host "  $Stage"
Write-Host ""
Write-Host "TEST THIS FIRST:" -ForegroundColor Yellow
Write-Host "  $Stage\EDGPT.exe"
Write-Host ""
Write-Host "It no longer needs Python or .venv."

if ($SkipInstaller) { exit 0 }

$Iss = Join-Path $Root "installer\EDGPT-standalone.iss"
if (-not (Test-Path $Iss)) { throw "Missing installer\EDGPT-standalone.iss" }

$Candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$ISCC = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ISCC) { throw "Inno Setup 7/6 compiler (ISCC.exe) was not found." }

Write-Host ""
Write-Host "Building Setup.exe..." -ForegroundColor Cyan
& $ISCC $Iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }

$Setup = Join-Path $InstallerOut "EDGPT-Setup-0.2.0-beta.exe"
if (-not (Test-Path $Setup)) { throw "Installer build finished but EDGPT-Setup-0.2.0-beta.exe was not found." }

Write-Host ""
Write-Host "DONE!" -ForegroundColor Green
Write-Host "Standalone app: $Stage"
Write-Host "Installer:      $Setup"
