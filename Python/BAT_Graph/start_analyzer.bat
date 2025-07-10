@echo off
chcp 65001 >nul
title 배터리 로그 분석기

echo ================================================
echo    배터리 로그 분석기 v1.0
echo    Battery Log Analyzer
echo ================================================
echo.

cd /d "%~dp0"

echo Python 설치 확인...
python --version >nul 2>&1
if errorlevel 1 (
    echo 오류: Python이 설치되지 않았거나 PATH에 등록되지 않았습니다.
    echo Python 3.8 이상을 설치하고 PATH에 등록해주세요.
    echo.
    pause
    exit /b 1
)

echo.
echo 프로그램을 실행합니다...
echo.

python run_analyzer.py

if errorlevel 1 (
    echo.
    echo 프로그램 실행 중 오류가 발생했습니다.
    echo.
)

pause 