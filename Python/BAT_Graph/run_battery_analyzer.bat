@echo off
chcp 65001 > nul
title 배터리 로그 분석기 - STM32L412 OnBoard

echo ============================================
echo 배터리 로그 분석기 시작 중...
echo ============================================
echo.

:: 현재 디렉토리 확인
echo 현재 디렉토리: %cd%
echo.

:: Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 설정되지 않았습니다.
    echo Python 3.7 이상을 설치해주세요.
    pause
    exit /b 1
)

echo Python 버전:
python --version
echo.

:: 필요한 패키지 확인 및 설치
echo 필요한 패키지 확인 중...
echo.

:: PyQt5 확인
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo PyQt5가 설치되어 있지 않습니다. 설치 중...
    pip install PyQt5
    if errorlevel 1 (
        echo [오류] PyQt5 설치에 실패했습니다.
        pause
        exit /b 1
    )
)

:: matplotlib 확인
python -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
    echo matplotlib가 설치되어 있지 않습니다. 설치 중...
    pip install matplotlib
    if errorlevel 1 (
        echo [오류] matplotlib 설치에 실패했습니다.
        pause
        exit /b 1
    )
)

:: pandas 확인
python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo pandas가 설치되어 있지 않습니다. 설치 중...
    pip install pandas
    if errorlevel 1 (
        echo [오류] pandas 설치에 실패했습니다.
        pause
        exit /b 1
    )
)

:: numpy 확인
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo numpy가 설치되어 있지 않습니다. 설치 중...
    pip install numpy
    if errorlevel 1 (
        echo [오류] numpy 설치에 실패했습니다.
        pause
        exit /b 1
    )
)

echo 모든 패키지가 설치되어 있습니다.
echo.

:: GUI 애플리케이션 실행
echo 배터리 로그 분석기 GUI를 시작합니다...
echo 창을 닫으려면 GUI 프로그램에서 종료해주세요.
echo.

python battery_analyzer_gui.py

if errorlevel 1 (
    echo.
    echo [오류] 프로그램 실행 중 오류가 발생했습니다.
    echo 오류 내용을 확인해주세요.
    pause
) else (
    echo.
    echo 프로그램이 정상적으로 종료되었습니다.
)

pause 