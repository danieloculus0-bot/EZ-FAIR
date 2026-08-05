# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('pytesseract')

datas = []
datas += collect_data_files('openpyxl')
datas += collect_data_files('pytesseract')

vendor_tesseract = Path('vendor/tesseract')
if vendor_tesseract.exists():
    datas.append((str(vendor_tesseract), 'tesseract'))

analysis = Analysis(
    ['ez_fair.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyinstaller_runtime_hook.py'],
    excludes=['pytest', 'reportlab'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='EZ-FAIR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='windows_version_info.txt',
    manifest='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="0.2.1.0" processorArchitecture="amd64" name="DanielBooneEngineering.EZFAIR" type="win32"/>
  <description>EZ FAIR Inspection Platform</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
      <supportedOS Id="{4f476546-9377-4f6b-9f7f-6a2cbf48e8c5}"/>
    </application>
  </compatibility>
</assembly>
''',
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='EZ-FAIR',
)
