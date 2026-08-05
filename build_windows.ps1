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

Step 'Staging bundled OCR engine'
$Vendor = Join-Path $Root 'vendor\tesseract'
Remove-Item $Vendor -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Vendor | Out-Null
$Candidates = @(
    'C:\Program Files\Tesseract-OCR',
    'C:\Program Files (x86)\Tesseract-OCR'
)
$TesseractSource = $Candidates | Where-Object { Test-Path (Join-Path $_ 'tesseract.exe') } | Select-Object -First 1
if (-not $TesseractSource) {
    Write-Host 'Tesseract not found. Installing build-time package with Chocolatey.' -ForegroundColor Yellow
    choco install tesseract --no-progress -y
    $TesseractSource = $Candidates | Where-Object { Test-Path (Join-Path $_ 'tesseract.exe') } | Select-Object -First 1
}
if (-not $TesseractSource) {
    throw 'Tesseract installation completed without a discoverable tesseract.exe.'
}
Copy-Item (Join-Path $TesseractSource '*') $Vendor -Recurse -Force
if (-not (Test-Path (Join-Path $Vendor 'tessdata\eng.traineddata'))) {
    throw 'English OCR language data was not staged.'
}

Step 'Cleaning previous build'
Remove-Item (Join-Path $Root 'build') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Root 'dist') -Recurse -Force -ErrorAction SilentlyContinue

Step 'Building EZ-FAIR executable'
& $Python -m PyInstaller --noconfirm --clean ez_fair.spec

$Exe = Join-Path $Root 'dist\EZ-FAIR\EZ-FAIR.exe'
$BundledOCR = Join-Path $Root 'dist\EZ-FAIR\_internal\tesseract\tesseract.exe'
if (-not (Test-Path $Exe)) {
    throw "Build completed without expected executable: $Exe"
}
if (-not (Test-Path $BundledOCR)) {
    $BundledOCR = Join-Path $Root 'dist\EZ-FAIR\tesseract\tesseract.exe'
}
if (-not (Test-Path $BundledOCR)) {
    throw 'Build completed without the bundled OCR engine.'
}

Step 'Writing release notes'
$Readme = @'
EZ-FAIR Windows Build

Run EZ-FAIR.exe. Python, pip, Tesseract installation, and internet access are not required for normal drawing work.

Important:
- Drawing files and project data remain local.
- Review every extracted requirement before releasing inspection records.
- OCR is bundled and runs locally.
'@
Set-Content -Path (Join-Path $Root 'dist\EZ-FAIR\README.txt') -Value $Readme -Encoding UTF8

Step 'Creating ZIP artifact'
$Zip = Join-Path $Root 'dist\EZ-FAIR-Windows-x64.zip'
Remove-Item $Zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $Root 'dist\EZ-FAIR\*') -DestinationPath $Zip -Force

Write-Host "`nBuild complete:" -ForegroundColor Green
Write-Host $Exe -ForegroundColor Green
Write-Host $Zip -ForegroundColor Green
