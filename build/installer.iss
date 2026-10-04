#define AppName "Track Separator"
[Setup]
AppId={{6B7A3F72-45EB-4BCD-9E8A-04855EB302A1}
AppName={#AppName}
AppVersion=0.4.1
DefaultDirName={localappdata}\Programs\TrackSeparator
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir=..\dist\installer
OutputBaseFilename=TrackSeparator-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
LicenseFile=..\LICENSE
[Files]
Source: "..\dist\TrackSeparator\*"; DestDir: "{app}"; Excludes: "unins*.exe,unins*.dat"; Flags: ignoreversion recursesubdirs createallsubdirs
[InstallDelete]
Type: files; Name: "{userprograms}\Music Digest Chords.lnk"
Type: files; Name: "{userdesktop}\Music Digest Chords.lnk"
[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\TrackSeparator.exe"; Parameters: "app"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\TrackSeparator.exe"; Parameters: "app"
[Run]
Filename: "{app}\TrackSeparator.exe"; Parameters: "app"; Description: "Open {#AppName}"; Flags: nowait postinstall skipifsilent
; User libraries and application data are deliberately outside {app}.

[UninstallDelete]
; PyInstaller's private runtime can contain caches created after installation.
; Remove only application-owned directories, never a wildcard over {app}.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: dirifempty; Name: "{app}"

[Code]
procedure StopInstalledProcesses;
var
  Locator, Services, Processes, Process: Variant;
  I, ResultCode: Integer;
  InstalledExe: String;
begin
  InstalledExe := ExpandConstant('{app}\TrackSeparator.exe');
  Locator := CreateOleObject('WbemScripting.SWbemLocator');
  Services := Locator.ConnectServer('', 'root\CIMV2');
  Processes := Services.ExecQuery('SELECT * FROM Win32_Process WHERE Name = ''TrackSeparator.exe''');
  for I := 0 to Processes.Count - 1 do begin
    Process := Processes.ItemIndex(I);
    if not VarIsNull(Process.ExecutablePath) then begin
      if CompareText(Process.ExecutablePath, InstalledExe) = 0 then begin
        Log('Closing installed Track Separator process ' + IntToStr(Process.ProcessId));
        ResultCode := Process.Terminate(0);
        if (ResultCode <> 0) and (ResultCode <> 9) then
          RaiseException('Close Track Separator and its separation jobs, then run uninstall again.');
      end;
    end;
  end;
  Sleep(1500);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    StopInstalledProcesses;
end;
