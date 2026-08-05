#define MyAppName "EZ FAIR"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "Daniel Boone Engineering"
#define MyAppExeName "EZ-FAIR.exe"

[Setup]
AppId={{E66D8360-8CB2-4F18-9ED9-9BE2CCDD9D18}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\EZ FAIR
DefaultGroupName=EZ FAIR
OutputDir=..\release
OutputBaseFilename=EZ-FAIR-{#MyAppVersion}-Setup-x64
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\EZ-FAIR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\EZ FAIR"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\EZ FAIR"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch EZ FAIR"; Flags: nowait postinstall skipifsilent
