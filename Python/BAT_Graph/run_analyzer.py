#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배터리 로그 분석기 실행 스크립트
Battery Log Analyzer Launcher

실행 방법:
1. 터미널에서: python run_analyzer.py
2. 또는 직접 파일을 더블클릭하여 실행

요구사항:
- Python 3.8 이상
- requirements.txt에 명시된 패키지들
"""

import sys
import os
import subprocess
import importlib.util

def check_python_version():
    """Python 버전 확인"""
    if sys.version_info < (3, 8):
        print("오류: Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: {sys.version}")
        return False
    return True

def check_required_packages():
    """필수 패키지 설치 확인"""
    required_packages = {
        'PyQt5': 'PyQt5',
        'pandas': 'pandas', 
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'scipy': 'scipy',
        'sklearn': 'scikit-learn'
    }
    
    missing_packages = []
    
    for module_name, package_name in required_packages.items():
        try:
            importlib.import_module(module_name)
            print(f"✓ {package_name} 설치됨")
        except ImportError:
            print(f"✗ {package_name} 설치 필요")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n누락된 패키지: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_packages)}")
        
        # 자동 설치 시도
        try_install = input("\n자동으로 설치하시겠습니까? (y/n): ").lower().strip()
        if try_install in ['y', 'yes', '예']:
            return install_packages(missing_packages)
        return False
    
    return True

def install_packages(packages):
    """패키지 자동 설치"""
    try:
        print("패키지를 설치하는 중...")
        cmd = [sys.executable, '-m', 'pip', 'install'] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 모든 패키지가 성공적으로 설치되었습니다!")
            return True
        else:
            print("✗ 패키지 설치에 실패했습니다:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ 설치 중 오류가 발생했습니다: {e}")
        return False

def check_files():
    """필요한 파일들이 존재하는지 확인"""
    required_files = [
        'battery_log_analyzer.py',
        'battery_log_parser.py', 
        'battery_analytics.py'
    ]
    
    missing_files = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for file_name in required_files:
        file_path = os.path.join(current_dir, file_name)
        if os.path.exists(file_path):
            print(f"✓ {file_name} 존재")
        else:
            print(f"✗ {file_name} 없음")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"\n누락된 파일: {', '.join(missing_files)}")
        return False
    
    return True

def create_test_data():
    """테스트용 로그 파일 생성"""
    try:
        from battery_log_parser import BatteryLogParser
        import pandas as pd
        from datetime import datetime, timedelta
        
        print("테스트 데이터를 생성하는 중...")
        
        parser = BatteryLogParser()
        test_data = parser.generate_test_data(1000, 24)
        
        # CSV 파일로 저장
        csv_file = "test_battery_log.csv"
        test_data.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"✓ 테스트 파일 생성됨: {csv_file}")
        
        # 텍스트 로그 파일로도 저장
        log_file = "test_battery_log.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("# 배터리 로그 테스트 데이터\n")
            f.write(f"# 생성일시: {datetime.now()}\n\n")
            
            for _, row in test_data.iterrows():
                timestamp = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                battery = row['battery']
                f.write(f"{timestamp} - BAT: {battery:.3f}V\n")
        
        print(f"✓ 테스트 로그 파일 생성됨: {log_file}")
        
        return True
        
    except Exception as e:
        print(f"✗ 테스트 데이터 생성 실패: {e}")
        return False

def run_analyzer():
    """배터리 로그 분석기 실행"""
    try:
        print("배터리 로그 분석기를 시작하는 중...")
        
        # 현재 디렉토리를 시스템 경로에 추가
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 분석기 실행
        from battery_log_analyzer import main
        main()
        
    except Exception as e:
        print(f"✗ 프로그램 실행 중 오류 발생: {e}")
        print("\n오류 세부사항:")
        import traceback
        traceback.print_exc()
        
        input("\n아무 키나 누르면 종료됩니다...")

def show_help():
    """도움말 표시"""
    help_text = """
=== 배터리 로그 분석기 v1.0 ===

프로그램 기능:
1. 다양한 형식의 배터리 로그 파일 파싱 (CSV, JSON, TXT, LOG)
2. 실시간 그래프 시각화 (시계열, 히스토그램, 박스플롯, 산점도)
3. 상세 분석 (이동평균, 변화율, 이상치 감지, 주기성 분석)
4. 배터리 건강도 평가 및 예측
5. 구간별 상세 분석
6. HTML/PDF 보고서 생성

사용 방법:
1. 프로그램 실행 후 '로그 파일 선택' 버튼 클릭
2. 분석할 배터리 로그 파일 선택
3. '분석 시작' 버튼 클릭
4. 결과 확인 및 필터 적용
5. 필요시 '보고서 저장' 버튼으로 결과 저장

지원 파일 형식:
- CSV: timestamp, battery 컬럼 포함
- JSON: 시계열 데이터 형태
- TXT/LOG: 자유 형식 텍스트 로그

문제 해결:
- 패키지 설치 오류 시: pip install -r requirements.txt
- PyQt5 오류 시: 시스템에 맞는 버전 설치 필요
- 파일 인코딩 오류 시: UTF-8로 저장된 파일 사용

지원: 개발자에게 문의
"""
    print(help_text)

def main():
    """메인 함수"""
    print("=" * 50)
    print("    배터리 로그 분석기 v1.0")
    print("    Battery Log Analyzer")
    print("=" * 50)
    print()
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            show_help()
            return
        elif sys.argv[1] in ['-t', '--test', 'test']:
            if check_files():
                create_test_data()
            return
    
    # 시스템 요구사항 확인
    print("시스템 요구사항을 확인하는 중...")
    if not check_python_version():
        input("아무 키나 누르면 종료됩니다...")
        return
    
    print("\n필수 패키지를 확인하는 중...")
    if not check_required_packages():
        input("아무 키나 누르면 종료됩니다...")
        return
    
    print("\n필요한 파일들을 확인하는 중...")
    if not check_files():
        print("\n누락된 파일이 있습니다. 전체 프로그램을 다시 다운로드하세요.")
        input("아무 키나 누르면 종료됩니다...")
        return
    
    print("\n✓ 모든 요구사항이 충족되었습니다!")
    print("\n프로그램을 시작합니다...")
    
    # 테스트 데이터 생성 여부 확인
    if not os.path.exists("test_battery_log.csv"):
        create_test = input("\n테스트용 데이터를 생성하시겠습니까? (y/n): ").lower().strip()
        if create_test in ['y', 'yes', '예']:
            create_test_data()
    
    # 프로그램 실행
    run_analyzer()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
        input("\n아무 키나 누르면 종료됩니다...") 