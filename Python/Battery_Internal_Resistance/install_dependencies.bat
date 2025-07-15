@echo off
chcp 65001 >nul
title 배터리 내부저항 계산기 - 의존성 설치

echo ================================================
echo 배터리 내부저항 계산기 의존성 설치
echo ================================================
echo.
echo 필요한 Python 패키지들을 설치합니다...
echo.

REM 현재 디렉토리를 스크립트 위치로 설정
cd /d "%~dp0"

REM Python 가상환경 확인
if exist "..\..\venv\Scripts\python.exe" (
    echo 가상환경을 사용합니다.
    set PYTHON_CMD="..\..\venv\Scripts\python.exe"
    set PIP_CMD="..\..\venv\Scripts\pip.exe"
) else if exist "venv\Scripts\python.exe" (
    echo 로컬 가상환경을 사용합니다.
    set PYTHON_CMD="venv\Scripts\python.exe"
    set PIP_CMD="venv\Scripts\pip.exe"
) else (
    echo 시스템 Python을 사용합니다.
    set PYTHON_CMD=python
    set PIP_CMD=pip
)

echo.
echo Python 버전 확인...
%PYTHON_CMD% --version

echo.
echo pip 업그레이드...
%PIP_CMD% install --upgrade pip

echo.
echo 필요한 패키지 설치...
%PIP_CMD% install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ================================================
    echo 패키지 설치 중 오류가 발생했습니다!
    echo ================================================
    echo.
    echo 개별 패키지 설치를 시도합니다...
    
    echo matplotlib 설치...
    %PIP_CMD% install matplotlib>=3.5.0
    
    echo numpy 설치...
    %PIP_CMD% install numpy>=1.21.0
    
    echo pandas 설치...
    %PIP_CMD% install pandas>=1.3.0
    
    echo openpyxl 설치...
    %PIP_CMD% install openpyxl>=3.0.0
    
    echo scikit-learn 설치...
    %PIP_CMD% install scikit-learn>=1.0.0
    
    echo seaborn 설치...
    %PIP_CMD% install seaborn>=0.11.0
    
    echo.
    echo 개별 설치가 완료되었습니다.
) else (
    echo.
    echo ================================================
    echo 모든 패키지가 성공적으로 설치되었습니다!
    echo ================================================
)

echo.
echo 설치된 패키지 목록:
%PIP_CMD% list | findstr -i "matplotlib numpy pandas openpyxl scikit-learn seaborn"

echo.
echo 설치가 완료되었습니다.
echo 이제 run_basic.bat 또는 run_advanced.bat를 실행할 수 있습니다.
echo.
pause 