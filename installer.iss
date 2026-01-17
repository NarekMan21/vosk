; VoiceInput Installer Script for Inno Setup
; Скомпилировать через Inno Setup Compiler

#define MyAppName "VoiceInput"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VoiceInput"
#define MyAppURL "https://github.com/your-repo/voiceinput"
#define MyAppExeName "VoiceInput.exe"

[Setup]
; Уникальный ID приложения (сгенерируйте свой на https://www.guidgenerator.com/)
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Выходной файл установщика
OutputDir=output
OutputBaseFilename=VoiceInput-Setup-{#MyAppVersion}
; Иконка установщика (опционально)
; SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Требуем права администратора для установки в Program Files
PrivilegesRequired=admin
; Минимальная версия Windows
MinVersion=10.0
; Архитектура
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Показывать лицензию
; LicenseFile=LICENSE.txt
; Показывать README после установки
; InfoAfterFile=README.txt

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "autostart"; Description: "Запускать при старте Windows"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Components]
Name: "main"; Description: "Основные файлы программы"; Types: full compact custom; Flags: fixed
Name: "model_small"; Description: "Малая модель (45 МБ) — быстрая, базовое качество"; Types: full compact custom; Flags: fixed
; Большая модель НЕ включается — пользователь скачает через Настройки → Управление моделями

[Types]
Name: "full"; Description: "Стандартная установка"
Name: "compact"; Description: "Компактная установка"
Name: "custom"; Description: "Выборочная установка"; Flags: iscustom

[Files]
; Основной исполняемый файл
Source: "dist\VoiceInput.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main
; Конфигурация
Source: "dist\config.json"; DestDir: "{app}"; Flags: ignoreversion; Components: main
; Малая модель (всегда устанавливается)
Source: "dist\models\vosk-model-small-ru-0.22\*"; DestDir: "{app}\models\vosk-model-small-ru-0.22"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: model_small
; Большая модель НЕ включается — скачивается через меню настроек

[Icons]
; Ярлык в меню Пуск
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
; Ярлык на рабочем столе
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; Ярлык в Quick Launch
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Автозапуск при старте Windows (если выбрано)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Запустить программу после установки
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Удалить логи и временные файлы при деинсталляции
Type: files; Name: "{app}\voice_input.log"
Type: files; Name: "{app}\stats.json"
Type: dirifempty; Name: "{app}\models"
Type: dirifempty; Name: "{app}"

[Code]
// Проверка, что приложение не запущено
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Проверяем, запущен ли VoiceInput
  if Exec('tasklist', '/FI "IMAGENAME eq VoiceInput.exe" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // Можно добавить проверку вывода tasklist
  end;
end;

// Завершение процесса перед обновлением
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    // Завершаем процесс VoiceInput если он запущен
    Exec('taskkill', '/F /IM VoiceInput.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
