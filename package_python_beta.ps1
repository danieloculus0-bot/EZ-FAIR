$ErrorActionPreference = 'Stop'

$Version = '0.1.0-beta'
$InstallRoot = Join-Path $env:USERPROFILE 'EZ-FAIR'
$AppDir = Join-Path $InstallRoot 'app'
$PackageRoot = Join-Path $InstallRoot 'packages'
$StageDir = Join-Path $PackageRoot "EZ-FAIR-$Version-python"
$ZipPath = Join-Path $PackageRoot "EZ-FAIR-$Version-python.zip"

function Write-Step($Message) {
    Write-Host ''
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

if (-not (Test-Path $AppDir)) {
    throw "App folder not found: $AppDir"
}

Write-Step 'Preparing package folders'
New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null
if (Test-Path $StageDir) { Remove-Item $StageDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

Write-Step 'Copying app files'
$ExcludeDirs = @('.git', '.venv', '__pycache__', '.pytest_cache', 'local_inputs', 'local_outputs', 'packages')
$ExcludeFiles = @('*.pyc', '*.pyo', '*.log', '*_FAI.xlsx', '*_FAI.xlsm', '*_BALLOONED.pdf', 'EZ_FAI_DEBUG_REPORT.txt', 'EXTRACTION_SUMMARY.txt')

Get-ChildItem $AppDir -Force | Where-Object { $_.Name -notin $ExcludeDirs } | ForEach-Object {
    Copy-Item $_.FullName $StageDir -Recurse -Force
}

Get-ChildItem $StageDir -Recurse -Directory -Force | Where-Object { $_.Name -in $ExcludeDirs } | Sort-Object FullName -Descending | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
}

foreach ($pattern in $ExcludeFiles) {
    Get-ChildItem $StageDir -Recurse -File -Filter $pattern -Force -ErrorAction SilentlyContinue | Remove-Item -Force
}

Write-Step 'Creating clean runtime folders'
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir 'local_inputs'), (Join-Path $StageDir 'local_outputs'), (Join-Path $StageDir 'templates') | Out-Null

Write-Step 'Writing launchers and README'
$RunCmd = @'
@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python polished_gui.py
if errorlevel 1 pause
'@
Set-Content -Path (Join-Path $StageDir 'RUN_EZ-FAIR.cmd') -Value $RunCmd -Encoding ASCII

$Readme = @"
EZ-FAIR $Version - Python Beta Package

Purpose:
EZ-FAIR creates ballooned PDF drawings and editable Excel first article forms from local PDF blueprint files.

Requirements:
- Windows PC
- Python already installed
- Internet access for first dependency install, unless packages are already installed/cached

How to run:
1. Double-click RUN_EZ-FAIR.cmd
2. Select a PDF drawing
3. Select the Excel FAI template
4. Click Extract + Review
5. Review/edit rows
6. Click Generate Outputs

Outputs:
- Ballooned PDF
- Filled editable Excel FAI
- Extraction summary
- Debug report

Important:
- Review all generated dimensions before use.
- This is a beta tool, not final controlled inspection software.
- Customer drawings stay local.
- No customer PDFs are included in this package.

Daniel Boone / EZ-FAIR
"@
Set-Content -Path (Join-Path $StageDir 'README.txt') -Value $Readme -Encoding UTF8

Write-Step 'Creating ZIP package'
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $StageDir '*') -DestinationPath $ZipPath -Force

Write-Step 'Package complete'
Write-Host "Folder: $StageDir" -ForegroundColor Green
Write-Host "ZIP:    $ZipPath" -ForegroundColor Green
explorer $PackageRoot
