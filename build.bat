@echo off
cd /d "%~dp0"
set LOG=%~dp0build_log.txt
echo Build started > "%LOG%"

set PY=
where py >nul 2>&1 && set PY=py -3
if "%PY%"=="" (where python >nul 2>&1 && set PY=python)
if "%PY%"=="" (
  echo [ERROR] Python not found. Install from python.org and tick "Add Python to PATH". >> "%LOG%"
  echo [ERROR] Python not found. Install from python.org and tick "Add Python to PATH".
  pause
  exit /b 1
)
echo Using: %PY% >> "%LOG%"

echo [1/4] Creating environment...
%PY% -m venv .venv >> "%LOG%" 2>&1 || goto :err
call .venv\Scripts\activate.bat

echo [2/4] Installing libraries (a few minutes)...
python -m pip install --upgrade pip >> "%LOG%" 2>&1
pip install -r requirements.txt >> "%LOG%" 2>&1 || goto :err

echo [3/4] Building app folder...
python make_icon.py >> "%LOG%" 2>&1 || goto :err
for /f %%v in ('python make_version.py') do set VER=%%v
echo Version: %VER% >> "%LOG%"
rem onedir (not onefile): opens in ~7s instead of 30s+ and triggers fewer antivirus false positives
pyinstaller --noconfirm --clean --onedir --windowed --noupx --name PDFYA ^
  --icon assets\icon.ico --version-file version_info.txt --splash assets\splash.png ^
  --add-data "assets;assets" --add-data "LICENSE.txt;." --add-data "THIRD_PARTY_NOTICES.txt;." ^
  --collect-all pptx --collect-all docx --collect-all pdf2docx --collect-all pymupdf ^
  --hidden-import i18n_en --hidden-import win32com.client --hidden-import pythoncom app.py >> "%LOG%" 2>&1 || goto :err

python prune_build.py >> "%LOG%" 2>&1
python make_portable.py >> "%LOG%" 2>&1 || goto :err

echo [4/4] Building installer...
set ISCC=
for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
  if exist %%p set ISCC=%%p
)
if not defined ISCC (
  echo [SKIP] Inno Setup 6 not found - installer not built. Get it from https://jrsoftware.org/isdl.php
  echo [SKIP] Inno Setup not found >> "%LOG%"
  goto :done
)
%ISCC% /Q /DAppVersion=%VER% installer.iss >> "%LOG%" 2>&1
if errorlevel 1 (
  rem antivirus sometimes locks the new setup file; retry once
  timeout /t 5 /nobreak >nul
  %ISCC% /Q /DAppVersion=%VER% installer.iss >> "%LOG%" 2>&1 || goto :err
)

:done
echo.
echo DONE:
echo   App folder: %~dp0dist\PDFYA\PDFYA.exe
echo   Portable:   %~dp0dist\installer\PDFYA-%VER%-portable.zip
if defined ISCC echo   Installer:  %~dp0dist\installer\PDFYA-Setup-%VER%.exe
pause
exit /b 0

:err
echo.
echo [ERROR] Build failed. See build_log.txt in this folder.
pause
exit /b 1
