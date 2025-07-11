import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
import json
import struct
from typing import Dict, List, Optional, Union
import os
import matplotlib.pyplot as plt
import seaborn as sns

class BatteryLogParser:
    """배터리 로그 파서 클래스"""
    
    def __init__(self):
        self.supported_formats = [
            'onboard_monitor',  # OnBoard 모니터 로그
            'general_battery',  # 일반 배터리 로그
            'csv_format',       # CSV 형식
            'json_format'       # JSON 형식
        ]
        
        # 배터리 타입별 기본 설정
        self.battery_configs = {
            '6s': {
                'nominal_voltage': 22.2,  # 3.7V × 6
                'max_voltage': 25.2,      # 4.2V × 6
                'min_voltage': 18.0,      # 3.0V × 6 (절대 최소값)
                'cutoff_voltage': 18.0,   # 3.0V × 6 (OnBoard 시스템 실제 사용 최소값)
                'recommended_100_voltage': 25.2,  # 추천 100% 전압
                'recommended_0_voltage': 19.8,    # 추천 0% 전압 (3.3V × 6)
                'cells': 6,
                'cell_nominal': 3.7
            },
            '3s': {
                'nominal_voltage': 11.1,  # 3.7V × 3
                'max_voltage': 12.6,      # 4.2V × 3
                'min_voltage': 9.0,       # 3.0V × 3
                'cutoff_voltage': 9.0,    # 3.0V × 3 (실제 사용 최소값)
                'recommended_100_voltage': 12.6,  # 추천 100% 전압
                'recommended_0_voltage': 9.9,     # 추천 0% 전압 (3.3V × 3)
                'cells': 3,
                'cell_nominal': 3.7
            },
            'single': {
                'nominal_voltage': 3.7,
                'max_voltage': 4.2,
                'min_voltage': 3.0,
                'cutoff_voltage': 3.0,    # 실제 사용 최소값
                'recommended_100_voltage': 4.2,   # 추천 100% 전압
                'recommended_0_voltage': 3.3,     # 추천 0% 전압
                'cells': 1,
                'cell_nominal': 3.7
            }
        }
    
    def parse_log_file(self, file_path):
        """
        로그 파일을 파싱하여 DataFrame 반환
        
        Args:
            file_path: 로그 파일 경로
            
        Returns:
            DataFrame: 파싱된 데이터
        """
        if not os.path.exists(file_path):
            print(f"파일을 찾을 수 없습니다: {file_path}")
            return None
        
        try:
            # 파일 형식 자동 감지
            file_format = self.detect_file_format(file_path)
            print(f"감지된 파일 형식: {file_format}")
            
            # 형식에 따른 파싱
            if file_format == 'onboard_monitor':
                return self.parse_onboard_monitor_log(file_path)
            elif file_format == 'csv_format':
                return self.parse_csv_log(file_path)
            elif file_format == 'json_format':
                return self.parse_json_log(file_path)
            else:
                return self.parse_general_battery_log(file_path)
                
        except Exception as e:
            print(f"파일 파싱 오류: {e}")
            return None
    
    def detect_file_format(self, file_path):
        """파일 형식 자동 감지"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 처음 몇 줄을 읽어서 형식 판단
                sample_lines = [f.readline().strip() for _ in range(5)]
                sample_lines = [line for line in sample_lines if line]  # 빈 줄 제거
            
            if not sample_lines:
                return 'general_battery'
            
            # OnBoard 모니터 로그 감지
            # 형식: 13:49:50		25.22V	00:00		STANDBY		X	X	3725
            onboard_pattern = r'^\d{2}:\d{2}:\d{2}\s+\d+\.\d+V\s+\d{2}:\d{2}\s+[A-Z]+\s+[X\w]\s+[X\w]\s+\d+'
            
            for line in sample_lines:
                if re.match(onboard_pattern, line):
                    return 'onboard_monitor'
            
            # CSV 형식 감지
            if any(',' in line and ('voltage' in line.lower() or 'battery' in line.lower()) for line in sample_lines):
                return 'csv_format'
            
            # JSON 형식 감지
            if any(line.strip().startswith('{') for line in sample_lines):
                return 'json_format'
            
            return 'general_battery'
            
        except Exception as e:
            print(f"형식 감지 오류: {e}")
            return 'general_battery'
    
    def parse_onboard_monitor_log(self, file_path):
        """OnBoard 모니터 로그 파싱"""
        try:
            data = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # OnBoard 로그 패턴 매칭
                    # 13:49:50		25.22V	00:00		STANDBY		X	X	3725
                    pattern = r'^(\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)V\s+(\d{2}:\d{2})\s+([A-Z]+)\s+([X\w])\s+([X\w])\s+(\d+)'
                    match = re.match(pattern, line)
                    
                    if match:
                        time_str, voltage_str, timer_str, status, l1, l2, memo = match.groups()
                        
                        # 타임스탬프 생성 (오늘 날짜 기준)
                        today = datetime.now().date()
                        timestamp = datetime.combine(today, datetime.strptime(time_str, '%H:%M:%S').time())
                        
                        # 전압값 파싱
                        voltage = float(voltage_str)
                        
                        # 메모값 파싱
                        memo_value = int(memo)
                        
                        data.append({
                            'timestamp': timestamp,
                            'battery': voltage,
                            'timer': timer_str,
                            'status': status,
                            'L1': l1,
                            'L2': l2,
                            'memo': memo_value,
                            'source': 'onboard_monitor'
                        })
                    else:
                        print(f"라인 {line_num} 파싱 실패: {line}")
            
            if not data:
                print("OnBoard 로그 데이터를 찾을 수 없습니다.")
                return None
            
            df = pd.DataFrame(data)
            
            # 타임스탬프 정렬
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            print(f"OnBoard 로그 파싱 완료: {len(df)}개 레코드")
            return df
            
        except Exception as e:
            print(f"OnBoard 로그 파싱 오류: {e}")
            return None
    
    def parse_csv_log(self, file_path):
        """CSV 형식 로그 파싱"""
        try:
            # CSV 파일 읽기
            df = pd.read_csv(file_path)
            
            # 컬럼명 정규화
            df.columns = df.columns.str.lower().str.strip()
            
            # 배터리 전압 컬럼 찾기
            voltage_columns = ['battery', 'voltage', 'volt', 'v']
            battery_col = None
            
            for col in voltage_columns:
                if col in df.columns:
                    battery_col = col
                    break
            
            if battery_col is None:
                print("배터리 전압 컬럼을 찾을 수 없습니다.")
                return None
            
            # 타임스탬프 컬럼 찾기
            timestamp_columns = ['timestamp', 'time', 'datetime', 'date']
            timestamp_col = None
            
            for col in timestamp_columns:
                if col in df.columns:
                    timestamp_col = col
                    break
            
            if timestamp_col is None:
                # 타임스탬프가 없으면 인덱스 기반으로 생성
                start_time = datetime.now()
                df['timestamp'] = [start_time + timedelta(seconds=i) for i in range(len(df))]
            else:
                df['timestamp'] = pd.to_datetime(df[timestamp_col])
            
            # 배터리 컬럼명 통일
            if battery_col != 'battery':
                df['battery'] = df[battery_col]
            
            # 필요한 컬럼만 선택
            result_df = df[['timestamp', 'battery']].copy()
            result_df['source'] = 'csv_format'
            
            print(f"CSV 로그 파싱 완료: {len(result_df)}개 레코드")
            return result_df
            
        except Exception as e:
            print(f"CSV 로그 파싱 오류: {e}")
            return None
    
    def parse_json_log(self, file_path):
        """JSON 형식 로그 파싱"""
        try:
            import json
            
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            data.append(record)
                        except json.JSONDecodeError:
                            continue
            
            if not data:
                print("JSON 로그 데이터를 찾을 수 없습니다.")
                return None
            
            df = pd.DataFrame(data)
            
            # 타임스탬프 처리
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'])
            else:
                start_time = datetime.now()
                df['timestamp'] = [start_time + timedelta(seconds=i) for i in range(len(df))]
            
            # 배터리 전압 컬럼 찾기
            if 'battery' not in df.columns:
                if 'voltage' in df.columns:
                    df['battery'] = df['voltage']
                else:
                    print("배터리 전압 데이터를 찾을 수 없습니다.")
                    return None
            
            result_df = df[['timestamp', 'battery']].copy()
            result_df['source'] = 'json_format'
            
            print(f"JSON 로그 파싱 완료: {len(result_df)}개 레코드")
            return result_df
            
        except Exception as e:
            print(f"JSON 로그 파싱 오류: {e}")
            return None
    
    def parse_general_battery_log(self, file_path):
        """일반 배터리 로그 파싱"""
        try:
            data = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 다양한 패턴 시도
                    patterns = [
                        # 타임스탬프와 전압이 함께 있는 경우
                        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)',
                        r'(\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)',
                        # 전압만 있는 경우
                        r'^(\d+\.\d+)$',
                        r'^(\d+\.\d+)V?$'
                    ]
                    
                    parsed = False
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            groups = match.groups()
                            
                            if len(groups) == 2:  # 타임스탬프 + 전압
                                time_str, voltage_str = groups
                                try:
                                    if len(time_str) > 8:  # 날짜 포함
                                        timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                                    else:  # 시간만
                                        today = datetime.now().date()
                                        timestamp = datetime.combine(today, datetime.strptime(time_str, '%H:%M:%S').time())
                                except:
                                    continue
                            else:  # 전압만
                                voltage_str = groups[0]
                                # 라인 번호 기반 타임스탬프 생성
                                base_time = datetime.now()
                                timestamp = base_time + timedelta(seconds=line_num)
                            
                            try:
                                voltage = float(voltage_str)
                                data.append({
                                    'timestamp': timestamp,
                                    'battery': voltage,
                                    'source': 'general_battery'
                                })
                                parsed = True
                                break
                            except:
                                continue
                    
                    if not parsed:
                        print(f"라인 {line_num} 파싱 실패: {line}")
            
            if not data:
                print("배터리 로그 데이터를 찾을 수 없습니다.")
                return None
            
            df = pd.DataFrame(data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            print(f"일반 배터리 로그 파싱 완료: {len(df)}개 레코드")
            return df
            
        except Exception as e:
            print(f"일반 배터리 로그 파싱 오류: {e}")
            return None
    
    def generate_test_data(self, num_points=1000, battery_type=1):
        """테스트 데이터 생성"""
        np.random.seed(42)
        
        # 시작 시간
        start_time = datetime.now() - timedelta(hours=24)
        
        # 시간 배열 생성
        timestamps = [start_time + timedelta(seconds=i*60) for i in range(num_points)]
        
        if battery_type == 6:  # OnBoard 6S 시스템 시뮬레이션
            # 6S 리튬이온 배터리 (20V~25.2V)
            base_voltage = 22.2  # 3.7V × 6
            
            # 방전 곡선 시뮬레이션
            discharge_curve = np.linspace(25.2, 20.5, num_points)
            
            # 노이즈 추가
            noise = np.random.normal(0, 0.05, num_points)
            battery_values = discharge_curve + noise
            
            # OnBoard 로그 형식 데이터 생성
            data = []
            statuses = ['STANDBY', 'ACTIVE', 'CHARGING']
            
            for i, (timestamp, voltage) in enumerate(zip(timestamps, battery_values)):
                # 타이머 값 (대부분 00:00)
                timer = '00:00' if np.random.random() > 0.1 else f'{np.random.randint(0,24):02d}:{np.random.randint(0,60):02d}'
                
                # 상태 (대부분 STANDBY)
                status = 'STANDBY' if np.random.random() > 0.2 else np.random.choice(statuses)
                
                # LED 상태 (대부분 X,X)
                l1 = 'X' if np.random.random() > 0.05 else 'O'
                l2 = 'X' if np.random.random() > 0.05 else 'O'
                
                # 메모 값
                memo = np.random.randint(3700, 3800)
                
                data.append({
                    'timestamp': timestamp,
                    'battery': voltage,
                    'timer': timer,
                    'status': status,
                    'L1': l1,
                    'L2': l2,
                    'memo': memo,
                    'source': 'onboard_monitor'
                })
        
        else:  # 일반 배터리 (3.7V 기준)
            # 리튬이온 배터리 방전 곡선
            discharge_curve = np.linspace(4.2, 3.0, num_points)
            noise = np.random.normal(0, 0.02, num_points)
            battery_values = discharge_curve + noise
            
            data = []
            for timestamp, voltage in zip(timestamps, battery_values):
                data.append({
                    'timestamp': timestamp,
                    'battery': voltage,
                    'source': 'test_data'
                })
        
        df = pd.DataFrame(data)
        print(f"테스트 데이터 생성 완료: {len(df)}개 레코드 (배터리 타입: {'OnBoard 6S' if battery_type == 6 else '일반'})")
        
        return df
    
    def save_test_onboard_log(self, file_path, num_points=100):
        """OnBoard 로그 형식의 테스트 파일 생성"""
        try:
            test_data = self.generate_test_data(num_points, battery_type=6)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for _, row in test_data.iterrows():
                    time_str = row['timestamp'].strftime('%H:%M:%S')
                    voltage_str = f"{row['battery']:.2f}V"
                    
                    line = f"{time_str}\t\t{voltage_str}\t{row['timer']}\t\t{row['status']}\t\t{row['L1']}\t{row['L2']}\t{row['memo']}\n"
                    f.write(line)
            
            print(f"OnBoard 테스트 로그 파일 생성: {file_path}")
            return True
            
        except Exception as e:
            print(f"테스트 파일 생성 오류: {e}")
            return False

    def analyze_battery_performance(self, df, load_watts=None, load_amps=None, 
                                  battery_capacity_ah=None, battery_type='6s'):
        """
        배터리 성능 분석 및 수명 평가 (충전 이벤트 필터링 포함)
        
        Args:
            df: 파싱된 배터리 데이터
            load_watts: 부하 전력 (W)
            load_amps: 부하 전류 (A)
            battery_capacity_ah: 배터리 용량 (Ah)
            battery_type: 배터리 타입 ('6s', '3s', 'single')
            
        Returns:
            dict: 분석 결과
        """
        if df is None or len(df) == 0:
            print("분석할 데이터가 없습니다.")
            return None
        
        try:
            config = self.battery_configs.get(battery_type, self.battery_configs['6s'])
            
            # 1. 충전/부하 종료 이벤트 감지 및 필터링
            filtered_df, charging_events, original_count, filtered_count = self.detect_and_filter_charging_events(df)
            
            # 원본 데이터와 필터링된 데이터 모두 분석
            analysis = {
                'original_data_info': {
                    'total_records': original_count,
                    'charging_events': len(charging_events),
                    'charging_event_details': charging_events
                },
                'filtered_data_info': {
                    'analysis_records': filtered_count,
                    'excluded_records': original_count - filtered_count,
                    'data_quality': 'good' if filtered_count > original_count * 0.7 else 'limited'
                },
                'battery_config': config
            }
            
            # 필터링된 데이터로 분석 수행 (데이터가 충분한 경우)
            if filtered_count > 5:  # 최소 5개 이상의 데이터 포인트 필요
                print(f"필터링된 데이터로 분석 수행: {filtered_count}개 레코드")
                
                # 기본 통계 계산
                analysis['basic_stats'] = self._calculate_basic_stats(filtered_df, config)
                analysis['voltage_analysis'] = self._analyze_voltage_pattern(filtered_df, config)
                analysis['time_analysis'] = self._analyze_time_pattern(filtered_df)
                
                # 부하 정보가 있는 경우 추가 분석
                if load_watts is not None or load_amps is not None:
                    analysis['load_analysis'] = self._analyze_load_performance(
                        filtered_df, load_watts, load_amps, config, battery_capacity_ah)
                    
                    # 내부 저항 분석 추가
                    analysis['resistance_analysis'] = self._analyze_internal_resistance(
                        filtered_df, load_watts, load_amps, config)
                
                # 배터리 수명 평가 (필터링된 데이터 기준)
                analysis['health_assessment'] = self._assess_battery_health(filtered_df, config)
                
                # 성능 예측
                analysis['performance_prediction'] = self._predict_performance(filtered_df, config)
                
            else:
                print(f"필터링 후 데이터 부족 ({filtered_count}개), 원본 데이터로 분석")
                # 데이터가 부족하면 원본 데이터로 분석 (경고 포함)
                analysis['basic_stats'] = self._calculate_basic_stats(df, config)
                analysis['voltage_analysis'] = self._analyze_voltage_pattern(df, config)
                analysis['time_analysis'] = self._analyze_time_pattern(df)
                
                if load_watts is not None or load_amps is not None:
                    analysis['load_analysis'] = self._analyze_load_performance(
                        df, load_watts, load_amps, config, battery_capacity_ah)
                    analysis['resistance_analysis'] = self._analyze_internal_resistance(
                        df, load_watts, load_amps, config)
                
                analysis['health_assessment'] = self._assess_battery_health(df, config)
                analysis['performance_prediction'] = self._predict_performance(df, config)
                
                # 경고 추가
                analysis['data_warning'] = "충전 이벤트 필터링 후 데이터 부족으로 원본 데이터 사용됨"
            
            # 추천 전압 정보 추가
            analysis['voltage_recommendations'] = {
                'recommended_100_percent': config['recommended_100_voltage'],
                'recommended_0_percent': config['recommended_0_voltage'],
                'safe_operating_range': {
                    'max': config['max_voltage'],
                    'min': config['cutoff_voltage']
                },
                'per_cell_recommendations': {
                    'recommended_100_percent_per_cell': config['recommended_100_voltage'] / config['cells'],
                    'recommended_0_percent_per_cell': config['recommended_0_voltage'] / config['cells'],
                    'safe_max_per_cell': config['max_voltage'] / config['cells'],
                    'safe_min_per_cell': config['cutoff_voltage'] / config['cells']
                }
            }
            
            return analysis
            
        except Exception as e:
            print(f"배터리 성능 분석 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_basic_stats(self, df, config):
        """기본 통계 계산"""
        voltage_stats = df['battery'].describe()
        
        # 전압 범위별 시간 계산
        duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600  # 시간
        
        # SOC (State of Charge) 추정
        soc_start = self._voltage_to_soc(df['battery'].iloc[0], config)
        soc_end = self._voltage_to_soc(df['battery'].iloc[-1], config)
        soc_used = soc_start - soc_end
        
        return {
            'voltage_stats': voltage_stats.to_dict(),
            'duration_hours': duration,
            'soc_start_percent': soc_start,
            'soc_end_percent': soc_end,
            'soc_used_percent': soc_used,
            'avg_voltage': df['battery'].mean(),
            'voltage_stability': df['battery'].std(),
            'total_records': len(df)
        }
    
    def _analyze_voltage_pattern(self, df, config):
        """전압 패턴 분석"""
        voltages = df['battery'].values
        
        # 방전 곡선 분석
        discharge_rate = np.diff(voltages)
        avg_discharge_rate = np.mean(discharge_rate[discharge_rate < 0])  # 방전만
        
        # 전압 변동성
        voltage_variation = np.std(voltages)
        
        # 급격한 전압 변화 감지
        sharp_drops = np.sum(discharge_rate < -0.1)  # 0.1V 이상 급락
        
        # 전압 회복 패턴
        recovery_points = np.sum(discharge_rate > 0.05)  # 0.05V 이상 회복
        
        return {
            'avg_discharge_rate_v_per_record': avg_discharge_rate,
            'voltage_variation': voltage_variation,
            'sharp_voltage_drops': sharp_drops,
            'voltage_recovery_events': recovery_points,
            'min_cell_voltage': voltages.min() / config['cells'],
            'max_cell_voltage': voltages.max() / config['cells'],
            'voltage_range': voltages.max() - voltages.min()
        }
    
    def _analyze_time_pattern(self, df):
        """시간 패턴 분석"""
        if len(df) < 2:
            return {}
        
        # 시간 간격 분석
        time_diffs = df['timestamp'].diff().dt.total_seconds().dropna()
        
        return {
            'avg_interval_seconds': time_diffs.mean(),
            'interval_consistency': time_diffs.std(),
            'total_duration_hours': (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600,
            'data_points_per_hour': len(df) / ((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600)
        }
    
    def _analyze_load_performance(self, df, load_watts, load_amps, config, battery_capacity_ah):
        """부하 성능 분석 (전압-전류 관계 개선)"""
        analysis = {}
        
        # 평균 전압
        avg_voltage = df['battery'].mean()
        
        # 부하 타입에 따른 계산
        if load_watts is not None:
            # 와트 입력: 일정 전력 부하 (전압 변화에 따라 전류 변화)
            load_type = 'constant_power'
            set_power = load_watts
            
            # 전압별 전류 계산
            voltages = df['battery'].values
            currents = set_power / voltages  # I = P / V
            avg_current = np.mean(currents)
            max_current = np.max(currents)  # 최저 전압에서 최대 전류
            
            analysis['calculated_load'] = {
                'load_type': load_type,
                'set_power_watts': set_power,
                'avg_current_amps': avg_current,
                'max_current_amps': max_current,
                'min_current_amps': np.min(currents),
                'avg_voltage': avg_voltage,
                'current_variation': np.std(currents)
            }
            
        elif load_amps is not None:
            # 암페어 입력: 일정 전류 부하 (전압 변화와 무관하게 전류 일정)
            load_type = 'constant_current'
            set_current = load_amps
            
            # 전압별 전력 계산
            voltages = df['battery'].values
            powers = set_current * voltages  # P = I × V
            avg_power = np.mean(powers)
            max_power = np.max(powers)  # 최고 전압에서 최대 전력
            
            analysis['calculated_load'] = {
                'load_type': load_type,
                'set_current_amps': set_current,
                'avg_power_watts': avg_power,
                'max_power_watts': max_power,
                'min_power_watts': np.min(powers),
                'avg_voltage': avg_voltage,
                'power_variation': np.std(powers)
            }
            
        else:
            return analysis
        
        # 배터리 용량 추정 (용량이 주어지지 않은 경우)
        if battery_capacity_ah is None:
            if config['cells'] == 6:
                battery_capacity_ah = 2.5
            elif config['cells'] == 3:
                battery_capacity_ah = 5.0
            else:
                battery_capacity_ah = 3.0
        
        analysis['battery_capacity_ah'] = battery_capacity_ah
        
        # 방전 시간 예측 (부하 타입에 따라 다르게 계산)
        if load_watts is not None:
            # 일정 전력 부하: 평균 전류로 계산
            effective_current = avg_current
        else:
            # 일정 전류 부하: 설정 전류 사용
            effective_current = set_current
        
        if effective_current > 0:
            # SOC 변화량 계산
            soc_start = self._voltage_to_soc(df['battery'].iloc[0], config)
            soc_end = self._voltage_to_soc(df['battery'].iloc[-1], config)
            soc_used = soc_start - soc_end
            
            # 실제 테스트 시간
            test_duration_hours = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
            
            if test_duration_hours > 0 and soc_used > 0:
                # 실제 방전율 계산
                actual_discharge_rate = soc_used / test_duration_hours
                
                # 예상 총 방전 시간
                estimated_total_hours = 100 / actual_discharge_rate
                
                # C-rate 계산 (평균 전류 기준)
                c_rate = effective_current / battery_capacity_ah
                
                # 부하 타입별 효율성 평가
                if load_watts is not None:
                    # 일정 전력: 전압 변동에 따른 전류 변화 고려
                    current_stability = 1 / (1 + analysis['calculated_load']['current_variation'])
                    efficiency_factor = current_stability
                else:
                    # 일정 전류: 전력 변동 고려
                    power_efficiency = avg_power / max_power if max_power > 0 else 1.0
                    efficiency_factor = power_efficiency
                
                analysis['discharge_analysis'] = {
                    'load_type': load_type,
                    'effective_current_amps': effective_current,
                    'actual_discharge_rate_percent_per_hour': actual_discharge_rate,
                    'estimated_total_discharge_hours': estimated_total_hours,
                    'c_rate': c_rate,
                    'estimated_remaining_hours': (soc_end / 100) * estimated_total_hours,
                    'efficiency_rating': self._calculate_efficiency_rating(c_rate, actual_discharge_rate),
                    'load_efficiency_factor': efficiency_factor
                }
        
        # 전압 강하 분석 (부하 타입별)
        voltage_drop = df['battery'].iloc[0] - df['battery'].iloc[-1]
        duration_hours = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
        
        if load_watts is not None:
            # 일정 전력: 전압 강하에 따른 전류 증가 분석
            start_current = load_watts / df['battery'].iloc[0]
            end_current = load_watts / df['battery'].iloc[-1]
            current_increase = end_current - start_current
            
            analysis['voltage_drop_analysis'] = {
                'total_voltage_drop': voltage_drop,
                'voltage_drop_per_hour': voltage_drop / duration_hours if duration_hours > 0 else 0,
                'voltage_stability_under_load': df['battery'].std(),
                'current_increase_due_to_voltage_drop': current_increase,
                'current_increase_percent': (current_increase / start_current * 100) if start_current > 0 else 0
            }
        else:
            # 일정 전류: 전압 강하에 따른 전력 감소 분석
            start_power = load_amps * df['battery'].iloc[0]
            end_power = load_amps * df['battery'].iloc[-1]
            power_decrease = start_power - end_power
            
            analysis['voltage_drop_analysis'] = {
                'total_voltage_drop': voltage_drop,
                'voltage_drop_per_hour': voltage_drop / duration_hours if duration_hours > 0 else 0,
                'voltage_stability_under_load': df['battery'].std(),
                'power_decrease_due_to_voltage_drop': power_decrease,
                'power_decrease_percent': (power_decrease / start_power * 100) if start_power > 0 else 0
            }
        
        return analysis
    
    def _assess_battery_health(self, df, config):
        """배터리 건강도 평가 (충전 이벤트 감지 포함)"""
        health_score = 100  # 시작 점수
        issues = []
        
        voltages = df['battery'].values
        
        # 1. 전압 범위 체크
        min_voltage = voltages.min()
        max_voltage = voltages.max()
        
        if min_voltage < config['cutoff_voltage']:
            health_score -= 20
            issues.append(f"위험: 최소 전압이 안전 범위 이하 ({min_voltage:.2f}V < {config['cutoff_voltage']}V)")
        
        if max_voltage > config['max_voltage'] * 1.05:  # 5% 여유
            health_score -= 15
            issues.append(f"주의: 최대 전압이 권장 범위 초과 ({max_voltage:.2f}V > {config['max_voltage']}V)")
        
        # 2. 전압 안정성 체크
        voltage_std = np.std(voltages)
        expected_std = 0.1  # 정상 범위
        
        if voltage_std > expected_std * 2:
            health_score -= 15
            issues.append(f"주의: 전압 변동성이 높음 (표준편차: {voltage_std:.3f}V)")
        
        # 3. 방전 곡선 분석
        if len(voltages) > 10:
            # 급격한 전압 강하 체크
            voltage_diffs = np.diff(voltages)
            sharp_drops = np.sum(voltage_diffs < -0.2)  # 0.2V 이상 급락
            
            if sharp_drops > len(voltages) * 0.05:  # 5% 이상
                health_score -= 10
                issues.append(f"주의: 급격한 전압 강하 감지 ({sharp_drops}회)")
        
        # 4. 용량 평가 (SOC 기준)
        soc_start = self._voltage_to_soc(voltages[0], config)
        soc_end = self._voltage_to_soc(voltages[-1], config)
        
        if soc_start > 90 and soc_end < 20:  # 충분한 방전 테스트
            # 방전 곡선의 선형성 체크
            expected_curve = np.linspace(soc_start, soc_end, len(voltages))
            actual_soc = [self._voltage_to_soc(v, config) for v in voltages]
            curve_deviation = np.std(np.array(actual_soc) - expected_curve)
            
            if curve_deviation > 5:  # 5% 이상 편차
                health_score -= 10
                issues.append(f"주의: 비정상적인 방전 곡선 (편차: {curve_deviation:.1f}%)")
        
        # 5. 온도 추정 (전압 변동 기준)
        temp_stress_indicator = voltage_std * 100  # 간접 지표
        if temp_stress_indicator > 10:
            health_score -= 5
            issues.append("주의: 온도 스트레스 가능성")
        
        # 건강도 등급 산정
        if health_score >= 90:
            health_grade = "우수"
        elif health_score >= 75:
            health_grade = "양호"
        elif health_score >= 60:
            health_grade = "보통"
        elif health_score >= 40:
            health_grade = "주의"
        else:
            health_grade = "교체 필요"
        
        # 추천 전압 정보 추가
        recommendations = self._generate_recommendations(health_score, issues)
        recommendations.extend([
            f"충전 완료 전압: {config['recommended_100_voltage']:.1f}V ({config['recommended_100_voltage']/config['cells']:.2f}V/cell)",
            f"방전 종료 전압: {config['recommended_0_voltage']:.1f}V ({config['recommended_0_voltage']/config['cells']:.2f}V/cell)"
        ])
        
        return {
            'health_score': max(0, health_score),
            'health_grade': health_grade,
            'issues': issues,
            'voltage_range_ok': config['min_voltage'] <= min_voltage <= max_voltage <= config['max_voltage'],
            'stability_good': voltage_std <= expected_std * 1.5,
            'recommendations': recommendations
        }
    
    def _predict_performance(self, df, config):
        """성능 예측"""
        voltages = df['battery'].values
        
        if len(voltages) < 10:
            return {"message": "예측을 위한 데이터가 부족합니다"}
        
        # 방전 추세 분석
        time_points = np.arange(len(voltages))
        slope, intercept = np.polyfit(time_points, voltages, 1)
        
        # 예상 수명 계산
        current_voltage = voltages[-1]
        cutoff_voltage = config['cutoff_voltage']
        
        if slope < 0:  # 방전 중
            remaining_points = (current_voltage - cutoff_voltage) / abs(slope)
            
            # 시간 간격 고려
            if len(df) > 1:
                avg_interval = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / (len(df) - 1)
                remaining_seconds = remaining_points * avg_interval
                remaining_hours = remaining_seconds / 3600
            else:
                remaining_hours = None
        else:
            remaining_hours = float('inf')  # 충전 중이거나 안정
        
        # 성능 추세 예측
        voltage_trend = "하강" if slope < -0.001 else "안정" if abs(slope) <= 0.001 else "상승"
        
        return {
            'voltage_trend': voltage_trend,
            'discharge_rate_v_per_point': slope,
            'estimated_remaining_hours': remaining_hours if remaining_hours != float('inf') else None,
            'projected_cutoff_time': (df['timestamp'].iloc[-1] + timedelta(hours=remaining_hours)).isoformat() if remaining_hours and remaining_hours != float('inf') else None,
            'trend_confidence': self._calculate_trend_confidence(voltages)
        }
    
    def _voltage_to_soc(self, voltage, config):
        """전압을 SOC(충전상태)로 변환"""
        v_min = config['min_voltage']
        v_max = config['max_voltage']
        
        # 리튬이온 배터리의 일반적인 전압-SOC 곡선 (근사)
        if voltage >= v_max:
            return 100
        elif voltage <= v_min:
            return 0
        else:
            # 비선형 곡선 근사 (S자 곡선)
            normalized = (voltage - v_min) / (v_max - v_min)
            # 간단한 다항식 근사
            soc = 100 * (0.1 + 0.9 * normalized**0.7)
            return max(0, min(100, soc))
    
    def _calculate_efficiency_rating(self, c_rate, discharge_rate):
        """효율성 평가"""
        # 이상적인 방전율 vs 실제 방전율 비교
        # C-rate에 따른 예상 방전율 (이론값)
        expected_rate = c_rate * 100  # C-rate * 100%/hour
        
        if expected_rate == 0:
            return "N/A"
        
        efficiency = (expected_rate / discharge_rate) * 100
        
        if efficiency >= 90:
            return "우수"
        elif efficiency >= 75:
            return "양호"
        elif efficiency >= 60:
            return "보통"
        else:
            return "개선 필요"
    
    def _calculate_trend_confidence(self, voltages):
        """추세 신뢰도 계산"""
        if len(voltages) < 3:
            return "낮음"
        
        # R-squared 계산
        time_points = np.arange(len(voltages))
        slope, intercept = np.polyfit(time_points, voltages, 1)
        predicted = slope * time_points + intercept
        
        ss_res = np.sum((voltages - predicted) ** 2)
        ss_tot = np.sum((voltages - np.mean(voltages)) ** 2)
        
        if ss_tot == 0:
            r_squared = 1.0
        else:
            r_squared = 1 - (ss_res / ss_tot)
        
        if r_squared >= 0.9:
            return "높음"
        elif r_squared >= 0.7:
            return "보통"
        else:
            return "낮음"
    
    def _generate_recommendations(self, health_score, issues):
        """권장사항 생성"""
        recommendations = []
        
        if health_score < 60:
            recommendations.append("배터리 교체를 권장합니다")
        elif health_score < 75:
            recommendations.append("배터리 상태 주의 깊게 모니터링 필요")
        
        for issue in issues:
            if "위험" in issue:
                recommendations.append("즉시 사용을 중단하고 전문가 상담")
            elif "급격한 전압" in issue:
                recommendations.append("부하를 줄이고 충전 패턴 점검")
            elif "변동성" in issue:
                recommendations.append("온도 환경 및 충전기 상태 점검")
        
        if not recommendations:
            recommendations.append("현재 배터리 상태 양호")
        
        return recommendations
    
    def generate_performance_report(self, df, load_watts=None, load_amps=None, 
                                  battery_capacity_ah=None, battery_type='6s', 
                                  save_path=None):
        """성능 분석 보고서 생성"""
        analysis = self.analyze_battery_performance(df, load_watts, load_amps, 
                                                   battery_capacity_ah, battery_type)
        
        if analysis is None:
            return None
        
        # 보고서 텍스트 생성
        report = self._format_analysis_report(analysis)
        
        # 파일로 저장
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"성능 분석 보고서 저장: {save_path}")
            except Exception as e:
                print(f"보고서 저장 오류: {e}")
        
        return report
    
    def _format_analysis_report(self, analysis):
        """분석 결과 보고서 포맷팅 (충전 이벤트 정보 포함)"""
        report = []
        report.append("=" * 60)
        report.append("배터리 성능 분석 보고서")
        report.append("=" * 60)
        report.append(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 데이터 품질 정보
        if 'original_data_info' in analysis:
            original_info = analysis['original_data_info']
            filtered_info = analysis['filtered_data_info']
            
            report.append("📊 데이터 품질 분석")
            report.append("-" * 30)
            report.append(f"원본 데이터: {original_info['total_records']}개 레코드")
            report.append(f"분석 데이터: {filtered_info['analysis_records']}개 레코드")
            report.append(f"제외된 데이터: {filtered_info['excluded_records']}개 레코드")
            report.append(f"충전/부하 종료 이벤트: {original_info['charging_events']}개")
            report.append(f"데이터 품질: {filtered_info['data_quality']}")
            
            # 충전 이벤트 상세 정보
            if original_info['charging_events'] > 0:
                report.append("\n⚡ 감지된 충전/부하 종료 이벤트:")
                for i, event in enumerate(original_info['charging_event_details'], 1):
                    report.append(f"  이벤트 {i}: {event['event_type']}")
                    report.append(f"    시간: {event['start_time'].strftime('%H:%M:%S')} ~ {event['end_time'].strftime('%H:%M:%S')}")
                    report.append(f"    전압 변화: {event['start_voltage']:.2f}V → {event['end_voltage']:.2f}V (+{event['voltage_increase']:.2f}V)")
                    report.append(f"    지속시간: {event['duration_records']}개 레코드")
            
            if 'data_warning' in analysis:
                report.append(f"\n⚠️ 경고: {analysis['data_warning']}")
            
            report.append("")
        
        # 기본 정보
        basic = analysis['basic_stats']
        report.append("📊 기본 통계")
        report.append("-" * 30)
        report.append(f"테스트 시간: {basic['duration_hours']:.2f} 시간")
        report.append(f"데이터 포인트: {basic['total_records']}개")
        report.append(f"평균 전압: {basic['avg_voltage']:.3f}V")
        report.append(f"전압 안정성: ±{basic['voltage_stability']:.3f}V")
        report.append(f"SOC 시작: {basic['soc_start_percent']:.1f}%")
        report.append(f"SOC 종료: {basic['soc_end_percent']:.1f}%")
        report.append(f"SOC 소모: {basic['soc_used_percent']:.1f}%")
        report.append("")
        
        # 추천 전압 정보
        if 'voltage_recommendations' in analysis:
            voltage_rec = analysis['voltage_recommendations']
            report.append("🎯 권장 전압 설정")
            report.append("-" * 30)
            report.append(f"충전 완료 전압: {voltage_rec['recommended_100_percent']:.1f}V")
            report.append(f"방전 종료 전압: {voltage_rec['recommended_0_percent']:.1f}V")
            report.append(f"안전 사용 범위: {voltage_rec['safe_operating_range']['min']:.1f}V ~ {voltage_rec['safe_operating_range']['max']:.1f}V")
            
            per_cell = voltage_rec['per_cell_recommendations']
            report.append(f"셀당 충전 완료: {per_cell['recommended_100_percent_per_cell']:.2f}V/cell")
            report.append(f"셀당 방전 종료: {per_cell['recommended_0_percent_per_cell']:.2f}V/cell")
            report.append(f"셀당 안전 범위: {per_cell['safe_min_per_cell']:.2f}V ~ {per_cell['safe_max_per_cell']:.2f}V/cell")
            report.append("")
        
        # 전압 분석
        voltage = analysis['voltage_analysis']
        report.append("⚡ 전압 분석")
        report.append("-" * 30)
        report.append(f"셀당 최소 전압: {voltage['min_cell_voltage']:.3f}V")
        report.append(f"셀당 최대 전압: {voltage['max_cell_voltage']:.3f}V")
        report.append(f"전압 변동 범위: {voltage['voltage_range']:.3f}V")
        report.append(f"급격한 전압 강하: {voltage['sharp_voltage_drops']}회")
        report.append(f"전압 회복 이벤트: {voltage['voltage_recovery_events']}회")
        report.append("")
        
        # 부하 분석 (있는 경우)
        if 'load_analysis' in analysis:
            load = analysis['load_analysis']
            report.append("🔋 부하 성능 분석")
            report.append("-" * 30)
            calc_load = load['calculated_load']
            
            # 부하 타입에 따른 표시
            if calc_load['load_type'] == 'constant_power':
                report.append(f"부하 타입: 일정 전력 (Constant Power)")
                report.append(f"설정 전력: {calc_load['set_power_watts']:.2f}W")
                report.append(f"평균 전류: {calc_load['avg_current_amps']:.2f}A")
                report.append(f"최대 전류: {calc_load['max_current_amps']:.2f}A (최저 전압시)")
                report.append(f"최소 전류: {calc_load['min_current_amps']:.2f}A (최고 전압시)")
                report.append(f"전류 변동: ±{calc_load['current_variation']:.3f}A")
                report.append(f"평균 전압: {calc_load['avg_voltage']:.2f}V")
            elif calc_load['load_type'] == 'constant_current':
                report.append(f"부하 타입: 일정 전류 (Constant Current)")
                report.append(f"설정 전류: {calc_load['set_current_amps']:.2f}A")
                report.append(f"평균 전력: {calc_load['avg_power_watts']:.2f}W")
                report.append(f"최대 전력: {calc_load['max_power_watts']:.2f}W (최고 전압시)")
                report.append(f"최소 전력: {calc_load['min_power_watts']:.2f}W (최저 전압시)")
                report.append(f"전력 변동: ±{calc_load['power_variation']:.3f}W")
                report.append(f"평균 전압: {calc_load['avg_voltage']:.2f}V")
            
            report.append(f"배터리 용량: {load['battery_capacity_ah']:.1f}Ah")
            
            if 'discharge_analysis' in load:
                discharge = load['discharge_analysis']
                report.append(f"유효 전류: {discharge['effective_current_amps']:.2f}A")
                report.append(f"C-rate: {discharge['c_rate']:.2f}C")
                report.append(f"방전율: {discharge['actual_discharge_rate_percent_per_hour']:.2f}%/시간")
                report.append(f"예상 총 방전시간: {discharge['estimated_total_discharge_hours']:.1f}시간")
                report.append(f"예상 잔여시간: {discharge['estimated_remaining_hours']:.1f}시간")
                report.append(f"효율성 등급: {discharge['efficiency_rating']}")
                report.append(f"부하 효율성 계수: {discharge['load_efficiency_factor']:.3f}")
            
            voltage_drop = load['voltage_drop_analysis']
            report.append(f"총 전압 강하: {voltage_drop['total_voltage_drop']:.3f}V")
            report.append(f"시간당 전압 강하: {voltage_drop['voltage_drop_per_hour']:.3f}V/h")
            report.append(f"부하 하 전압 안정성: ±{voltage_drop['voltage_stability_under_load']:.3f}V")
            
            # 부하 타입별 추가 정보
            if 'current_increase_due_to_voltage_drop' in voltage_drop:
                report.append(f"전압 강하로 인한 전류 증가: {voltage_drop['current_increase_due_to_voltage_drop']:.3f}A")
                report.append(f"전류 증가율: {voltage_drop['current_increase_percent']:.1f}%")
            elif 'power_decrease_due_to_voltage_drop' in voltage_drop:
                report.append(f"전압 강하로 인한 전력 감소: {voltage_drop['power_decrease_due_to_voltage_drop']:.3f}W")
                report.append(f"전력 감소율: {voltage_drop['power_decrease_percent']:.1f}%")
            
            report.append("")
        
        # 내부 저항 분석 (있는 경우)
        if 'resistance_analysis' in analysis:
            resistance = analysis['resistance_analysis']
            if 'message' not in resistance:  # 계산이 성공한 경우
                report.append("🔧 내부 저항 분석")
                report.append("-" * 30)
                
                if resistance['load_type'] == 'constant_power':
                    report.append(f"분석 방법: 일정 전력 부하")
                    report.append(f"평균 전류: {resistance['avg_current']:.3f}A")
                    report.append(f"전압 강하: {resistance['voltage_drop']:.3f}V")
                    report.append(f"전류 증가: {resistance['current_increase']:.3f}A")
                    report.append(f"내부 저항 (방법1): {resistance['internal_resistance_method1']:.4f}Ω")
                    
                    if resistance['dynamic_resistance'] is not None:
                        report.append(f"동적 저항: {resistance['dynamic_resistance']:.4f}Ω")
                    
                elif resistance['load_type'] == 'constant_current':
                    report.append(f"분석 방법: 일정 전류 부하")
                    report.append(f"일정 전류: {resistance['constant_current']:.3f}A")
                    report.append(f"전압 강하: {resistance['voltage_drop']:.3f}V")
                    report.append(f"내부 저항: {resistance['internal_resistance']:.4f}Ω")
                    report.append(f"전압 효율성: {resistance['voltage_efficiency']:.3f}")
                
                if 'resistance_rating' in resistance:
                    rating = resistance['resistance_rating']
                    report.append(f"셀당 저항: {rating['resistance_per_cell_mohm']:.1f}mΩ")
                    report.append(f"저항 등급: {rating['grade']}")
                    report.append(f"평가: {rating['description']}")
                
                # 전력 손실 계산
                if 'avg_current' in resistance:
                    current = resistance['avg_current']
                elif 'constant_current' in resistance:
                    current = resistance['constant_current']
                else:
                    current = 0
                
                if current > 0 and 'internal_resistance' in resistance:
                    power_loss = self._calculate_power_loss_due_to_resistance(
                        resistance['internal_resistance'], current)
                    report.append(f"내부 저항으로 인한 전력 손실: {power_loss:.3f}W")
                elif current > 0 and 'internal_resistance_method1' in resistance:
                    power_loss = self._calculate_power_loss_due_to_resistance(
                        resistance['internal_resistance_method1'], current)
                    report.append(f"내부 저항으로 인한 전력 손실: {power_loss:.3f}W")
                
                report.append("")
        
        # 건강도 평가
        health = analysis['health_assessment']
        report.append("💚 배터리 건강도")
        report.append("-" * 30)
        report.append(f"건강도 점수: {health['health_score']:.0f}/100")
        report.append(f"건강도 등급: {health['health_grade']}")
        
        if health['issues']:
            report.append("\n⚠️  발견된 문제점:")
            for issue in health['issues']:
                report.append(f"  • {issue}")
        
        report.append("\n💡 권장사항:")
        for rec in health['recommendations']:
            report.append(f"  • {rec}")
        report.append("")
        
        # 성능 예측
        prediction = analysis['performance_prediction']
        if 'voltage_trend' in prediction:
            report.append("🔮 성능 예측")
            report.append("-" * 30)
            report.append(f"전압 추세: {prediction['voltage_trend']}")
            report.append(f"추세 신뢰도: {prediction['trend_confidence']}")
            
            if prediction['estimated_remaining_hours']:
                report.append(f"예상 잔여시간: {prediction['estimated_remaining_hours']:.1f}시간")
                if prediction['projected_cutoff_time']:
                    cutoff_time = datetime.fromisoformat(prediction['projected_cutoff_time'])
                    report.append(f"예상 방전 완료: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

    def calculate_cycle_life_estimation(self, df, load_watts=None, load_amps=None, 
                                      battery_capacity_ah=None, battery_type='6s'):
        """
        배터리 사이클 수명 추정
        
        Args:
            df: 배터리 데이터
            load_watts: 부하 전력 (W)
            load_amps: 부하 전류 (A)
            battery_capacity_ah: 배터리 용량 (Ah)
            battery_type: 배터리 타입
            
        Returns:
            dict: 사이클 수명 분석 결과
        """
        if df is None or len(df) == 0:
            return None
        
        try:
            config = self.battery_configs.get(battery_type, self.battery_configs['6s'])
            
            # 기본 분석 수행
            analysis = self.analyze_battery_performance(df, load_watts, load_amps, 
                                                      battery_capacity_ah, battery_type)
            if not analysis:
                return None
            
            # DOD (Depth of Discharge) 계산
            soc_start = analysis['basic_stats']['soc_start_percent']
            soc_end = analysis['basic_stats']['soc_end_percent']
            dod = soc_start - soc_end
            
            # 평균 전압과 최저 전압 분석
            avg_voltage = analysis['basic_stats']['avg_voltage']
            min_voltage = df['battery'].min()
            voltage_stress_factor = self._calculate_voltage_stress(min_voltage, config)
            
            # C-rate 스트레스 계산
            c_rate_stress = 1.0
            if 'load_analysis' in analysis and 'discharge_analysis' in analysis['load_analysis']:
                c_rate = analysis['load_analysis']['discharge_analysis']['c_rate']
                c_rate_stress = self._calculate_c_rate_stress(c_rate)
            
            # 온도 스트레스 추정 (전압 변동 기준)
            voltage_std = analysis['basic_stats']['voltage_stability']
            temp_stress = self._estimate_temperature_stress(voltage_std)
            
            # 기본 사이클 수명 (리튬이온 기준: 500~2000 사이클)
            base_cycles = 1000  # 일반적인 리튬이온 배터리
            
            # DOD에 따른 수명 계산 (깊이가 깊을수록 수명 감소)
            dod_factor = self._calculate_dod_factor(dod)
            
            # 총 스트레스 팩터
            total_stress = voltage_stress_factor * c_rate_stress * temp_stress
            
            # 예상 사이클 수명
            estimated_cycles = int(base_cycles * dod_factor / total_stress)
            
            # 용량 유지율 예측 (사이클에 따른)
            capacity_retention_curve = self._predict_capacity_retention(estimated_cycles)
            
            # 실제 사용 패턴 기반 수명 예측
            if dod > 0:
                cycles_per_day = 1.0  # 기본값 (하루 1회 방전)
                estimated_lifespan_days = estimated_cycles / cycles_per_day
                estimated_lifespan_years = estimated_lifespan_days / 365
            else:
                estimated_lifespan_days = None
                estimated_lifespan_years = None
            
            return {
                'cycle_analysis': {
                    'estimated_cycle_life': estimated_cycles,
                    'dod_percent': dod,
                    'dod_factor': dod_factor,
                    'voltage_stress_factor': voltage_stress_factor,
                    'c_rate_stress_factor': c_rate_stress,
                    'temperature_stress_factor': temp_stress,
                    'total_stress_factor': total_stress
                },
                'lifespan_prediction': {
                    'estimated_lifespan_days': estimated_lifespan_days,
                    'estimated_lifespan_years': estimated_lifespan_years,
                    'cycles_per_day': cycles_per_day
                },
                'capacity_retention': capacity_retention_curve,
                'recommendations': self._generate_cycle_life_recommendations(
                    dod, c_rate_stress, voltage_stress_factor, temp_stress)
            }
            
        except Exception as e:
            print(f"사이클 수명 계산 오류: {e}")
            return None
    
    def _calculate_voltage_stress(self, min_voltage, config):
        """전압 스트레스 계산"""
        safe_min = config['cutoff_voltage']
        critical_min = config['min_voltage']
        
        if min_voltage >= safe_min:
            return 1.0  # 스트레스 없음
        elif min_voltage >= critical_min:
            # 선형적으로 스트레스 증가
            stress_range = safe_min - critical_min
            voltage_below_safe = safe_min - min_voltage
            return 1.0 + (voltage_below_safe / stress_range) * 1.5  # 최대 2.5배 스트레스
        else:
            return 3.0  # 위험 영역에서는 3배 스트레스
    
    def _calculate_c_rate_stress(self, c_rate):
        """C-rate 스트레스 계산"""
        if c_rate <= 0.5:
            return 1.0  # 낮은 C-rate는 스트레스 없음
        elif c_rate <= 1.0:
            return 1.0 + (c_rate - 0.5) * 0.5  # 0.5C~1C: 선형 증가
        elif c_rate <= 2.0:
            return 1.25 + (c_rate - 1.0) * 0.75  # 1C~2C: 더 빠른 증가
        else:
            return 2.0 + (c_rate - 2.0) * 1.0  # 2C 이상: 급격한 증가
    
    def _estimate_temperature_stress(self, voltage_std):
        """온도 스트레스 추정 (전압 변동 기준)"""
        # 전압 변동이 클수록 온도 스트레스가 높다고 가정
        if voltage_std <= 0.05:
            return 1.0  # 낮은 변동: 정상 온도
        elif voltage_std <= 0.1:
            return 1.0 + voltage_std * 2  # 중간 변동: 약간의 스트레스
        else:
            return 1.2 + voltage_std * 5  # 높은 변동: 높은 온도 스트레스
    
    def _calculate_dod_factor(self, dod):
        """DOD에 따른 수명 계수 계산"""
        # 일반적인 DOD-사이클 수명 관계 (근사)
        if dod <= 20:
            return 5.0  # 얕은 방전: 수명 크게 증가
        elif dod <= 40:
            return 3.0  # 중간 방전: 수명 증가
        elif dod <= 60:
            return 2.0  # 보통 방전: 약간 증가
        elif dod <= 80:
            return 1.0  # 깊은 방전: 기본 수명
        else:
            return 0.5  # 매우 깊은 방전: 수명 감소
    
    def _predict_capacity_retention(self, estimated_cycles):
        """사이클에 따른 용량 유지율 예측"""
        cycles = np.arange(0, estimated_cycles + 1, estimated_cycles // 10)
        
        # 리튬이온 배터리의 일반적인 용량 감소 곡선 (지수적 감소)
        retention = 100 * np.exp(-cycles / (estimated_cycles * 1.2))
        retention = np.maximum(retention, 60)  # 최소 60% 유지
        
        return {
            'cycles': cycles.tolist(),
            'capacity_percent': retention.tolist(),
            'end_of_life_cycle': int(estimated_cycles * 0.8)  # 80% 용량에서 수명 종료
        }
    
    def _generate_cycle_life_recommendations(self, dod, c_rate_stress, voltage_stress, temp_stress):
        """사이클 수명 기반 권장사항 생성"""
        recommendations = []
        
        if dod > 80:
            recommendations.append("배터리 수명 연장을 위해 방전 깊이를 80% 이하로 제한하세요")
        elif dod > 60:
            recommendations.append("가능하면 방전 깊이를 60% 이하로 유지하세요")
        
        if c_rate_stress > 2.0:
            recommendations.append("높은 C-rate 사용을 피하고 충전/방전 속도를 줄이세요")
        elif c_rate_stress > 1.5:
            recommendations.append("가능하면 더 낮은 전류로 사용하세요")
        
        if voltage_stress > 2.0:
            recommendations.append("위험: 안전 전압 이하로 방전하지 마세요")
        elif voltage_stress > 1.5:
            recommendations.append("방전 하한 전압을 높게 설정하세요")
        
        if temp_stress > 1.5:
            recommendations.append("배터리 온도 관리에 주의하고 과열을 방지하세요")
        
        if not recommendations:
            recommendations.append("현재 사용 패턴이 배터리 수명에 적절합니다")
        
        return recommendations
    
    def generate_comprehensive_report(self, df, load_watts=None, load_amps=None, 
                                    battery_capacity_ah=None, battery_type='6s', 
                                    save_path=None):
        """종합 배터리 분석 보고서 생성"""
        if df is None or len(df) == 0:
            print("분석할 데이터가 없습니다.")
            return None
        
        try:
            # 기본 성능 분석
            performance_analysis = self.analyze_battery_performance(
                df, load_watts, load_amps, battery_capacity_ah, battery_type)
            
            # 사이클 수명 분석
            cycle_analysis = self.calculate_cycle_life_estimation(
                df, load_watts, load_amps, battery_capacity_ah, battery_type)
            
            # 종합 보고서 생성
            report = self._format_comprehensive_report(performance_analysis, cycle_analysis)
            
            # 파일 저장
            if save_path:
                try:
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"종합 분석 보고서 저장: {save_path}")
                except Exception as e:
                    print(f"보고서 저장 오류: {e}")
            
            return {
                'performance_analysis': performance_analysis,
                'cycle_analysis': cycle_analysis,
                'report_text': report
            }
            
        except Exception as e:
            print(f"종합 보고서 생성 오류: {e}")
            return None
    
    def _format_comprehensive_report(self, performance_analysis, cycle_analysis):
        """종합 보고서 포맷팅"""
        report = []
        report.append("=" * 80)
        report.append("종합 배터리 분석 보고서")
        report.append("=" * 80)
        report.append(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 기본 성능 분석 (기존 보고서 내용)
        if performance_analysis:
            performance_report = self._format_analysis_report(performance_analysis)
            report.append(performance_report)
        
        # 사이클 수명 분석
        if cycle_analysis:
            report.append("\n" + "=" * 80)
            report.append("🔄 배터리 사이클 수명 분석")
            report.append("=" * 80)
            
            cycle = cycle_analysis['cycle_analysis']
            lifespan = cycle_analysis['lifespan_prediction']
            
            report.append("📈 사이클 수명 예측")
            report.append("-" * 40)
            report.append(f"예상 사이클 수명: {cycle['estimated_cycle_life']:,}회")
            report.append(f"방전 깊이 (DOD): {cycle['dod_percent']:.1f}%")
            report.append(f"DOD 영향 계수: {cycle['dod_factor']:.2f}x")
            report.append("")
            
            report.append("⚡ 스트레스 분석")
            report.append("-" * 40)
            report.append(f"전압 스트레스: {cycle['voltage_stress_factor']:.2f}x")
            report.append(f"C-rate 스트레스: {cycle['c_rate_stress_factor']:.2f}x")
            report.append(f"온도 스트레스: {cycle['temperature_stress_factor']:.2f}x")
            report.append(f"총 스트레스: {cycle['total_stress_factor']:.2f}x")
            report.append("")
            
            if lifespan['estimated_lifespan_years']:
                report.append("📅 예상 수명")
                report.append("-" * 40)
                report.append(f"예상 수명: {lifespan['estimated_lifespan_years']:.1f}년")
                report.append(f"예상 수명: {lifespan['estimated_lifespan_days']:.0f}일")
                report.append(f"일평균 사이클: {lifespan['cycles_per_day']:.1f}회")
                report.append("")
            
            # 용량 유지율
            retention = cycle_analysis['capacity_retention']
            eol_cycle = retention['end_of_life_cycle']
            report.append("📊 용량 유지율 예측")
            report.append("-" * 40)
            report.append(f"수명 종료 사이클 (80% 용량): {eol_cycle:,}회")
            
            # 주요 마일스톤
            cycles = retention['cycles']
            capacities = retention['capacity_percent']
            for i in range(0, len(cycles), len(cycles)//5):
                if i < len(cycles):
                    report.append(f"{cycles[i]:,}회 후 용량: {capacities[i]:.1f}%")
            report.append("")
            
            # 사이클 수명 권장사항
            report.append("💡 수명 연장 권장사항")
            report.append("-" * 40)
            for rec in cycle_analysis['recommendations']:
                report.append(f"  • {rec}")
            report.append("")
        
        # 종합 평가
        report.append("=" * 80)
        report.append("🏆 종합 평가")
        report.append("=" * 80)
        
        if performance_analysis and cycle_analysis:
            health_score = performance_analysis['health_assessment']['health_score']
            estimated_cycles = cycle_analysis['cycle_analysis']['estimated_cycle_life']
            
            # 종합 등급 계산
            if health_score >= 90 and estimated_cycles >= 1500:
                grade = "A+ (우수)"
            elif health_score >= 80 and estimated_cycles >= 1000:
                grade = "A (양호)"
            elif health_score >= 70 and estimated_cycles >= 800:
                grade = "B (보통)"
            elif health_score >= 60 and estimated_cycles >= 500:
                grade = "C (주의)"
            else:
                grade = "D (교체 필요)"
            
            report.append(f"배터리 종합 등급: {grade}")
            report.append(f"현재 건강도: {health_score}/100")
            report.append(f"예상 사이클 수명: {estimated_cycles:,}회")
            
            # 비용 효율성 분석 (옵션)
            if 'load_analysis' in performance_analysis:
                load_analysis = performance_analysis['load_analysis']
                if 'discharge_analysis' in load_analysis:
                    efficiency = load_analysis['discharge_analysis']['efficiency_rating']
                    report.append(f"에너지 효율성: {efficiency}")
        
        report.append("")
        report.append("=" * 80)
        report.append("보고서 끝")
        report.append("=" * 80)
        
        return "\n".join(report)

    def analyze_with_ui_input(self, df, load_value, load_type='watts', 
                             battery_capacity_ah=None, battery_type='6s'):
        """
        UI에서 입력받은 부하 정보로 배터리 성능 분석
        
        Args:
            df: 배터리 데이터
            load_value: 부하 값 (숫자)
            load_type: 부하 타입 ('watts' 또는 'amps')
            battery_capacity_ah: 배터리 용량 (Ah)
            battery_type: 배터리 타입
            
        Returns:
            dict: 분석 결과
        """
        load_watts = None
        load_amps = None
        
        if load_type.lower() == 'watts':
            load_watts = float(load_value)
        elif load_type.lower() == 'amps':
            load_amps = float(load_value)
        else:
            raise ValueError("load_type은 'watts' 또는 'amps'여야 합니다.")
        
        return self.analyze_battery_performance(
            df=df,
            load_watts=load_watts,
            load_amps=load_amps,
            battery_capacity_ah=battery_capacity_ah,
            battery_type=battery_type
        )
    
    def generate_ui_report(self, df, load_value, load_type='watts', 
                          battery_capacity_ah=None, battery_type='6s', 
                          report_type='comprehensive', save_path=None):
        """
        UI용 보고서 생성
        
        Args:
            df: 배터리 데이터
            load_value: 부하 값
            load_type: 부하 타입 ('watts' 또는 'amps')
            battery_capacity_ah: 배터리 용량
            battery_type: 배터리 타입
            report_type: 보고서 타입 ('basic', 'performance', 'comprehensive')
            save_path: 저장 경로
            
        Returns:
            dict: 분석 결과와 보고서
        """
        try:
            load_watts = None
            load_amps = None
            
            if load_type.lower() == 'watts':
                load_watts = float(load_value)
            elif load_type.lower() == 'amps':
                load_amps = float(load_value)
            
            if report_type == 'comprehensive':
                result = self.generate_comprehensive_report(
                    df=df,
                    load_watts=load_watts,
                    load_amps=load_amps,
                    battery_capacity_ah=battery_capacity_ah,
                    battery_type=battery_type,
                    save_path=save_path
                )
            elif report_type == 'performance':
                report = self.generate_performance_report(
                    df=df,
                    load_watts=load_watts,
                    load_amps=load_amps,
                    battery_capacity_ah=battery_capacity_ah,
                    battery_type=battery_type,
                    save_path=save_path
                )
                result = {
                    'performance_analysis': self.analyze_battery_performance(
                        df, load_watts, load_amps, battery_capacity_ah, battery_type),
                    'report_text': report
                }
            else:  # basic
                result = {
                    'performance_analysis': self.analyze_battery_performance(
                        df, load_watts, load_amps, battery_capacity_ah, battery_type),
                    'report_text': None
                }
            
            return result
            
        except Exception as e:
            print(f"UI 보고서 생성 오류: {e}")
            return None
    
    def get_analysis_summary(self, df, load_value, load_type='watts', 
                           battery_capacity_ah=None, battery_type='6s'):
        """
        UI 표시용 간단한 분석 요약
        
        Returns:
            dict: 주요 지표들
        """
        try:
            analysis = self.analyze_with_ui_input(
                df, load_value, load_type, battery_capacity_ah, battery_type)
            
            if not analysis:
                return None
            
            basic = analysis['basic_stats']
            health = analysis['health_assessment']
            
            summary = {
                'health_score': health['health_score'],
                'health_grade': health['health_grade'],
                'avg_voltage': basic['avg_voltage'],
                'duration_hours': basic['duration_hours'],
                'soc_used': basic['soc_used_percent'],
                'voltage_stability': basic['voltage_stability'],
                'total_records': basic['total_records']
            }
            
            # 부하 분석 정보 추가
            if 'load_analysis' in analysis:
                load = analysis['load_analysis']
                calc_load = load['calculated_load']
                
                if calc_load['load_type'] == 'constant_power':
                    summary['load_type'] = '일정 전력'
                    summary['load_watts'] = calc_load['set_power_watts']
                    summary['avg_amps'] = calc_load['avg_current_amps']
                    summary['max_amps'] = calc_load['max_current_amps']
                    summary['current_variation'] = calc_load['current_variation']
                elif calc_load['load_type'] == 'constant_current':
                    summary['load_type'] = '일정 전류'
                    summary['load_amps'] = calc_load['set_current_amps']
                    summary['avg_watts'] = calc_load['avg_power_watts']
                    summary['max_watts'] = calc_load['max_power_watts']
                    summary['power_variation'] = calc_load['power_variation']
                
                if 'discharge_analysis' in load:
                    discharge = load['discharge_analysis']
                    summary['c_rate'] = discharge['c_rate']
                    summary['estimated_hours'] = discharge['estimated_total_discharge_hours']
                    summary['efficiency'] = discharge['efficiency_rating']
                    summary['load_efficiency'] = discharge['load_efficiency_factor']
            
            # 내부 저항 정보 추가
            if 'resistance_analysis' in analysis:
                resistance = analysis['resistance_analysis']
                if 'message' not in resistance:  # 계산이 성공한 경우
                    if 'internal_resistance' in resistance:
                        summary['internal_resistance'] = resistance['internal_resistance']
                    elif 'internal_resistance_method1' in resistance:
                        summary['internal_resistance'] = resistance['internal_resistance_method1']
                    
                    if 'resistance_rating' in resistance:
                        rating = resistance['resistance_rating']
                        summary['resistance_grade'] = rating['grade']
                        summary['resistance_per_cell'] = rating['resistance_per_cell_mohm']
            
            # 사이클 수명 정보 추가
            cycle_analysis = self.calculate_cycle_life_estimation(
                df, load_value if load_type == 'watts' else None,
                load_value if load_type == 'amps' else None,
                battery_capacity_ah, battery_type
            )
            
            if cycle_analysis:
                cycle = cycle_analysis['cycle_analysis']
                summary['estimated_cycles'] = cycle['estimated_cycle_life']
                summary['dod_percent'] = cycle['dod_percent']
                
                lifespan = cycle_analysis['lifespan_prediction']
                if lifespan['estimated_lifespan_years']:
                    summary['estimated_years'] = lifespan['estimated_lifespan_years']
            
            return summary
            
        except Exception as e:
            print(f"분석 요약 생성 오류: {e}")
            return None

    def _analyze_internal_resistance(self, df, load_watts, load_amps, config):
        """
        배터리 내부 저항 분석
        
        방법:
        1. 전압 변화율과 전류 변화율을 분석
        2. 옴의 법칙 (R = ΔV / ΔI) 적용
        3. 무부하 전압과 부하 전압 차이 분석
        """
        resistance_analysis = {}
        
        voltages = df['battery'].values
        
        if len(voltages) < 2:
            return {'message': '내부 저항 계산을 위한 데이터가 부족합니다'}
        
        # 전압 변화량 계산
        voltage_change = voltages[0] - voltages[-1]  # 초기 - 최종 전압
        
        if load_watts is not None:
            # 일정 전력 부하의 경우
            initial_current = load_watts / voltages[0]
            final_current = load_watts / voltages[-1]
            current_change = final_current - initial_current
            
            # 평균 전류로 내부 저항 추정
            avg_current = np.mean(load_watts / voltages)
            
            # 방법 1: 전압 강하 / 평균 전류
            if avg_current > 0:
                resistance_method1 = voltage_change / avg_current
            else:
                resistance_method1 = 0
            
            # 방법 2: 전압 변화 / 전류 변화 (동적 저항)
            if abs(current_change) > 0.001:  # 전류 변화가 충분히 큰 경우
                dynamic_resistance = -voltage_change / current_change  # 음수 부호: 전류 증가 시 전압 감소
            else:
                dynamic_resistance = None
            
            resistance_analysis = {
                'load_type': 'constant_power',
                'avg_current': avg_current,
                'voltage_drop': voltage_change,
                'current_increase': current_change,
                'internal_resistance_method1': resistance_method1,
                'dynamic_resistance': dynamic_resistance,
                'resistance_unit': 'ohms'
            }
            
        elif load_amps is not None:
            # 일정 전류 부하의 경우
            constant_current = load_amps
            
            # 옴의 법칙: R = ΔV / I
            if constant_current > 0:
                internal_resistance = voltage_change / constant_current
            else:
                internal_resistance = 0
            
            # 전압 효율성 계산
            voltage_efficiency = voltages[-1] / voltages[0] if voltages[0] > 0 else 1.0
            
            resistance_analysis = {
                'load_type': 'constant_current',
                'constant_current': constant_current,
                'voltage_drop': voltage_change,
                'internal_resistance': internal_resistance,
                'voltage_efficiency': voltage_efficiency,
                'resistance_unit': 'ohms'
            }
        
        # 내부 저항 등급 평가
        if 'internal_resistance' in resistance_analysis:
            resistance_value = resistance_analysis['internal_resistance']
        elif 'internal_resistance_method1' in resistance_analysis:
            resistance_value = resistance_analysis['internal_resistance_method1']
        else:
            resistance_value = None
        
        if resistance_value is not None:
            resistance_analysis['resistance_rating'] = self._evaluate_resistance_rating(
                resistance_value, config['cells'])
            resistance_analysis['resistance_per_cell'] = resistance_value / config['cells']
        
        return resistance_analysis
    
    def _evaluate_resistance_rating(self, total_resistance, cell_count):
        """
        내부 저항 등급 평가
        
        일반적인 리튬이온 배터리 내부 저항 기준:
        - 신품: 20-50mΩ/cell
        - 양호: 50-100mΩ/cell  
        - 보통: 100-200mΩ/cell
        - 주의: 200-500mΩ/cell
        - 교체필요: 500mΩ/cell 이상
        """
        resistance_per_cell = (total_resistance * 1000) / cell_count  # mΩ 단위로 변환
        
        if resistance_per_cell <= 50:
            return {
                'grade': '우수',
                'description': '신품 수준의 낮은 내부 저항',
                'resistance_per_cell_mohm': resistance_per_cell
            }
        elif resistance_per_cell <= 100:
            return {
                'grade': '양호', 
                'description': '정상적인 내부 저항 범위',
                'resistance_per_cell_mohm': resistance_per_cell
            }
        elif resistance_per_cell <= 200:
            return {
                'grade': '보통',
                'description': '약간 높은 내부 저항, 모니터링 필요',
                'resistance_per_cell_mohm': resistance_per_cell
            }
        elif resistance_per_cell <= 500:
            return {
                'grade': '주의',
                'description': '높은 내부 저항, 성능 저하',
                'resistance_per_cell_mohm': resistance_per_cell
            }
        else:
            return {
                'grade': '교체 필요',
                'description': '매우 높은 내부 저항, 즉시 교체 권장',
                'resistance_per_cell_mohm': resistance_per_cell
            }
    
    def _calculate_power_loss_due_to_resistance(self, resistance, current):
        """내부 저항으로 인한 전력 손실 계산"""
        if resistance <= 0 or current <= 0:
            return 0
        
        # P_loss = I²R
        power_loss = (current ** 2) * resistance
        return power_loss

    def detect_and_filter_charging_events(self, df, voltage_threshold=0.2, duration_threshold=5):
        """
        전압 급격한 상승(충전/부하 종료) 감지 및 필터링
        
        Args:
            df: 배터리 데이터
            voltage_threshold: 급격한 상승 감지 기준 (V/record)
            duration_threshold: 지속시간 기준 (연속 레코드 수)
            
        Returns:
            tuple: (filtered_df, charging_events, original_count, filtered_count)
        """
        if df is None or len(df) < 2:
            return df, [], len(df) if df is not None else 0, len(df) if df is not None else 0
        
        original_count = len(df)
        charging_events = []
        
        # 전압 변화율 계산
        df_copy = df.copy()
        df_copy['voltage_diff'] = df_copy['battery'].diff()
        
        # 급격한 상승 구간 감지
        sharp_rise_mask = df_copy['voltage_diff'] > voltage_threshold
        
        # 연속된 급격한 상승 구간 그룹화
        rise_groups = []
        current_group = []
        
        for i, is_rise in enumerate(sharp_rise_mask):
            if is_rise:
                current_group.append(i)
            else:
                if len(current_group) >= duration_threshold:
                    rise_groups.append(current_group)
                current_group = []
        
        # 마지막 그룹 처리
        if len(current_group) >= duration_threshold:
            rise_groups.append(current_group)
        
        # 충전 이벤트 정보 수집 및 제외할 인덱스 결정
        exclude_indices = set()
        
        for group in rise_groups:
            start_idx = group[0]
            end_idx = group[-1]
            
            # 이벤트 정보
            start_voltage = df_copy.iloc[start_idx-1]['battery'] if start_idx > 0 else df_copy.iloc[start_idx]['battery']
            end_voltage = df_copy.iloc[end_idx]['battery']
            voltage_increase = end_voltage - start_voltage
            duration = len(group)
            
            # 시간 정보
            start_time = df_copy.iloc[start_idx]['timestamp']
            end_time = df_copy.iloc[end_idx]['timestamp']
            
            charging_event = {
                'start_index': start_idx,
                'end_index': end_idx,
                'start_time': start_time,
                'end_time': end_time,
                'start_voltage': start_voltage,
                'end_voltage': end_voltage,
                'voltage_increase': voltage_increase,
                'duration_records': duration,
                'event_type': 'charging' if voltage_increase > 1.0 else 'load_removal'
            }
            
            charging_events.append(charging_event)
            
            # 충전/부하 종료 구간과 그 이후 안정화 구간까지 제외
            stabilization_period = min(10, len(df_copy) - end_idx - 1)  # 최대 10 레코드 또는 데이터 끝까지
            exclude_end = min(end_idx + stabilization_period, len(df_copy) - 1)
            
            for idx in range(start_idx, exclude_end + 1):
                exclude_indices.add(idx)
        
        # 필터링된 데이터프레임 생성
        if exclude_indices:
            filtered_df = df_copy.drop(index=exclude_indices).reset_index(drop=True)
        else:
            filtered_df = df_copy.drop(columns=['voltage_diff'])
        
        filtered_count = len(filtered_df)
        
        print(f"충전/부하 종료 이벤트 감지: {len(charging_events)}개")
        print(f"데이터 필터링: {original_count}개 → {filtered_count}개 (제외: {original_count - filtered_count}개)")
        
        return filtered_df, charging_events, original_count, filtered_count

# 사용 예시
if __name__ == '__main__':
    parser = BatteryLogParser()
    
    # 테스트 OnBoard 로그 파일 생성
    test_file = 'test_onboard_log.txt'
    parser.save_test_onboard_log(test_file, 50)
    
    # 파싱 테스트
    data = parser.parse_log_file(test_file)
    if data is not None:
        print("\n=== 기본 파싱 결과 ===")
        print(data.head())
        print(f"\n컬럼: {list(data.columns)}")
        print(f"데이터 타입: {data.dtypes}")
        
        # 배터리 성능 분석 테스트
        print("\n=== 배터리 성능 분석 ===")
        
        # 부하 정보 설정 (예시)
        load_watts = 50  # 50W 부하
        battery_capacity = 2.5  # 2.5Ah 배터리
        battery_type = '6s'  # 6S 배터리
        
        # 성능 분석 실행
        analysis = parser.analyze_battery_performance(
            df=data,
            load_watts=load_watts,
            battery_capacity_ah=battery_capacity,
            battery_type=battery_type
        )
        
        if analysis:
            # 분석 결과 요약 출력
            basic = analysis['basic_stats']
            health = analysis['health_assessment']
            
            print(f"📊 테스트 기간: {basic['duration_hours']:.2f}시간")
            print(f"📊 평균 전압: {basic['avg_voltage']:.3f}V")
            print(f"📊 SOC 변화: {basic['soc_start_percent']:.1f}% → {basic['soc_end_percent']:.1f}%")
            print(f"💚 배터리 건강도: {health['health_score']}/100 ({health['health_grade']})")
            
            if 'load_analysis' in analysis:
                load = analysis['load_analysis']
                print(f"🔋 설정 부하: {load['calculated_load']['load_watts']:.1f}W")
                print(f"🔋 부하 전류: {load['calculated_load']['load_amps']:.2f}A")
                
                if 'discharge_analysis' in load:
                    discharge = load['discharge_analysis']
                    print(f"🔋 C-rate: {discharge['c_rate']:.2f}C")
                    print(f"🔋 예상 총 방전시간: {discharge['estimated_total_discharge_hours']:.1f}시간")
                    print(f"🔋 효율성: {discharge['efficiency_rating']}")
            
            if health['issues']:
                print("\n⚠️ 발견된 문제점:")
                for issue in health['issues']:
                    print(f"  • {issue}")
            
            print("\n💡 권장사항:")
            for rec in health['recommendations']:
                print(f"  • {rec}")
            
            # 상세 보고서 생성 및 저장
            report_file = 'battery_performance_report.txt'
            report = parser.generate_performance_report(
                df=data,
                load_watts=load_watts,
                battery_capacity_ah=battery_capacity,
                battery_type=battery_type,
                save_path=report_file
            )
            
            print(f"\n📄 상세 보고서가 '{report_file}'에 저장되었습니다.")
        
        # 시각화 예시 (matplotlib 사용)
        try:
            plt.style.use('default')
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle('배터리 성능 분석 결과', fontsize=16, fontweight='bold')
            
            # 전압 변화 그래프
            axes[0, 0].plot(data.index, data['battery'], 'b-', linewidth=2)
            axes[0, 0].set_title('전압 변화')
            axes[0, 0].set_xlabel('시간 (레코드)')
            axes[0, 0].set_ylabel('전압 (V)')
            axes[0, 0].grid(True, alpha=0.3)
            
            # SOC 변화 (추정)
            if analysis:
                config = analysis['battery_config']
                soc_values = [parser._voltage_to_soc(v, config) for v in data['battery']]
                axes[0, 1].plot(data.index, soc_values, 'g-', linewidth=2)
                axes[0, 1].set_title('SOC 변화 (추정)')
                axes[0, 1].set_xlabel('시간 (레코드)')
                axes[0, 1].set_ylabel('SOC (%)')
                axes[0, 1].grid(True, alpha=0.3)
            
            # 전압 분포 히스토그램
            axes[1, 0].hist(data['battery'], bins=20, alpha=0.7, color='orange', edgecolor='black')
            axes[1, 0].set_title('전압 분포')
            axes[1, 0].set_xlabel('전압 (V)')
            axes[1, 0].set_ylabel('빈도')
            axes[1, 0].grid(True, alpha=0.3)
            
            # 건강도 점수 (바 차트)
            if analysis:
                health_score = analysis['health_assessment']['health_score']
                health_grade = analysis['health_assessment']['health_grade']
                
                colors = ['red' if health_score < 60 else 'orange' if health_score < 75 else 'green']
                bars = axes[1, 1].bar(['건강도'], [health_score], color=colors, alpha=0.7)
                axes[1, 1].set_title(f'배터리 건강도: {health_grade}')
                axes[1, 1].set_ylabel('점수')
                axes[1, 1].set_ylim(0, 100)
                axes[1, 1].grid(True, alpha=0.3)
                
                # 점수 표시
                for bar in bars:
                    height = bar.get_height()
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + 1,
                                   f'{height:.0f}/100', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            
            # 그래프 저장
            plt.savefig('battery_analysis_graph.png', dpi=300, bbox_inches='tight')
            print("📊 분석 그래프가 'battery_analysis_graph.png'에 저장되었습니다.")
            
            # 그래프 표시 (주석 처리 - 자동 실행 시 창이 뜨는 것 방지)
            # plt.show()
            
        except Exception as e:
            print(f"시각화 오류: {e}")
            print("matplotlib 설치 필요: pip install matplotlib")
        
        # 사이클 수명 분석 테스트
        print("\n=== 배터리 사이클 수명 분석 ===")
        cycle_analysis = parser.calculate_cycle_life_estimation(
            df=data,
            load_watts=load_watts,
            battery_capacity_ah=battery_capacity,
            battery_type=battery_type
        )
        
        if cycle_analysis:
            cycle = cycle_analysis['cycle_analysis']
            lifespan = cycle_analysis['lifespan_prediction']
            
            print(f"🔄 예상 사이클 수명: {cycle['estimated_cycle_life']:,}회")
            print(f"🔄 방전 깊이: {cycle['dod_percent']:.1f}%")
            print(f"🔄 총 스트레스 계수: {cycle['total_stress_factor']:.2f}x")
            
            if lifespan['estimated_lifespan_years']:
                print(f"📅 예상 수명: {lifespan['estimated_lifespan_years']:.1f}년")
            
            print("\n💡 수명 연장 권장사항:")
            for rec in cycle_analysis['recommendations']:
                print(f"  • {rec}")
        
        # 종합 보고서 생성
        print("\n=== 종합 분석 보고서 생성 ===")
        comprehensive_file = 'comprehensive_battery_report.txt'
        comprehensive_result = parser.generate_comprehensive_report(
            df=data,
            load_watts=load_watts,
            battery_capacity_ah=battery_capacity,
            battery_type=battery_type,
            save_path=comprehensive_file
        )
        
        if comprehensive_result:
            print(f"📄 종합 분석 보고서가 '{comprehensive_file}'에 저장되었습니다.")
            
            # 종합 등급 표시
            if comprehensive_result['performance_analysis'] and comprehensive_result['cycle_analysis']:
                health_score = comprehensive_result['performance_analysis']['health_assessment']['health_score']
                estimated_cycles = comprehensive_result['cycle_analysis']['cycle_analysis']['estimated_cycle_life']
                
                # 종합 등급 계산
                if health_score >= 90 and estimated_cycles >= 1500:
                    grade = "A+ (우수)"
                elif health_score >= 80 and estimated_cycles >= 1000:
                    grade = "A (양호)"
                elif health_score >= 70 and estimated_cycles >= 800:
                    grade = "B (보통)"
                elif health_score >= 60 and estimated_cycles >= 500:
                    grade = "C (주의)"
                else:
                    grade = "D (교체 필요)"
                
                print(f"🏆 배터리 종합 등급: {grade}")

    # 실제 사용법 예시 출력
    print("\n" + "="*60)
    print("🔧 실제 사용법 예시")
    print("="*60)
    print("""
# 1. 기본 로그 파싱
parser = BatteryLogParser()
data = parser.parse_log_file('your_battery_log.txt')

# 2. 부하 정보와 함께 성능 분석
analysis = parser.analyze_battery_performance(
    df=data,
    load_watts=30,           # 30W 부하 또는
    load_amps=1.5,          # 1.5A 부하
    battery_capacity_ah=3.0, # 3.0Ah 배터리 용량
    battery_type='6s'        # 배터리 타입: '6s', '3s', 'single'
)

# 3. 사이클 수명 분석
cycle_analysis = parser.calculate_cycle_life_estimation(
    df=data,
    load_watts=30,
    battery_capacity_ah=3.0,
    battery_type='6s'
)

# 4. 종합 보고서 생성 (성능 + 수명 분석)
comprehensive = parser.generate_comprehensive_report(
    df=data,
    load_watts=30,
    battery_capacity_ah=3.0,
    battery_type='6s',
    save_path='full_battery_report.txt'
)

# 5. 주요 결과 확인
if analysis and cycle_analysis:
    health = analysis['health_assessment']
    cycle = cycle_analysis['cycle_analysis']
    
    print(f"건강도: {health['health_score']}/100 ({health['health_grade']})")
    print(f"예상 사이클 수명: {cycle['estimated_cycle_life']:,}회")
    print(f"방전 깊이: {cycle['dod_percent']:.1f}%")
    
    if 'load_analysis' in analysis:
        load = analysis['load_analysis']['discharge_analysis']
        print(f"예상 방전시간: {load['estimated_total_discharge_hours']:.1f}시간")
        print(f"C-rate: {load['c_rate']:.2f}C")
        print(f"효율성: {load['efficiency_rating']}")
""")
    
    print("\n📋 분석 가능한 항목:")
    print("  • 배터리 전압 패턴 분석")
    print("  • SOC (충전 상태) 추정")
    print("  • 부하 성능 및 효율성 평가")
    print("  • C-rate 및 방전율 계산")
    print("  • 배터리 건강도 점수")
    print("  • 사이클 수명 예측")
    print("  • 용량 유지율 곡선")
    print("  • 스트레스 요인 분석 (전압, C-rate, 온도)")
    print("  • 수명 연장 권장사항")
    
    print("\n지원하는 배터리 타입:")
    for battery_type, config in parser.battery_configs.items():
        print(f"  • {battery_type}: {config['nominal_voltage']}V ({config['cells']}셀)")
    
    print(f"\n임시 파일 정리 중...")
    # 생성된 테스트 파일 삭제
    try:
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"✓ {test_file} 삭제됨")
    except Exception as e:
        print(f"파일 정리 오류: {e}") 