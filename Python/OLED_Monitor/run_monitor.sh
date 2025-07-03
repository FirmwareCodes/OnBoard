#!/bin/bash
# OnBoard OLED Monitor 실행 스크립트 (Linux/macOS)
# 
# 이 스크립트는 Python 가상환경을 활성화하고
# OLED Monitor를 실행합니다.

echo "======================================"
echo "  OnBoard OLED Monitor v1.0"
echo "======================================"
echo

# 현재 디렉토리 확인
echo "현재 위치: $(pwd)"
echo

# Python 설치 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3이 설치되지 않았습니다."
    echo "Python 3.7 이상을 설치해주세요."
    read -p "아무 키나 누르면 종료합니다..."
    exit 1
fi

echo "Python 버전:"
python3 --version
echo

# 가상환경 존재 확인
if [ -f "venv/bin/activate" ]; then
    echo "가상환경을 활성화합니다..."
    source venv/bin/activate
    echo "가상환경 활성화 완료."
    echo
    PYTHON_CMD="python"
else
    echo "[경고] 가상환경이 없습니다. 전역 Python 환경을 사용합니다."
    echo "권장사항: python3 -m venv venv 명령으로 가상환경을 생성하세요."
    echo
    PYTHON_CMD="python3"
fi

# 필수 패키지 확인
echo "필수 패키지 확인 중..."
if ! $PYTHON_CMD -c "import serial, PIL, numpy, tkinter" &> /dev/null; then
    echo "[경고] 일부 필수 패키지가 설치되지 않았습니다."
    echo -n "패키지를 설치하시겠습니까? (y/N): "
    read install_packages
    if [[ "$install_packages" =~ ^[Yy]$ ]]; then
        echo "패키지 설치 중..."
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "[오류] 패키지 설치에 실패했습니다."
            read -p "아무 키나 누르면 종료합니다..."
            exit 1
        fi
        echo "패키지 설치 완료."
        echo
    fi
fi

# 권한 확인 (시리얼 포트 접근)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! groups | grep -q "dialout"; then
        echo "[경고] 시리얼 포트 접근 권한이 없을 수 있습니다."
        echo "다음 명령으로 권한을 부여하세요:"
        echo "sudo usermod -a -G dialout \$USER"
        echo "이후 로그아웃/로그인하거나 재부팅하세요."
        echo
    fi
fi

# OLED Monitor 실행
echo "OnBoard OLED Monitor를 시작합니다..."
echo "프로그램을 종료하려면 창을 닫거나 Ctrl+C를 누르세요."
echo

$PYTHON_CMD oled_monitor.py

# 실행 완료 처리
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo
    echo "[오류] 프로그램 실행 중 오류가 발생했습니다. (종료 코드: $exit_code)"
    echo "로그 파일을 확인하거나 개발자에게 문의하세요."
else
    echo
    echo "프로그램이 정상적으로 종료되었습니다."
fi

echo
read -p "아무 키나 누르면 종료합니다..." 