@echo off
chcp 65001 >nul
title OnBoard OLED Monitor
echo OnBoard OLED Monitor를 시작합니다...
echo.
echo 실행 중... 창이 나타날 때까지 잠시 기다려주세요.
echo 프로그램을 종료하려면 창을 닫으세요.
echo.
"%~dp0OnBoard_OLED_Monitor.exe"
if errorlevel 1 (
    echo.
    echo 프로그램 실행 중 오류가 발생했습니다.
    pause
)
