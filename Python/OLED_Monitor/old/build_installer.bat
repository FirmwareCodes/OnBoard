@echo off
chcp 65001 >nul
title OnBoard OLED Monitor - EXE 빌드 및 인스톨러

echo ================================================================
echo OnBoard OLED Monitor EXE 빌드 및 인스톨러 v1.4
echo ================================================================
echo.

REM 현재 디렉토리 확인
set CURRENT_DIR=%~dp0
set PROJECT_ROOT=%CURRENT_DIR%..\..\
set RUN_DIR=%CURRENT_DIR%run
set BUILD_DIR=%CURRENT_DIR%build
set DIST_DIR=%CURRENT_DIR%dist

echo [1/8] 환경 확인 중...
echo 현재 디렉토리: %CURRENT_DIR%
echo 프로젝트 루트: %PROJECT_ROOT%
echo 실행 파일 저장 위치: %RUN_DIR%
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다!
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)

echo ✅ Python 설치 확인됨
python --version

REM pip 확인
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip이 설치되어 있지 않습니다!
    pause
    exit /b 1
)

echo ✅ pip 설치 확인됨
echo.

echo [2/8] 필수 패키지 설치 중...
echo PyInstaller 설치...
pip install pyinstaller --quiet --disable-pip-version-check
if errorlevel 1 (
    echo ❌ PyInstaller 설치 실패!
    pause
    exit /b 1
)

echo 기본 의존성 설치...
pip install pillow numpy pyserial --quiet --disable-pip-version-check
if errorlevel 1 (
    echo ❌ 의존성 설치 실패!
    pause
    exit /b 1
)

echo ✅ 필수 패키지 설치 완료
echo.

echo [3/8] run 폴더 생성...
if not exist "%RUN_DIR%" (
    mkdir "%RUN_DIR%"
    echo ✅ run 폴더 생성됨: %RUN_DIR%
) else (
    echo ✅ run 폴더 확인됨: %RUN_DIR%
)
echo.

echo [4/9] 아이콘 생성...
if not exist "%CURRENT_DIR%icon.ico" (
    echo 아이콘 파일이 없습니다. 생성 중...
    python "%CURRENT_DIR%create_icon.py"
    if errorlevel 1 (
        echo ⚠️ 아이콘 생성 실패 - 기본 아이콘 없이 빌드합니다
        set ICON_PARAM=
    ) else (
        echo ✅ 아이콘 생성 완료
        set ICON_PARAM=--icon="%CURRENT_DIR%icon.ico"
    )
) else (
    echo ✅ 기존 아이콘 파일 확인됨
    set ICON_PARAM=--icon="%CURRENT_DIR%icon.ico"
)
echo.

echo [5/9] 기존 빌드 파일 정리...
if exist "%BUILD_DIR%" (
    echo 기존 build 폴더 삭제 중...
    rmdir /s /q "%BUILD_DIR%"
)
if exist "%DIST_DIR%" (
    echo 기존 dist 폴더 삭제 중...
    rmdir /s /q "%DIST_DIR%"
)
if exist "*.spec" (
    echo 기존 spec 파일 삭제 중...
    del /q *.spec
)
echo ✅ 기존 빌드 파일 정리 완료
echo.

echo [6/9] EXE 파일 빌드 중...
echo 이 과정은 1-3분 정도 소요될 수 있습니다...
echo.

REM PyInstaller로 EXE 빌드
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "OnBoard_OLED_Monitor" ^
    --add-data "requirements.txt;." ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "numpy" ^
    --hidden-import "serial" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.filedialog" ^
    --hidden-import "tkinter.messagebox" ^
    --collect-all "serial" ^
    --collect-all "PIL" ^
    --exclude-module "matplotlib" ^
    --exclude-module "scipy" ^
    --exclude-module "pandas" ^
    --optimize 2 ^
    %ICON_PARAM% ^
    "oled_monitor.py"

if errorlevel 1 (
    echo ❌ EXE 빌드 실패!
    echo 오류 로그를 확인하세요.
    pause
    exit /b 1
)

echo ✅ EXE 빌드 완료
echo.

echo [7/9] 생성된 EXE 파일 확인...
if not exist "%DIST_DIR%\OnBoard_OLED_Monitor.exe" (
    echo ❌ EXE 파일이 생성되지 않았습니다!
    pause
    exit /b 1
)

REM 파일 크기 확인
for %%A in ("%DIST_DIR%\OnBoard_OLED_Monitor.exe") do (
    set EXE_SIZE=%%~zA
)
set /a EXE_SIZE_MB=%EXE_SIZE% / 1024 / 1024

echo ✅ EXE 파일 생성 확인됨
echo 파일 크기: %EXE_SIZE_MB% MB
echo.

echo [8/9] EXE 파일을 run 폴더로 이동...
copy "%DIST_DIR%\OnBoard_OLED_Monitor.exe" "%RUN_DIR%\" >nul
if errorlevel 1 (
    echo ❌ EXE 파일 복사 실패!
    pause
    exit /b 1
)

echo ✅ EXE 파일 이동 완료: %RUN_DIR%\OnBoard_OLED_Monitor.exe
echo.

echo [9/9] 빌드 파일 정리...
echo build 폴더 삭제 중...
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%"
)

echo dist 폴더 삭제 중...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%"
)

echo spec 파일 삭제 중...
if exist "OnBoard_OLED_Monitor.spec" (
    del /q "OnBoard_OLED_Monitor.spec"
)

echo ✅ 빌드 파일 정리 완료
echo.

REM README 파일 생성
echo [추가] README 파일 생성...
(
echo OnBoard OLED Monitor - 독립 실행 파일
echo ==========================================
echo.
echo 이 폴더에는 OnBoard OLED Monitor의 독립 실행 파일이 포함되어 있습니다.
echo.
echo 파일 설명:
echo - OnBoard_OLED_Monitor.exe : 메인 프로그램 ^(독립 실행 파일^)
echo - start_monitor.bat        : 프로그램 시작 스크립트
echo - README.txt               : 이 파일
echo.
echo 사용 방법:
echo 1. OnBoard_OLED_Monitor.exe를 직접 실행하거나
echo 2. start_monitor.bat을 실행하세요
echo.
echo 시스템 요구사항:
echo - Windows 10/11 ^(64-bit^)
echo - 시리얼 포트 드라이버 설치됨
echo - USB-Serial 변환기 ^(필요시^)
echo.
echo 문제 해결:
echo - 프로그램이 실행되지 않으면 Windows Defender 예외 목록에 추가하세요
echo - COM 포트가 인식되지 않으면 드라이버를 재설치하세요
echo - 연결 문제시 다른 프로그램이 포트를 사용 중인지 확인하세요
echo.
echo 버전: v1.4 - Request-Response Protocol
echo 빌드 날짜: %date% %time%
echo.
echo 설치 위치: %RUN_DIR%
echo 실행 방법: start_monitor.bat 또는 OnBoard_OLED_Monitor.exe
) > "%RUN_DIR%\README.txt"

echo ✅ README 파일 생성: %RUN_DIR%\README.txt
echo.

echo ================================================================
echo 🎉 OnBoard OLED Monitor EXE 빌드 및 인스톨 완료!
echo ================================================================
echo.
echo 📁 설치 위치: %RUN_DIR%
echo 📄 실행 파일: OnBoard_OLED_Monitor.exe
echo 🚀 시작 스크립트: start_monitor.bat
echo 📋 사용 설명서: README.txt
echo.
echo 파일 크기: %EXE_SIZE_MB% MB
echo.
echo 💡 사용 방법:
echo 1. %RUN_DIR% 폴더로 이동
echo 2. start_monitor.bat을 실행하거나
echo 3. OnBoard_OLED_Monitor.exe를 직접 실행하세요
echo.
echo ⚠️  주의사항:
echo - 처음 실행시 Windows Defender가 차단할 수 있습니다
echo - 차단시 "추가 정보" → "실행" 클릭하여 허용하세요
echo - 또는 Windows Defender 예외 목록에 추가하세요
echo.

REM 실행 폴더 열기 옵션
set /p OPEN_FOLDER="run 폴더를 열까요? (Y/N): "
if /i "%OPEN_FOLDER%"=="Y" (
    start "" "%RUN_DIR%"
)

REM 바로 실행 옵션
set /p RUN_NOW="지금 바로 실행해보시겠습니까? (Y/N): "
if /i "%RUN_NOW%"=="Y" (
    echo.
    echo 프로그램을 시작합니다...
    start "" "%RUN_DIR%\OnBoard_OLED_Monitor.exe"
)

echo.
echo 빌드 및 인스톨이 완료되었습니다!
pause 