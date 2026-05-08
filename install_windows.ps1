$ErrorActionPreference = 'Stop'

$RepoZipUrl = 'https://github.com/danieloculus0-bot/EZ-FAIR/archive/refs/heads/main.zip'
$InstallRoot = Join-Path $env:USERPROFILE 'EZ-FAIR'
$SourceDir = Join-Path $InstallRoot 'app'
$VenvDir = Join-Path $InstallRoot '.venv'
$BinDir = Join-Path $InstallRoot 'bin'
$IconPath = Join-Path $BinDir 'EZ-FAIR.ico'
$LauncherPs1 = Join-Path $BinDir 'Launch-EZ-FAIR.ps1'
$LauncherCmd = Join-Path $BinDir 'Launch-EZ-FAIR.cmd'
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'EZ-FAIR.lnk'
$StartMenuDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'EZ-FAIR'
$StartMenuShortcut = Join-Path $StartMenuDir 'EZ-FAIR.lnk'
$TempDir = Join-Path $env:TEMP ('ezfair_install_' + [Guid]::NewGuid().ToString('N'))
$ZipPath = Join-Path $TempDir 'EZ-FAIR-main.zip'
$ExtractDir = Join-Path $TempDir 'extract'

function Write-Step($Message) {
    Write-Host ''
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Get-PythonExe {
    foreach ($cmd in @('py','python')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $cmd }
    }
    throw 'Python is installed somewhere, but PowerShell cannot find py.exe or python.exe in PATH.'
}

function New-EzFairIcon($Path) {
    Add-Type -AssemblyName System.Drawing
    $bmp = New-Object System.Drawing.Bitmap 64,64
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::FromArgb(16,24,32))
    $blue = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(9,58,117))
    $light = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(40,125,205))
    $white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(210,225,240)), 2
    $g.FillEllipse($blue, 6, 6, 52, 52)
    $g.DrawEllipse($pen, 6, 6, 52, 52)
    $g.FillRectangle($light, 14, 16, 36, 7)
    $g.FillRectangle($light, 11, 29, 42, 7)
    $g.FillRectangle($light, 8, 42, 48, 7)
    $font = New-Object System.Drawing.Font 'Arial', 13, ([System.Drawing.FontStyle]::Bold)
    $fmt = New-Object System.Drawing.StringFormat
    $fmt.Alignment = [System.Drawing.StringAlignment]::Center
    $fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
    $g.DrawString('FAI', $font, $white, (New-Object System.Drawing.RectangleF 0,0,64,64), $fmt)
    $icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
    $stream = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::Create)
    $icon.Save($stream)
    $stream.Close()
    $g.Dispose()
    $bmp.Dispose()
}

function New-Shortcut($ShortcutPath, $TargetPath, $Arguments, $WorkingDirectory, $IconLocation) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.IconLocation = $IconLocation
    $shortcut.Description = 'EZ-FAIR First Article Builder'
    $shortcut.Save()
}

Write-Step 'Creating install folders'
New-Item -ItemType Directory -Force -Path $InstallRoot, $BinDir, $TempDir, $ExtractDir | Out-Null

Write-Step 'Downloading EZ-FAIR from GitHub'
Invoke-WebRequest -Uri $RepoZipUrl -OutFile $ZipPath -UseBasicParsing

Write-Step 'Extracting repo files'
Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force
$ExtractedRepo = Get-ChildItem $ExtractDir -Directory | Select-Object -First 1
if (-not $ExtractedRepo) { throw 'Extracted ZIP did not contain a repo folder.' }
if (Test-Path $SourceDir) { Remove-Item $SourceDir -Recurse -Force }
Copy-Item $ExtractedRepo.FullName $SourceDir -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $SourceDir 'local_inputs'), (Join-Path $SourceDir 'local_outputs') | Out-Null

Write-Step 'Creating Python virtual environment'
$PythonCmd = Get-PythonExe
if (Test-Path $VenvDir) { Remove-Item $VenvDir -Recurse -Force }
if ($PythonCmd -eq 'py') { & py -3 -m venv $VenvDir } else { & python -m venv $VenvDir }
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$PythonwExe = Join-Path $VenvDir 'Scripts\pythonw.exe'
if (-not (Test-Path $PythonExe)) { throw 'Virtual environment Python was not created.' }

Write-Step 'Installing Python packages'
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r (Join-Path $SourceDir 'requirements.txt')

Write-Step 'Creating icon and launcher'
New-EzFairIcon $IconPath
$LauncherPs1Content = @"
`$ErrorActionPreference = 'Stop'
`$Root = Split-Path -Parent (Split-Path -Parent `$MyInvocation.MyCommand.Path)
`$SourceDir = Join-Path `$Root 'app'
`$Pythonw = Join-Path `$Root '.venv\Scripts\pythonw.exe'
`$Python = Join-Path `$Root '.venv\Scripts\python.exe'
`$Script = Join-Path `$SourceDir 'polished_gui.py'
Set-Location `$SourceDir
if (Test-Path `$Pythonw) {
    Start-Process -FilePath `$Pythonw -ArgumentList @(`$Script) -WorkingDirectory `$SourceDir
} else {
    Start-Process -FilePath `$Python -ArgumentList @(`$Script) -WorkingDirectory `$SourceDir
}
"@
Set-Content -Path $LauncherPs1 -Value $LauncherPs1Content -Encoding UTF8
Set-Content -Path $LauncherCmd -Value '@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-EZ-FAIR.ps1"`r`n' -Encoding ASCII

Write-Step 'Creating Desktop and Start Menu shortcuts'
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
New-Shortcut -ShortcutPath $DesktopShortcut -TargetPath $LauncherCmd -Arguments '' -WorkingDirectory $SourceDir -IconLocation $IconPath
New-Shortcut -ShortcutPath $StartMenuShortcut -TargetPath $LauncherCmd -Arguments '' -WorkingDirectory $SourceDir -IconLocation $IconPath

Write-Step 'Running sanity check'
$CheckScript = Join-Path $TempDir 'check_ezfair.py'
Set-Content -Path $CheckScript -Value "import fitz, openpyxl, ez_fai_builder, fai_template_writer, polished_gui; print('EZ-FAIR imports OK')" -Encoding UTF8
Push-Location $SourceDir
& $PythonExe $CheckScript
Pop-Location

Write-Step 'Install complete'
Write-Host "Installed to: $InstallRoot" -ForegroundColor Green
Write-Host "Desktop launcher: $DesktopShortcut" -ForegroundColor Green
Write-Host "Double-click EZ-FAIR on the desktop to launch it." -ForegroundColor Green
Write-Host ''
Write-Host 'Say next when done.'
