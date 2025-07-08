#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배터리 테스트 데이터 분석 및 그래프 생성 스크립트
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import re

# 한글 폰트 설정 (Windows 환경 고려)
try:
    # Windows용 한글 폰트 시도
    plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except:
    # 한글 폰트가 없으면 기본 폰트 사용
    plt.rcParams['font.family'] = 'DejaVu Sans'
    print("한글 폰트를 찾을 수 없어 영어로 표시됩니다.")

def parse_battery_log(file_path):
    """
    배터리 로그 파일을 파싱하여 DataFrame으로 변환
    """
    data = []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                # 여러 공백과 탭을 하나의 구분자로 처리
                parts = re.split(r'\s+', line)
                
                # 디버깅을 위해 첫 몇 줄 출력
                if line_num <= 5:
                    print(f"라인 {line_num}: {parts}")
                
                # 최소 7개 필드가 있어야 함
                if len(parts) < 7:
                    if line_num <= 10:  # 처음 10줄만 오류 출력
                        print(f"라인 {line_num} 필드 부족: {len(parts)}개 필드 - {line}")
                    continue
                
                # 데이터 추출
                time_str = parts[0]  # 13:26:49
                battery_percent = int(parts[1].replace('%', ''))  # 98%
                timer_time = parts[2]  # 89:59
                status = parts[3]  # RUNNING
                # parts[4], parts[5]는 빈 필드일 수 있음
                led1 = parts[-3] if len(parts) >= 7 else 'X'  # X
                led2 = parts[-2] if len(parts) >= 7 else 'X'  # X
                adc_value = int(parts[-1])  # 3624
                
                # 타이머 시간을 초로 변환
                timer_parts = timer_time.split(':')
                if len(timer_parts) == 2:
                    timer_seconds = int(timer_parts[0]) * 60 + int(timer_parts[1])
                else:
                    timer_seconds = 0
                
                data.append({
                    'time': time_str,
                    'battery_percent': battery_percent,
                    'timer_minutes': int(timer_parts[0]) if len(timer_parts) == 2 else 0,
                    'timer_seconds': timer_seconds,
                    'status': status,
                    'led1': led1,
                    'led2': led2,
                    'adc_value': adc_value
                })
                
            except (ValueError, IndexError) as e:
                if line_num <= 10:  # 처음 10줄만 오류 출력
                    print(f"라인 {line_num} 파싱 오류: {line} - {e}")
                continue
    
    print(f"총 {len(data)}개의 데이터 포인트를 성공적으로 파싱했습니다.")
    return pd.DataFrame(data)

def create_battery_graphs(df, output_dir='graphs'):
    """
    배터리 데이터 그래프 생성
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 시간 인덱스 생성 (초 단위)
    df['time_index'] = range(len(df))
    df['time_minutes'] = df['time_index'] / 60  # 분 단위로 변환
    
    # 1. 배터리 퍼센트 vs 시간 그래프
    plt.figure(figsize=(15, 8))
    
    plt.subplot(2, 2, 1)
    plt.plot(df['time_minutes'], df['battery_percent'], 'b-', linewidth=2, label='배터리 잔량')
    plt.title('배터리 잔량 변화 (시간별)', fontsize=14, fontweight='bold')
    plt.xlabel('시간 (분)', fontsize=12)
    plt.ylabel('배터리 잔량 (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 2. ADC 값 vs 시간 그래프
    plt.subplot(2, 2, 2)
    plt.plot(df['time_minutes'], df['adc_value'], 'r-', linewidth=2, label='ADC 값')
    plt.title('ADC 값 변화 (시간별)', fontsize=14, fontweight='bold')
    plt.xlabel('시간 (분)', fontsize=12)
    plt.ylabel('ADC 값', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 3. 배터리 퍼센트 vs ADC 값 상관관계
    plt.subplot(2, 2, 3)
    plt.scatter(df['adc_value'], df['battery_percent'], alpha=0.6, s=1, c='green')
    plt.title('배터리 잔량 vs ADC 값 상관관계', fontsize=14, fontweight='bold')
    plt.xlabel('ADC 값', fontsize=12)
    plt.ylabel('배터리 잔량 (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 선형 회귀선 추가
    z = np.polyfit(df['adc_value'], df['battery_percent'], 1)
    p = np.poly1d(z)
    plt.plot(df['adc_value'], p(df['adc_value']), "r--", alpha=0.8, linewidth=2, label=f'추세선: y={z[0]:.4f}x{z[1]:+.2f}')
    plt.legend()
    
    # 4. 타이머 시간 vs 배터리 소모량
    plt.subplot(2, 2, 4)
    # 초기 배터리 잔량 기준으로 소모량 계산
    initial_battery = df['battery_percent'].iloc[0]
    df['battery_consumed'] = initial_battery - df['battery_percent']
    
    plt.plot(df['timer_minutes'], df['battery_consumed'], 'purple', linewidth=2, label='배터리 소모량')
    plt.title('타이머 시간 vs 배터리 소모량', fontsize=14, fontweight='bold')
    plt.xlabel('타이머 시간 (분)', fontsize=12)
    plt.ylabel('배터리 소모량 (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'battery_analysis_overview.png'), dpi=300, bbox_inches='tight')
    plt.show()
    
    # 5. 상세 배터리 잔량 그래프 (더 큰 크기)
    plt.figure(figsize=(16, 10))
    
    # 배터리 잔량 그래프
    plt.subplot(3, 1, 1)
    plt.plot(df['time_minutes'], df['battery_percent'], 'b-', linewidth=2, label='배터리 잔량')
    plt.fill_between(df['time_minutes'], df['battery_percent'], alpha=0.3, color='blue')
    plt.title('배터리 잔량 변화 (상세)', fontsize=16, fontweight='bold')
    plt.xlabel('시간 (분)', fontsize=14)
    plt.ylabel('배터리 잔량 (%)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # ADC 값 그래프
    plt.subplot(3, 1, 2)
    plt.plot(df['time_minutes'], df['adc_value'], 'r-', linewidth=2, label='ADC 값')
    plt.fill_between(df['time_minutes'], df['adc_value'], alpha=0.3, color='red')
    plt.title('ADC 값 변화 (상세)', fontsize=16, fontweight='bold')
    plt.xlabel('시간 (분)', fontsize=14)
    plt.ylabel('ADC 값', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # 배터리 소모율 그래프
    plt.subplot(3, 1, 3)
    # 시간당 배터리 소모율 계산 (이동평균 사용)
    window_size = 60  # 60초 윈도우
    df['battery_consumption_rate'] = df['battery_percent'].rolling(window=window_size, center=True).apply(
        lambda x: (x.iloc[0] - x.iloc[-1]) if len(x) == window_size else 0
    )
    
    plt.plot(df['time_minutes'], df['battery_consumption_rate'], 'green', linewidth=2, label='배터리 소모율 (%/분)')
    plt.title('배터리 소모율 변화', fontsize=16, fontweight='bold')
    plt.xlabel('시간 (분)', fontsize=14)
    plt.ylabel('소모율 (%/분)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'battery_detailed_analysis.png'), dpi=300, bbox_inches='tight')
    plt.show()

def generate_statistics(df):
    """
    배터리 테스트 통계 생성
    """
    print("=" * 60)
    print("배터리 테스트 통계 분석")
    print("=" * 60)
    
    # 기본 통계
    print(f"테스트 시간: {len(df)} 초 ({len(df)/60:.1f} 분)")
    print(f"초기 배터리 잔량: {df['battery_percent'].iloc[0]}%")
    print(f"최종 배터리 잔량: {df['battery_percent'].iloc[-1]}%")
    print(f"총 배터리 소모량: {df['battery_percent'].iloc[0] - df['battery_percent'].iloc[-1]}%")
    
    # ADC 값 통계
    print(f"\nADC 값 통계:")
    print(f"  최대값: {df['adc_value'].max()}")
    print(f"  최소값: {df['adc_value'].min()}")
    print(f"  평균값: {df['adc_value'].mean():.1f}")
    print(f"  표준편차: {df['adc_value'].std():.1f}")
    
    # 배터리 소모율 계산
    test_duration_hours = len(df) / 3600
    total_consumption = df['battery_percent'].iloc[0] - df['battery_percent'].iloc[-1]
    consumption_rate_per_hour = total_consumption / test_duration_hours
    
    print(f"\n배터리 소모율:")
    print(f"  시간당 소모율: {consumption_rate_per_hour:.2f}%/시간")
    print(f"  예상 총 사용시간: {100 / consumption_rate_per_hour:.1f} 시간")
    
    # 배터리 잔량별 ADC 값 범위
    print(f"\n배터리 잔량별 ADC 값 범위:")
    for percent in [100, 95, 90, 85, 80, 75, 70]:
        mask = (df['battery_percent'] >= percent-2) & (df['battery_percent'] <= percent+2)
        if mask.any():
            adc_range = df.loc[mask, 'adc_value']
            print(f"  {percent}%: {adc_range.min()} - {adc_range.max()} (평균: {adc_range.mean():.0f})")

def main():
    # 파일 경로 설정
    log_file = "run/LOG/BAT_TEST_3A.txt"
    
    if not os.path.exists(log_file):
        print(f"로그 파일을 찾을 수 없습니다: {log_file}")
        return
    
    print("배터리 테스트 로그 파일 분석 중...")
    
    # 데이터 파싱
    df = parse_battery_log(log_file)
    
    if df.empty:
        print("파싱된 데이터가 없습니다.")
        return
    
    print(f"총 {len(df)}개의 데이터 포인트를 파싱했습니다.")
    
    # 통계 생성
    generate_statistics(df)
    
    # 그래프 생성
    print("\n그래프 생성 중...")
    create_battery_graphs(df)
    
    print("분석 완료!")

if __name__ == "__main__":
    main() 