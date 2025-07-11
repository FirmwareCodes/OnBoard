#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
충전 이벤트 감지 기능 테스트 스크립트
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from battery_log_parser import BatteryLogParser

def create_test_data_with_charging_events():
    """충전 이벤트가 포함된 테스트 데이터 생성"""
    
    # 기본 설정
    num_points = 200
    start_time = datetime.now() - timedelta(hours=2)
    
    # 시간 배열
    timestamps = [start_time + timedelta(seconds=i*30) for i in range(num_points)]
    
    # 기본 방전 곡선 (25.2V → 20V)
    base_discharge = np.linspace(25.2, 20.0, num_points)
    
    # 노이즈 추가
    noise = np.random.normal(0, 0.03, num_points)
    voltages = base_discharge + noise
    
    # 충전 이벤트 삽입
    # 이벤트 1: 50번째 포인트에서 급격한 상승 (부하 종료)
    for i in range(50, 60):
        if i < len(voltages):
            voltages[i] += (i - 49) * 0.3  # 0.3V씩 상승
    
    # 이벤트 2: 100번째 포인트에서 충전 시작
    for i in range(100, 120):
        if i < len(voltages):
            voltages[i] += (i - 99) * 0.15 + 1.5  # 1.5V 급상승 후 점진적 상승
    
    # 이벤트 3: 150번째 포인트에서 또 다른 부하 종료
    for i in range(150, 155):
        if i < len(voltages):
            voltages[i] += (i - 149) * 0.4  # 0.4V씩 급상승
    
    # 데이터프레임 생성
    data = []
    for i, (timestamp, voltage) in enumerate(zip(timestamps, voltages)):
        data.append({
            'timestamp': timestamp,
            'battery': voltage,
            'source': 'test_with_charging'
        })
    
    return pd.DataFrame(data)

def test_charging_detection():
    """충전 이벤트 감지 테스트"""
    print("=" * 60)
    print("충전 이벤트 감지 기능 테스트")
    print("=" * 60)
    
    # 테스트 데이터 생성
    print("1. 충전 이벤트가 포함된 테스트 데이터 생성...")
    test_data = create_test_data_with_charging_events()
    print(f"   생성된 데이터: {len(test_data)}개 포인트")
    
    # 파서 초기화
    parser = BatteryLogParser()
    
    # 충전 이벤트 감지 및 필터링
    print("\n2. 충전 이벤트 감지 및 필터링...")
    filtered_df, charging_events, original_count, filtered_count = parser.detect_and_filter_charging_events(test_data)
    
    print(f"   원본 데이터: {original_count}개")
    print(f"   필터링된 데이터: {filtered_count}개")
    print(f"   제외된 데이터: {original_count - filtered_count}개")
    print(f"   감지된 이벤트: {len(charging_events)}개")
    
    # 이벤트 상세 정보
    print("\n3. 감지된 이벤트 상세 정보:")
    for i, event in enumerate(charging_events, 1):
        print(f"   이벤트 {i}:")
        print(f"     타입: {event['event_type']}")
        print(f"     시간: {event['start_time'].strftime('%H:%M:%S')} ~ {event['end_time'].strftime('%H:%M:%S')}")
        print(f"     전압 변화: {event['start_voltage']:.2f}V → {event['end_voltage']:.2f}V")
        print(f"     상승량: +{event['voltage_increase']:.2f}V")
        print(f"     지속시간: {event['duration_records']}개 레코드")
        print(f"     인덱스: {event['start_index']} ~ {event['end_index']}")
        print()
    
    # 분석 테스트
    print("4. 필터링된 데이터로 배터리 분석...")
    analysis = parser.analyze_battery_performance(
        df=test_data,
        load_watts=50,
        battery_capacity_ah=2.5,
        battery_type='6s'
    )
    
    if analysis:
        print("   분석 완료!")
        
        # 데이터 품질 정보
        if 'original_data_info' in analysis:
            original_info = analysis['original_data_info']
            filtered_info = analysis['filtered_data_info']
            
            print(f"   원본 데이터: {original_info['total_records']}개 레코드")
            print(f"   분석 데이터: {filtered_info['analysis_records']}개 레코드")
            print(f"   데이터 품질: {filtered_info['data_quality']}")
            print(f"   충전 이벤트: {original_info['charging_events']}개")
        
        # 추천 전압 정보
        if 'voltage_recommendations' in analysis:
            voltage_rec = analysis['voltage_recommendations']
            print(f"   추천 충전 완료 전압: {voltage_rec['recommended_100_percent']:.1f}V")
            print(f"   추천 방전 종료 전압: {voltage_rec['recommended_0_percent']:.1f}V")
        
        # 건강도
        if 'health_assessment' in analysis:
            health = analysis['health_assessment']
            print(f"   배터리 건강도: {health['health_score']}/100 ({health['health_grade']})")
    
    # 시각화
    print("\n5. 결과 시각화...")
    create_visualization(test_data, filtered_df, charging_events)
    
    return test_data, filtered_df, charging_events, analysis

def create_visualization(original_data, filtered_data, charging_events):
    """결과 시각화"""
    plt.figure(figsize=(15, 10))
    plt.rcParams['font.family'] = ['Malgun Gothic', 'NanumGothic', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 서브플롯 1: 원본 데이터
    plt.subplot(2, 2, 1)
    plt.plot(original_data.index, original_data['battery'], 'b-', linewidth=2, label='원본 데이터')
    
    # 충전 이벤트 구간 강조
    for event in charging_events:
        start_idx = event['start_index']
        end_idx = event['end_index']
        plt.axvspan(start_idx, end_idx, alpha=0.3, color='red', label=f'{event["event_type"]}')
    
    plt.title('원본 데이터 (충전 이벤트 포함)')
    plt.xlabel('시간 (레코드)')
    plt.ylabel('전압 (V)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 서브플롯 2: 필터링된 데이터
    plt.subplot(2, 2, 2)
    plt.plot(filtered_data.index, filtered_data['battery'], 'g-', linewidth=2, label='필터링된 데이터')
    plt.title('필터링된 데이터 (충전 이벤트 제외)')
    plt.xlabel('시간 (레코드)')
    plt.ylabel('전압 (V)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 서브플롯 3: 전압 변화율
    plt.subplot(2, 2, 3)
    original_diff = original_data['battery'].diff()
    plt.plot(original_data.index[1:], original_diff[1:], 'r-', linewidth=1, label='전압 변화율')
    plt.axhline(y=0.2, color='orange', linestyle='--', label='감지 임계값 (0.2V)')
    plt.title('전압 변화율 분석')
    plt.xlabel('시간 (레코드)')
    plt.ylabel('전압 변화 (V/record)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 서브플롯 4: 데이터 비교
    plt.subplot(2, 2, 4)
    plt.plot(original_data.index, original_data['battery'], 'b-', alpha=0.5, linewidth=1, label='원본')
    plt.plot(filtered_data.index, filtered_data['battery'], 'g-', linewidth=2, label='필터링됨')
    
    # 제거된 구간 표시
    all_indices = set(original_data.index)
    filtered_indices = set(filtered_data.index)
    excluded_indices = sorted(all_indices - filtered_indices)
    
    if excluded_indices:
        excluded_voltages = original_data.loc[excluded_indices, 'battery']
        plt.scatter(excluded_indices, excluded_voltages, c='red', s=20, alpha=0.7, label='제외된 데이터')
    
    plt.title('데이터 비교')
    plt.xlabel('시간 (레코드)')
    plt.ylabel('전압 (V)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('charging_event_detection_test.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("   시각화 완료! 'charging_event_detection_test.png' 파일이 저장되었습니다.")

def save_test_log_file():
    """테스트용 OnBoard 로그 파일 저장"""
    test_data = create_test_data_with_charging_events()
    
    filename = 'test_onboard_log_with_charging.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        for _, row in test_data.iterrows():
            time_str = row['timestamp'].strftime('%H:%M:%S')
            voltage_str = f"{row['battery']:.2f}V"
            
            # OnBoard 로그 형식으로 저장
            line = f"{time_str}\t\t{voltage_str}\t00:00\t\tSTANDBY\t\tX\tX\t3750\n"
            f.write(line)
    
    print(f"테스트 로그 파일 저장: {filename}")
    return filename

if __name__ == '__main__':
    try:
        # 충전 이벤트 감지 테스트 실행
        original, filtered, events, analysis = test_charging_detection()
        
        # 테스트 로그 파일 저장
        print("\n" + "=" * 60)
        print("테스트 로그 파일 생성")
        print("=" * 60)
        log_file = save_test_log_file()
        
        print(f"\n✅ 테스트 완료!")
        print(f"📄 생성된 파일:")
        print(f"   - {log_file} (GUI 테스트용 로그 파일)")
        print(f"   - charging_event_detection_test.png (시각화 결과)")
        
        print(f"\n📊 테스트 결과 요약:")
        print(f"   - 원본 데이터: {len(original)}개 포인트")
        print(f"   - 필터링된 데이터: {len(filtered)}개 포인트")
        print(f"   - 감지된 충전 이벤트: {len(events)}개")
        print(f"   - 데이터 제외율: {(len(original) - len(filtered)) / len(original) * 100:.1f}%")
        
        if analysis and 'voltage_recommendations' in analysis:
            voltage_rec = analysis['voltage_recommendations']
            print(f"\n🎯 추천 전압 설정:")
            print(f"   - 충전 완료: {voltage_rec['recommended_100_percent']:.1f}V")
            print(f"   - 방전 종료: {voltage_rec['recommended_0_percent']:.1f}V")
        
        print(f"\n💡 GUI 테스트 방법:")
        print(f"   1. battery_analyzer_gui.py 실행")
        print(f"   2. '{log_file}' 파일 선택")
        print(f"   3. 부하 설정 후 분석 시작")
        print(f"   4. '데이터 품질 및 이벤트' 패널에서 충전 이벤트 확인")
        print(f"   5. '추천 전압 설정' 패널에서 권장 전압 확인")
        
    except Exception as e:
        print(f"테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc() 