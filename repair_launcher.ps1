$ErrorActionPreference = 'Stop'

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
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$GuiScript = Join-Path $SourceDir 'polished_gui.py'

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

Write-Step 'Checking install paths'
if (-not (Test-Path $SourceDir)) { throw "Missing app folder: $SourceDir" }
if (-not (Test-Path $PythonExe)) { throw "Missing venv Python: $PythonExe" }
if (-not (Test-Path $GuiScript)) { throw "Missing GUI script: $GuiScript" }
New-Item -ItemType Directory -Force -Path $BinDir, $StartMenuDir | Out-Null

Write-Step 'Repairing launcher files'
$LauncherPs1Content = @'
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SourceDir = Join-Path $Root 'app'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Script = Join-Path $SourceDir 'polished_gui.py'
Set-Location $SourceDir
& $Python $Script
'@
Set-Content -Path $LauncherPs1 -Value $LauncherPs1Content -Encoding UTF8

$LauncherCmdLines = @(
    '@echo off',
    'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-EZ-FAIR.ps1"',
    'if errorlevel 1 pause'
)
Set-Content -Path $LauncherCmd -Value $LauncherCmdLines -Encoding ASCII

Write-Step 'Repairing shortcuts'
New-Shortcut -ShortcutPath $DesktopShortcut -TargetPath $LauncherCmd -Arguments '' -WorkingDirectory $SourceDir -IconLocation $IconPath
New-Shortcut -ShortcutPath $StartMenuShortcut -TargetPath $LauncherCmd -Arguments '' -WorkingDirectory $SourceDir -IconLocation $IconPath

Write-Step 'Running import check'
Push-Location $SourceDir
& $PythonExe -c "import fitz, openpyxl, ez_fai_builder, fai_template_writer, local_test_runner, polished_gui; print('imports OK')"
Pop-Location

Write-Step 'Launching EZ-FAIR in debug mode'
Write-Host 'If the GUI closes, this window will show the actual error instead of doing that blink-and-die crap.' -ForegroundColor Yellow
Push-Location $SourceDir
& $PythonExe $GuiScript
Pop-Location
