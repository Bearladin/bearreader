; BearReader - Windows Installer
; Compile: ISCC installer.iss /DMyAppVersion=X.Y.Z
; Requires: Inno Setup 6 (https://jrsoftware.org/isinfo.php)

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName      "BearReader"
#define MyAppPublisher "Bearladin"
#define MyAppURL       "https://github.com/lncrawl/lightnovel-crawler"
#define MyAppExeName   "BearReader.exe"
; Stable XiaoXiong AppId — never change this GUID, it identifies the app for upgrades/uninstalls
#define MyAppID        "{{D44F8E47-8D94-4E50-A1F8-39D57C2B18E6}"

[Setup]
AppId={#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\XiaoXiongNovel
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Per-user install without an UAC prompt.
PrivilegesRequired=lowest
ChangesEnvironment=yes
OutputDir=..\dist
OutputBaseFilename=BearReader-setup-{#MyAppVersion}-{#GetDateTimeString('yyyymmdd','','')}
SetupIconFile=..\res\bearreader.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
; Require Windows 10 or later
MinVersion=10.0

[Languages]
; MIT-licensed translation pinned from kira-96/Inno-Setup-Chinese-Simplified-Translation.
Name: "chinesesimp"; MessagesFile: ".\languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath";   Description: "将 {#MyAppName} 添加到 PATH（用于命令行）"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\dist\BearReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; The installer intentionally does not pre-delete the bundled source tree before copying:
; doing so could leave an existing install unusable if extraction fails or the user cancels.
; Stale bundled crawler files left behind by an upgrade are instead ignored at runtime,
; because bundled crawlers are activated strictly from the filtered index rather than by
; directory glob.

[Icons]
Name: "{group}\{#MyAppName}";                          Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";                    Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Add install dir to current-user PATH when "addtopath" task is selected
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Check: PathEntryMissing('{app}'); Tasks: addtopath

[Code]
function PathEntryMissing(Entry: string): boolean;
var
  CurrentPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', CurrentPath) then
  begin
    Result := True;
    Exit;
  end;
  Result := Pos(';' + Lowercase(Entry) + ';',
                ';' + Lowercase(CurrentPath) + ';') = 0;
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent
