$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Step([string]$Message) {
    Write-Host "`n== $Message ==" -ForegroundColor Cyan
}

Step 'Checking Python'
python --version

Step 'Creating isolated build environment'
$Venv = Join-Path $Root '.venv-build'
if (-not (Test-Path $Venv)) {
    python -m venv $Venv
}
$Python = Join-Path $Venv 'Scripts\python.exe'

Step 'Installing build dependencies'
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python -m pip install pyinstaller pytest reportlab

Step 'Running tests'
& $Python -m pytest -q

Step 'Cleaning previous build'
Remove-Item (Join-Path $Root 'build') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Root 'dist') -Recurse -Force -ErrorAction SilentlyContinue

Step 'Building EZ-FAIR executable'
& $Python -m PyInstaller --noconfirm --clean ez_fair.spec

$Exe = Join-Path $Root 'dist\EZ-FAIR\EZ-FAIR.exe'
if (-not (Test-Path $Exe)) {
    throw "Build completed without expected executable: $Exe"
}

Step 'Writing release notes'
$Readme = @'
EZ-FAIR Windows Build

Run EZ-FAIR.exe. Python and internet access are not required.

Important:
- Drawing files remain local.
- Review all extracted requirements before releasing inspection records.
- OCR requires the Tesseract engine when processing raster-only drawings. Vector PDF extraction works without Tesseract.
'@
Set-Content -Path (Join-Path $Root 'dist\EZ-FAIR\README.txt') -Value $Readme -Encoding UTF8

Step 'Creating ZIP artifact'
$Zip = Join-Path $Root 'dist\EZ-FAIR-Windows-x64.zip'
Remove-Item $Zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $Root 'dist\EZ-FAIR\*') -DestinationPath $Zip -Force

Write-Host "`nBuild complete:" -ForegroundColor Green
Write-Host $Exe -ForegroundColor Green
Write-Host $Zip -ForegroundColor Green
