@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion

REM OnBoard OLED Monitor 실행 스크립트 v2.1
REM 가상환경 자동 생성 및 패키지 자동 설치 지원 - 에러 수정 버전

title OnBoard OLED Monitor - 자동 실행기
echo ================================================================
echo   OnBoard OLED Monitor v1.4 - 자동 실행기 (개선판)
echo ================================================================
echo.

REM 현재 디렉토리 확인
set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%venv
set REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt

echo [1/6] 환경 확인 중...
echo 현재 위치: %SCRIPT_DIR%
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았거나 PATH에 등록되지 않았습니다.
    echo.
    echo 해결 방법:
    echo 1. Python 3.8 이상을 https://python.org에서 다운로드하여 설치
    echo 2. 설치시 "Add Python to PATH" 옵션 체크
    echo 3. 설치 후 CMD를 재시작하고 다시 실행
    echo.
    pause
    exit /b 1
)

echo ✅ Python 설치 확인됨
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %PYTHON_VERSION%
echo.

echo [2/6] 가상환경 확인 및 생성...
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ✅ 기존 가상환경 발견: %VENV_DIR%
) else (
    echo 🔧 가상환경이 없습니다. 자동으로 생성합니다...
    echo 가상환경 생성 중... (잠시 기다려주세요)
    
    python -m venv "%VENV_DIR%" --clear
    if errorlevel 1 (
        echo ❌ 가상환경 생성 실패!
        echo Python venv 모듈이 설치되어 있는지 확인하세요.
        pause
        exit /b 1
    )
    
    echo ✅ 가상환경 생성 완료: %VENV_DIR%
)
echo.

echo [3/6] 가상환경 활성화...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ❌ 가상환경 활성화 실패!
    echo 가상환경이 손상되었을 수 있습니다.
    
    set /p RECREATE="가상환경을 다시 생성하시겠습니까? (Y/N): "
    if /i "!RECREATE!"=="Y" (
        echo 기존 가상환경 삭제 중...
        rmdir /s /q "%VENV_DIR%"
        
        echo 새 가상환경 생성 중...
        python -m venv "%VENV_DIR%" --clear
        call "%VENV_DIR%\Scripts\activate.bat"
        
        if errorlevel 1 (
            echo ❌ 가상환경 재생성 실패!
            pause
            exit /b 1
        )
        echo ✅ 가상환경 재생성 완료
    ) else (
        pause
        exit /b 1
    )
)

echo ✅ 가상환경 활성화됨
echo 활성 Python: 
python --version
echo 가상환경 경로: %VIRTUAL_ENV%
echo.

echo [4/6] pip 업그레이드...
echo pip 업그레이드 중... (네트워크 상태에 따라 시간이 걸릴 수 있습니다)
python -m pip install --upgrade pip --quiet --disable-pip-version-check
if errorlevel 1 (
    echo ⚠️ pip 업그레이드 실패 - 기존 버전으로 계속 진행
) else (
    echo ✅ pip 업그레이드 완료
)
echo.

echo [5/6] 필수 패키지 설치 확인...

REM requirements.txt가 있으면 사용, 없으면 기본 패키지 설치
if exist "%REQUIREMENTS_FILE%" (
    echo requirements.txt 파일 발견 - 패키지 설치 중...
    pip install -r "%REQUIREMENTS_FILE%" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo ⚠️ requirements.txt 설치 중 일부 오류 발생 - 개별 패키지 설치 진행
        goto INSTALL_INDIVIDUAL
    ) else (
        echo ✅ requirements.txt 패키지 설치 완료
        goto CHECK_PACKAGES
    )
) else (
    echo requirements.txt가 없습니다 - 기본 패키지 설치 진행
    goto INSTALL_INDIVIDUAL
)

:INSTALL_INDIVIDUAL
echo 필수 패키지 개별 설치 중...

echo - pyserial 설치...
pip install pyserial --quiet --disable-pip-version-check
if errorlevel 1 echo ⚠️ pyserial 설치 실패

echo - pillow 설치...
pip install pillow --quiet --disable-pip-version-check  
if errorlevel 1 echo ⚠️ pillow 설치 실패

echo - numpy 설치...
pip install numpy --quiet --disable-pip-version-check
if errorlevel 1 echo ⚠️ numpy 설치 실패

echo ✅ 기본 패키지 설치 완료

:CHECK_PACKAGES
echo.
echo 설치된 패키지 확인...
echo 핵심 모듈 import 테스트 중...

REM 임시 Python 스크립트 파일 생성하여 모듈 테스트
echo import sys > temp_test.py
echo success = True >> temp_test.py
echo modules = ['serial', 'PIL', 'tkinter'] >> temp_test.py
echo optional_modules = ['numpy'] >> temp_test.py
echo. >> temp_test.py
echo print('✅ 필수 모듈 확인:') >> temp_test.py
echo for module in modules: >> temp_test.py
echo     try: >> temp_test.py
echo         __import__(module) >> temp_test.py
echo         print(f'  ✓ {module}') >> temp_test.py
echo     except ImportError as e: >> temp_test.py
echo         print(f'  ✗ {module} - 실패: {e}') >> temp_test.py
echo         success = False >> temp_test.py
echo. >> temp_test.py
echo print('📦 선택적 모듈 확인:') >> temp_test.py
echo for module in optional_modules: >> temp_test.py
echo     try: >> temp_test.py
echo         __import__(module) >> temp_test.py
echo         print(f'  ✓ {module}') >> temp_test.py
echo     except ImportError: >> temp_test.py
echo         print(f'  ○ {module} - 없음 (선택사항)') >> temp_test.py
echo. >> temp_test.py
echo if not success: >> temp_test.py
echo     print('') >> temp_test.py
echo     print('❌ 일부 필수 모듈이 누락되었습니다.') >> temp_test.py
echo     sys.exit(1) >> temp_test.py
echo else: >> temp_test.py
echo     print('') >> temp_test.py
echo     print('✅ 모든 필수 모듈이 정상적으로 설치되었습니다.') >> temp_test.py

REM Python 스크립트 실행
python temp_test.py
set MODULE_CHECK_RESULT=!errorlevel!

REM 임시 파일 정리
del temp_test.py >nul 2>&1

if !MODULE_CHECK_RESULT! neq 0 (
    echo.
    echo ❌ 패키지 확인 실패!
    echo 일부 필수 패키지가 제대로 설치되지 않았습니다.
    echo.
    echo 해결 방법:
    echo 1. 인터넷 연결 확인
    echo 2. 방화벽/백신 프로그램 확인
    echo 3. 관리자 권한으로 실행
    echo 4. Python 재설치 고려
    echo.
    set /p CONTINUE="패키지 문제를 무시하고 계속하시겠습니까? (Y/N): "
    if /i not "!CONTINUE!"=="Y" (
        pause
        exit /b 1
    )
) else (
    echo ✅ 패키지 확인 완료
)

echo.
echo [6/6] OnBoard OLED Monitor 시작...
echo.
echo 🚀 OnBoard OLED Monitor를 시작합니다...
echo 📡 시리얼 포트를 연결하고 GUI가 나타날 때까지 기다려주세요.
echo 🔄 프로그램을 종료하려면 창을 닫거나 Ctrl+C를 누르세요.
echo.

REM 현재 디렉토리에서 oled_monitor.py 실행
if exist "%SCRIPT_DIR%oled_monitor.py" (
    python "%SCRIPT_DIR%oled_monitor.py"
    set EXIT_CODE=!errorlevel!
) else (
    echo ❌ oled_monitor.py 파일을 찾을 수 없습니다!
    echo 파일 위치: %SCRIPT_DIR%oled_monitor.py
    echo 현재 디렉토리의 파일 목록:
    dir /b "*.py"
    set EXIT_CODE=1
)

REM 실행 완료 처리
echo.
if !EXIT_CODE! equ 0 (
    echo ✅ 프로그램이 정상적으로 종료되었습니다.
) else (
    echo ❌ 프로그램 실행 중 오류가 발생했습니다. (종료 코드: !EXIT_CODE!)
    echo.
    echo 일반적인 문제 해결:
    echo 1. COM 포트가 다른 프로그램에서 사용 중인지 확인
    echo 2. USB 케이블 연결 상태 확인  
    echo 3. 디바이스 드라이버 설치 확인
    echo 4. 윈도우 보안 프로그램 확인
)

echo.
echo 가상환경을 비활성화합니다...
deactivate

echo.
echo ================================================================
echo 감사합니다. 아무 키나 누르면 종료합니다.
echo ================================================================
pause >nul 