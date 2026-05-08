$ErrorActionPreference = 'Stop'

$RepoZipUrl = 'https://github.com/danieloculus0-bot/EZ-FAIR/archive/refs/heads/main.zip'
$InstallRoot = Join-Path $env:USERPROFILE 'EZ-FAIR'
$SourceDir = Join-Path $InstallRoot 'app'
$VenvDir = Join-Path $InstallRoot '.venv'
$BinDir = Join-Path $InstallRoot 'bin'
$LauncherPs1 = Join-Path $BinDir 'Launch-EZ-FAIR.ps1'
$LauncherCmd = Join-Path $BinDir 'Launch-EZ-FAIR.cmd'
$IconPath = Join-Path $BinDir 'EZ-FAIR.ico'
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'EZ-FAIR.lnk'
$StartMenuDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'EZ-FAIR'
$StartMenuShortcut = Join-Path $StartMenuDir 'EZ-FAIR.lnk'
$TempDir = Join-Path $env:TEMP ('ezfair_update_' + [Guid]::NewGuid().ToString('N'))
$ZipPath = Join-Path $TempDir 'EZ-FAIR-main.zip'
$ExtractDir = Join-Path $TempDir 'extract'

function Write-Step($Message) {
    Write-Host ''
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function New-Shortcut($ShortcutPath, $TargetPath, $Arguments, $WorkingDirectory, $IconLocation) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments
    $shortcut.WorkingDirectory = $WorkingDirectory
    if (Test-Path $IconLocation) { $shortcut.IconLocation = $IconLocation }
    $shortcut.Description = 'EZ-FAIR First Article Builder'
    $shortcut.Save()
}

function Copy-RepoItem($Source, $Destination) {
    $name = Split-Path $Source -Leaf
    if ($name -in @('.git', '.venv', 'local_inputs', 'local_outputs', '__pycache__')) { return }
    Copy-Item $Source $Destination -Recurse -Force
}

Write-Step 'Creating update folders'
New-Item -ItemType Directory -Force -Path $InstallRoot, $SourceDir, $BinDir, $TempDir, $ExtractDir | Out-Null

Write-Step 'Downloading latest EZ-FAIR from GitHub'
Invoke-WebRequest -Uri $RepoZipUrl -OutFile $ZipPath -UseBasicParsing

Write-Step 'Extracting update package'
Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force
$ExtractedRepo = Get-ChildItem $ExtractDir -Directory | Select-Object -First 1
if (-not $ExtractedRepo) { throw 'Extracted ZIP did not contain a repo folder.' }

Write-Step 'Updating app files without touching local inputs/outputs'
New-Item -ItemType Directory -Force -Path (Join-Path $SourceDir 'local_inputs'), (Join-Path $SourceDir 'local_outputs') | Out-Null
Get-ChildItem $ExtractedRepo.FullName -Force | ForEach-Object {
    Copy-RepoItem $_.FullName $SourceDir
}

Write-Step 'Updating Python packages'
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $PythonExe)) {
    throw "Missing venv Python: $PythonExe. Run install_windows.ps1 once first."
}
& $PythonExe -m pip install -r (Join-Path $SourceDir 'requirements.txt')

Write-Step 'Repairing launcher'
$LauncherPs1Content = @"
`$ErrorActionPreference = 'Stop'
`$Root = Split-Path -Parent (Split-Path -Parent `$MyInvocation.MyCommand.Path)
`$SourceDir = Join-Path `$Root 'app'
`$Python = Join-Path `$Root '.venv\Scripts\python.exe'
`$Script = Join-Path `$SourceDir 'polished_gui.py'
Set-Location `$SourceDir
& `$Python `$Script
"@
Set-Content -Path $LauncherPs1 -Value $LauncherPs1Content -Encoding UTF8
$LauncherCmdLines = @(
    '@echo off',
    'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-EZ-FAIR.ps1"',
    'if errorlevel 1 pause'
)
Set-Content -Path $LauncherCmd -Value $LauncherCmdLines -Encoding ASCII
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
New-Shortcut -ShortcutPath $DesktopShortcut -TargetPath $LauncherCmd -Arguments '' -WorkingDirectory $SourceDir -IconLocation $IconPath
New-Shortcut -ShortcutPath $StartMenuShortcut -TargetPath $LauncherCmd -Arguments '' -WorkingDirectory $SourceDir -IconLocation $IconPath

Write-Step 'Running import check'
Push-Location $SourceDir
& $PythonExe -c "import fitz, openpyxl, extractor_engine, fai_template_writer, local_test_runner, polished_gui; print('EZ-FAIR updated OK')"
Pop-Location

Write-Step 'Update complete'
Write-Host "Updated app folder: $SourceDir" -ForegroundColor Green
Write-Host 'Your local_inputs and local_outputs folders were preserved.' -ForegroundColor Green
Write-Host 'Close any open old output files if Windows still complains next time.' -ForegroundColor Yellow
