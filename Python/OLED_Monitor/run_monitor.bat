@echo off
chcp 65001 > nul 2>&1
REM OnBoard OLED Monitor 실행 스크립트 (Windows)
REM 
REM 이 배치 파일은 Python 가상환경을 활성화하고
REM OLED Monitor를 실행합니다.

echo ======================================
echo   OnBoard OLED Monitor v1.0
echo ======================================
echo.

REM 현재 디렉토리 확인
echo 현재 위치: %CD%
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았거나 PATH에 등록되지 않았습니다.
    echo Python 3.7 이상을 설치해주세요.
    pause
    exit /b 1
)

echo Python 버전:
python --version
echo.

REM 가상환경 존재 확인
if exist "venv\Scripts\activate.bat" (
    echo 가상환경을 활성화합니다...
    call venv\Scripts\activate.bat
    echo 가상환경 활성화 완료.
    echo.
) else (
    echo [경고] 가상환경이 없습니다. 전역 Python 환경을 사용합니다.
    echo 권장사항: python -m venv venv 명령으로 가상환경을 생성하세요.
    echo.
)

REM 필수 패키지 확인
echo 필수 패키지 확인 중...
python -c "import serial, PIL, numpy, tkinter" >nul 2>&1
if errorlevel 1 (
    echo [경고] 일부 필수 패키지가 설치되지 않았습니다.
    echo 패키지를 설치하시겠습니까? (Y/N)
    set /p install_packages=
    if /i "%install_packages%"=="Y" (
        echo 패키지 설치 중...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [오류] 패키지 설치에 실패했습니다.
            pause
            exit /b 1
        )
        echo 패키지 설치 완료.
        echo.
    )
)

REM OLED Monitor 실행
echo OnBoard OLED Monitor를 시작합니다...
echo 프로그램을 종료하려면 창을 닫거나 Ctrl+C를 누르세요.
echo.

python oled_monitor.py

REM 실행 완료 처리
if errorlevel 1 (
    echo.
    echo [오류] 프로그램 실행 중 오류가 발생했습니다.
    echo 로그 파일을 확인하거나 개발자에게 문의하세요.
) else (
    echo.
    echo 프로그램이 정상적으로 종료되었습니다.
)

echo.
echo 아무 키나 누르면 종료합니다...
pause >nul 