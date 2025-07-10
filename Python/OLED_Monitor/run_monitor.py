# -*- coding: utf-8 -*-
"""
OLED 모니터 실행 스크립트
패키지 경로 설정 및 애플리케이션 실행
"""

import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 메인 애플리케이션 실행
if __name__ == "__main__":
    try:
        from oled_monitor_optimized import OptimizedOLEDMonitor
        
        print("OLED 모니터 시작 중...")
        app = OptimizedOLEDMonitor()
        app.run()
        
    except ImportError as e:
        print(f"모듈 import 오류: {e}")
        print("필요한 모듈이 설치되어 있는지 확인하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"애플리케이션 실행 오류: {e}")
        sys.exit(1) 