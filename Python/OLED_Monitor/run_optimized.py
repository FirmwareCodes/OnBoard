# -*- coding: utf-8 -*-
"""
OLED Monitor 최적화 버전 실행 스크립트
"""

import sys
import os
import logging

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('oled_monitor.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_dependencies():
    """의존성 확인"""
    required_packages = [
        'tkinter',
        'numpy',
        'PIL',
        'serial',
        'json'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            elif package == 'numpy':
                import numpy
            elif package == 'PIL':
                from PIL import Image, ImageTk
            elif package == 'serial':
                import serial
            elif package == 'json':
                import json
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"다음 패키지가 필요합니다: {', '.join(missing_packages)}")
        print("pip install numpy pillow pyserial 명령으로 설치하세요.")
        return False
    
    return True

def main():
    """메인 함수"""
    print("OLED Monitor 최적화 버전 시작...")
    
    # 로깅 설정
    setup_logging()
    
    # 의존성 확인
    if not check_dependencies():
        print("의존성 확인 실패. 프로그램을 종료합니다.")
        sys.exit(1)
    
    try:
        # 최적화된 OLED 모니터 실행
        from oled_monitor_optimized import OptimizedOLEDMonitor
        
        app = OptimizedOLEDMonitor()
        app.run()
        
    except ImportError as e:
        print(f"모듈 임포트 오류: {e}")
        print("모든 모듈이 올바르게 설치되었는지 확인하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"애플리케이션 실행 오류: {e}")
        logging.error(f"애플리케이션 실행 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 