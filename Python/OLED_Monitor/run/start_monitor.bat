@echo off
title OnBoard OLED Monitor
echo OnBoard OLED Monitor를 시작합니다...
echo.
echo 실행 중... 창이 나타날 때까지 잠시 기다려주세요.
echo 프로그램을 종료하려면 창을 닫으세요.
echo.
"C:\Users\ym720\Git-projects\OnBoard_FW\Python\OLED_Monitor\..\..\run\OnBoard_OLED_Monitor.exe"
if errorlevel 1 (
    echo.
    echo 프로그램 실행 중 오류가 발생했습니다.
    pause
)
