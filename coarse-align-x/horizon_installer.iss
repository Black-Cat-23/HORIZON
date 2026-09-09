; Inno Setup installer script for HORIZON
; Generated as part of Phase 19 implementation

[Setup]
AppName=HORIZON
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\HORIZON
DefaultGroupName=HORIZON
AllowNoIcons=yes
OutputBaseFilename=HORIZON_Installer
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=icons/horizon.ico
UninstallDisplayIcon={app}\HORIZON.exe

[Files]
Source: "dist\HORIZON\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\HORIZON"; Filename: "{app}\HORIZON.exe"
Name: "{commondesktop}\HORIZON"; Filename: "{app}\HORIZON.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\HORIZON.exe"; Description: "Launch HORIZON"; Flags: nowait postinstall skipifsilent

