@echo off
chcp 65001 >nul
title 배터리 내부저항 계산기 (부하 전류 기반)

echo ================================================
echo 배터리 내부저항 계산기 (부하 전류 기반)
echo ================================================
echo.
echo 키르히호프 법칙 기반 정확한 계산 프로그램을 시작합니다...
echo - 부하 전류를 포함한 정밀 계산
echo - 6S 배터리 전용 지원
echo - 계산 과정 단계별 표시
echo - 측정 시간 검증 기능
echo.

REM 현재 디렉토리를 스크립트 위치로 설정
cd /d "%~dp0"

REM Python 가상환경 확인 및 활성화
if exist "..\..\venv\Scripts\python.exe" (
    echo 가상환경을 사용합니다.
    "..\..\venv\Scripts\python.exe" battery_resistance_calculator.py
) else if exist "venv\Scripts\python.exe" (
    echo 로컬 가상환경을 사용합니다.
    "venv\Scripts\python.exe" battery_resistance_calculator.py
) else (
    echo 시스템 Python을 사용합니다.
    python battery_resistance_calculator.py
)

if errorlevel 1 (
    echo.
    echo ================================================
    echo 오류가 발생했습니다!
    echo ================================================
    echo 가능한 해결 방법:
    echo 1. Python이 설치되어 있는지 확인하세요
    echo 2. 필요한 패키지를 설치하세요: pip install -r requirements.txt
    echo 3. 가상환경이 올바르게 설정되어 있는지 확인하세요
    echo.
    pause
) else (
    echo.
    echo 프로그램이 정상적으로 종료되었습니다.
)

echo.
pause 