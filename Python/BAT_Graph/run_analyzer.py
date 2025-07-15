#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OnBoard 배터리 로그 분석기 실행 스크립트
- 단일파일 분석중 옵션 변경시 응답없음 문제 해결
- 성능 최적화 및 UI 응답성 개선
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """메인 실행 함수"""
    try:
        # 배터리 로그 분석기 임포트 및 실행
        from battery_log_analyzer import main as analyzer_main
        
        print("🔋 OnBoard 배터리 로그 분석기 v2.1 시작")
        print("📈 최적화된 UI 응답성 - 옵션 변경시 응답없음 문제 해결")
        print("=" * 60)
        
        # 분석기 실행
        analyzer_main()
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 오류: {e}")
        print("필요한 패키지를 설치하세요:")
        print("pip install pandas numpy matplotlib PyQt5 seaborn scikit-learn")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 