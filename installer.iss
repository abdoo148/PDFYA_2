; مثبّت PDFYA من Codpact (Inno Setup 6) — يُبنى عبر build.bat بعد PyInstaller
; يدويًا: ISCC.exe /DAppVersion=1.2.0 installer.iss

#ifndef AppVersion
  #define AppVersion "1.2.0"
#endif
#define AppName "PDFYA"
#define AppExe "PDFYA.exe"
#define AppPublisher "Codpact"
#define AppPublisherAr "Codpact للحلول الرقمية"

[Setup]
; لا تغيّر AppId أبدًا: هو ما يجعل الإصدارات الجديدة تُحدِّث نفس التثبيت
AppId={{FE54C93C-1D77-4A82-8A14-93C33B75625C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=(C) 2026 {#AppPublisherAr}
VersionInfoCompany={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=LICENSE.txt
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; تثبيت للمستخدم الحالي بدون صلاحيات مسؤول، مع خيار التثبيت لكل المستخدمين
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
#if FileExists(CompilerPath + "Languages\Arabic.isl")
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"; InfoBeforeFile: "docs\install_notes_ar.txt"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "docs\install_notes_en.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\PDFYA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\install_notes_*.txt"; DestDir: "{app}"; Flags: ignoreversion
; الكود المصدري الكامل (مطلوب بترخيص AGPL عند توزيع البرنامج)
Source: "app.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "core.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "i18n.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "i18n_en.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "gui\*.py"; DestDir: "{app}\source\gui"; Flags: ignoreversion
Source: "make_icon.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "make_version.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "make_portable.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "prune_build.py"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "build.bat"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "installer.iss"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\source\assets"; Flags: ignoreversion

[InstallDelete]
; عند التحديث من إصدار سابق باسم SignConvert أو Pedo (نفس AppId)
Type: files; Name: "{app}\SignConvert.exe"
Type: files; Name: "{autoprograms}\SignConvert.lnk"
Type: files; Name: "{autodesktop}\SignConvert.lnk"
Type: files; Name: "{app}\Pedo.exe"
Type: files; Name: "{autoprograms}\Pedo.lnk"
Type: files; Name: "{autodesktop}\Pedo.lnk"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; ملاحظة: إعدادات المستخدم ومكتبة التواقيع في %APPDATA%\PDFYA لا تُحذف عند إزالة البرنامج
; (عند أول تشغيل تُنسخ تلقائيًا من %APPDATA%\Pedo أو %APPDATA%\SignConvert إن وُجد)
