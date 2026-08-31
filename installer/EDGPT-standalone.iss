; EDGPT standalone installer
#define MyAppName "EDGPT"
#define MyAppVersion "0.2.0-beta"
#define MyAppPublisher "EDGPT Community"
#define MyAppExeName "EDGPT.exe"

[Setup]
AppId={{5E4518B7-B1AC-4F7D-A9B9-ED6FAF8A10D7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\EDGPT
DefaultGroupName=EDGPT
PrivilegesRequired=lowest
OutputDir=..\release\installer
OutputBaseFilename=EDGPT-Setup-0.2.0-beta
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=EDGPT
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\release\EDGPT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EDGPT"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\EDGPT"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch EDGPT"; Flags: nowait postinstall skipifsilent
