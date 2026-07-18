#ifndef MyAppVersion
  #define MyAppVersion "2.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\AirMouse"
#endif
#ifndef OutputDir
  #define OutputDir "..\release"
#endif
#ifndef IconFile
  #define IconFile "..\build\AirMouse.ico"
#endif

#define MyAppName "AirMouse"
#define MyAppPublisher "Tory-Xu"
#define MyAppExeName "AirMouse.exe"

[Setup]
AppId={{B8C1EA3F-79F6-4A44-9C75-6C4CF490A2B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=AirMouse-Setup-{#MyAppVersion}-x64
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
AppMutex=Local\AirMouse.Remote

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项："; Flags: checkedonce
Name: "autostart"; Description: "登录 Windows 后自动启动 AirMouse"; GroupDescription: "附加选项："

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AirMouse"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AirMouse"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AirMouse"; ValueData: """{app}\{#MyAppExeName}"" --autostart"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "运行 AirMouse"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not WizardIsTaskSelected('autostart')) then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'AirMouse');
end;
