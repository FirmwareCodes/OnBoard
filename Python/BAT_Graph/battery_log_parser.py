import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
import json
import struct
from typing import Dict, List, Optional, Union

class BatteryLogParser:
    """배터리 로그 파일 파싱 클래스"""
    
    def __init__(self):
        
        # 로그 패턴 정의
        self.patterns = {
            'timestamp': [
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',  # YYYY-MM-DD HH:MM:SS
                r'(\d{2}:\d{2}:\d{2})',  # HH:MM:SS
                r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',  # MM/DD/YYYY HH:MM:SS
                r'(\d{10})',  # Unix timestamp
            ],
            'battery': [
                r'BAT[:\s]*([0-9]+\.?[0-9]*)[V\s]',  # BAT: 3.7V
                r'BATTERY[:\s]*([0-9]+\.?[0-9]*)[V\s]',  # BATTERY: 3.7V
                r'전압[:\s]*([0-9]+\.?[0-9]*)[V\s]',  # 전압: 3.7V
                r'VOLTAGE[:\s]*([0-9]+\.?[0-9]*)[V\s]',  # VOLTAGE: 3.7V
                r'V[:\s]*([0-9]+\.?[0-9]*)',  # V: 3.7
            ],
            'status': [
                r'STATUS[:\s]*(.+)',  # STATUS: ...
                r'상태[:\s]*(.+)',  # 상태: ...
            ],
            # OnBoard OLED Monitor 로그 전용 패턴
            'onboard_log': [
                r'(\d{2}:\d{2}:\d{2})\s+([0-9]+\.?[0-9]*)V\s+(\d{2}:\d{2})\s+(\w+)\s+([XO])\s+([XO])\s+(\d+)',
            ]
        }
        
    def parse_log_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        로그 파일 파싱
        
        Args:
            file_path: 로그 파일 경로
            
        Returns:
            pd.DataFrame: 파싱된 데이터 또는 None
        """
        try:
            # 파일 인코딩 자동 감지
            encoding = self.detect_encoding(file_path)
            
            # 파일 읽기
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            # OnBoard OLED Monitor 로그인지 먼저 확인
            if self.is_onboard_log(content):
                return self.parse_onboard_log(content, file_path)
            
            # 파일 형식에 따른 파싱
            if file_path.endswith('.csv'):
                return self.parse_csv_file(file_path, encoding)
            elif file_path.endswith('.json'):
                return self.parse_json_file(file_path, encoding)
            else:
                return self.parse_text_log(content)
                
        except Exception as e:
            print(f"파일 파싱 오류: {e}")
            return None
    
    def is_onboard_log(self, content: str) -> bool:
        """OnBoard OLED Monitor 로그인지 확인"""
        indicators = [
            'OnBoard OLED Monitor 상태 로그',
            '시간\t\t\t배터리\t타이머\t\t상태\t\tL1\tL2\t비고',
            'STANDBY'
        ]
        return any(indicator in content for indicator in indicators)
    
    def parse_onboard_log(self, content: str, file_path: str) -> Optional[pd.DataFrame]:
        """OnBoard OLED Monitor 로그 파싱"""
        lines = content.split('\n')
        result_data = []
        
        # 파일명에서 날짜 추출 (status_log_YYYYMMDDHHMMSS.txt)
        base_date = self.extract_date_from_filename(file_path)
        
        # 헤더 찾기
        data_start_line = 0
        for i, line in enumerate(lines):
            if '--------------------------------------------------------------------------------' in line:
                data_start_line = i + 1
                break
        
        # 데이터 라인 파싱
        for line_num, line in enumerate(lines[data_start_line:], start=data_start_line+1):
            line = line.strip()
            if not line or '=' in line:
                continue
            
            # OnBoard 로그 패턴으로 파싱 시도
            parsed_data = self.parse_onboard_line(line, base_date)
            if parsed_data:
                parsed_data['line_number'] = line_num
                result_data.append(parsed_data)
            else:
                # 일반 텍스트 로그 파싱도 시도
                general_parsed = self.parse_text_line(line)
                if general_parsed:
                    if base_date:
                        # 시간만 있는 경우 날짜 보완
                        time_only = general_parsed['timestamp'].time()
                        general_parsed['timestamp'] = datetime.combine(base_date.date(), time_only)
                    general_parsed['line_number'] = line_num
                    result_data.append(general_parsed)
        
        if result_data:
            df = pd.DataFrame(result_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            return self.validate_data(df)
        
        return None
    
    def extract_date_from_filename(self, file_path: str) -> Optional[datetime]:
        """파일명에서 날짜 추출"""
        try:
            import os
            filename = os.path.basename(file_path)
            
            # status_log_YYYYMMDDHHMMSS.txt 패턴
            match = re.search(r'status_log_(\d{8})(\d{6})?\.txt', filename)
            if match:
                date_str = match.group(1)  # YYYYMMDD
                time_str = match.group(2) if match.group(2) else '000000'  # HHMMSS
                
                return datetime.strptime(date_str + time_str, '%Y%m%d%H%M%S')
            
            # 다른 날짜 패턴 시도
            date_patterns = [
                r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
                r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
                r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, filename)
                if match:
                    if len(match.group(1)) == 4:  # 년도가 4자리인 경우
                        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    else:  # 년도가 2자리인 경우
                        return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        
        except Exception as e:
            print(f"파일명에서 날짜 추출 오류: {e}")
        
        return datetime.now()  # 기본값으로 현재 날짜 반환
    
    def parse_onboard_line(self, line: str, base_date: datetime) -> Optional[Dict]:
        """OnBoard OLED Monitor 로그 라인 파싱"""
        try:
            # 탭으로 분할된 데이터 파싱
            parts = re.split(r'\t+', line)
            
            if len(parts) >= 7:
                time_str = parts[0].strip()
                battery_str = parts[1].strip()
                timer_str = parts[2].strip()
                status_str = parts[3].strip()
                l1_str = parts[4].strip()
                l2_str = parts[5].strip()
                memo_str = parts[6].strip()
                
                # 시간 파싱
                timestamp = self.parse_onboard_time(time_str, base_date)
                if not timestamp:
                    return None
                
                # 배터리 전압 파싱
                battery_match = re.match(r'([0-9]+\.?[0-9]*)V?', battery_str)
                if not battery_match:
                    return None
                
                battery = float(battery_match.group(1))
                
                return {
                    'timestamp': timestamp,
                    'battery': battery,
                    'timer': timer_str,
                    'status': status_str,
                    'L1': l1_str,
                    'L2': l2_str,
                    'memo': memo_str,
                    'source': 'onboard_monitor'
                }
            
            # 정규식 패턴으로도 시도
            for pattern in self.patterns['onboard_log']:
                match = re.match(pattern, line)
                if match:
                    time_str = match.group(1)
                    battery_val = float(match.group(2))
                    timer_str = match.group(3)
                    status_str = match.group(4)
                    l1_str = match.group(5)
                    l2_str = match.group(6)
                    memo_str = match.group(7)
                    
                    timestamp = self.parse_onboard_time(time_str, base_date)
                    if timestamp:
                        return {
                            'timestamp': timestamp,
                            'battery': battery_val,
                            'timer': timer_str,
                            'status': status_str,
                            'L1': l1_str,
                            'L2': l2_str,
                            'memo': memo_str,
                            'source': 'onboard_monitor'
                        }
        
        except Exception as e:
            print(f"OnBoard 라인 파싱 오류: {e}, 라인: {line}")
        
        return None
    
    def parse_onboard_time(self, time_str: str, base_date: datetime) -> Optional[datetime]:
        """OnBoard 로그의 시간 파싱"""
        try:
            # HH:MM:SS 형식
            time_match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})', time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                second = int(time_match.group(3))
                
                # base_date의 날짜에 시간 결합
                return datetime.combine(
                    base_date.date(),
                    datetime.min.time().replace(hour=hour, minute=minute, second=second)
                )
        
        except Exception as e:
            print(f"시간 파싱 오류: {e}, 시간: {time_str}")
        
        return None

    def detect_encoding(self, file_path: str) -> str:
        """파일 인코딩 감지"""
        encodings = ['utf-8', 'cp949', 'euc-kr', 'ascii', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # 샘플 읽기
                return encoding
            except UnicodeDecodeError:
                continue
        
        return 'utf-8'  # 기본값
    
    def parse_csv_file(self, file_path: str, encoding: str) -> Optional[pd.DataFrame]:
        """CSV 파일 파싱"""
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            
            # 컬럼명 정규화
            df.columns = [col.lower().strip() for col in df.columns]
            
            # 시간 컬럼 찾기
            time_cols = ['time', 'timestamp', 'datetime', '시간', '날짜']
            time_col = None
            for col in time_cols:
                if col in df.columns:
                    time_col = col
                    break
            
            if time_col is None:
                # 첫 번째 컬럼을 시간으로 간주
                time_col = df.columns[0]
            
            # 배터리 컬럼 찾기
            battery_cols = ['battery', 'bat', 'voltage', 'v', '배터리', '전압']
            battery_col = None
            for col in battery_cols:
                if col in df.columns:
                    battery_col = col
                    break
            
            if battery_col is None:
                # 두 번째 컬럼을 배터리로 간주
                if len(df.columns) > 1:
                    battery_col = df.columns[1]
                else:
                    return None
            
            # 데이터 정리
            result_df = pd.DataFrame()
            result_df['timestamp'] = pd.to_datetime(df[time_col], errors='coerce')
            result_df['battery'] = pd.to_numeric(df[battery_col], errors='coerce')
            
            # 유효하지 않은 데이터 제거
            result_df = result_df.dropna()
            
            return result_df
            
        except Exception as e:
            print(f"CSV 파싱 오류: {e}")
            return None
    
    def parse_json_file(self, file_path: str, encoding: str) -> Optional[pd.DataFrame]:
        """JSON 파일 파싱"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                data = json.load(f)
            
            # JSON 구조에 따른 파싱
            if isinstance(data, list):
                return self.parse_json_array(data)
            elif isinstance(data, dict):
                return self.parse_json_object(data)
            
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
            return None
    
    def parse_json_array(self, data: List) -> Optional[pd.DataFrame]:
        """JSON 배열 파싱"""
        result_data = []
        
        for item in data:
            if isinstance(item, dict):
                parsed_item = self.extract_battery_data_from_dict(item)
                if parsed_item:
                    result_data.append(parsed_item)
        
        if result_data:
            return pd.DataFrame(result_data)
        return None
    
    def parse_json_object(self, data: Dict) -> Optional[pd.DataFrame]:
        """JSON 객체 파싱"""
        # 시계열 데이터 형태인지 확인
        if 'timestamp' in data and 'battery' in data:
            timestamps = data['timestamp']
            batteries = data['battery']
            
            df = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps),
                'battery': pd.to_numeric(batteries, errors='coerce')
            })
            return df.dropna()
        
        return None
    
    def extract_battery_data_from_dict(self, item: Dict) -> Optional[Dict]:
        """딕셔너리에서 배터리 데이터 추출"""
        timestamp = None
        battery = None
        
        # 시간 정보 추출
        time_keys = ['timestamp', 'time', 'datetime', '시간', 'date']
        for key in time_keys:
            if key in item:
                try:
                    timestamp = pd.to_datetime(item[key])
                    break
                except:
                    continue
        
        # 배터리 정보 추출
        battery_keys = ['battery', 'bat', 'voltage', 'v', '배터리', '전압']
        for key in battery_keys:
            if key in item:
                try:
                    battery = float(item[key])
                    break
                except:
                    continue
        
        if timestamp is not None and battery is not None:
            return {'timestamp': timestamp, 'battery': battery}
        
        return None
    
    def parse_text_log(self, content: str) -> Optional[pd.DataFrame]:
        """텍스트 로그 파싱"""
        lines = content.split('\n')
        result_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
        
            # 일반 텍스트 로그 파싱
            parsed_data = self.parse_text_line(line)
            if parsed_data:
                result_data.append(parsed_data)
        
        if result_data:
            df = pd.DataFrame(result_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            return df
        
        return None

    def parse_text_line(self, line: str) -> Optional[Dict]:
        """텍스트 라인 파싱"""
        timestamp = None
        battery = None
        
        # 타임스탬프 추출
        for pattern in self.patterns['timestamp']:
            match = re.search(pattern, line)
            if match:
                timestamp_str = match.group(1)
                timestamp = self.parse_timestamp(timestamp_str)
                break
        
        # 배터리 전압 추출
        for pattern in self.patterns['battery']:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    battery_str = match.group(1)
                    battery = float(battery_str)
                    
                    # 단위 변환 (mV -> V)
                    if battery > 100:
                        battery = battery / 1000
                    
                    break
                except ValueError:
                    continue
        
        # 타임스탬프가 없으면 현재 시간 사용
        if timestamp is None:
            timestamp = datetime.now()
        
        if battery is not None:
            return {
                'timestamp': timestamp,
                'battery': battery
            }
        
        return None
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """타임스탬프 문자열 파싱"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S'
        ]
        
        # Unix 타임스탬프 체크
        if timestamp_str.isdigit():
            try:
                return datetime.fromtimestamp(int(timestamp_str))
            except:
                pass
        
        # 포맷별 파싱 시도
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 유효성 검사 및 정리"""
        if df is None or len(df) == 0:
            return df
        
        # 중복 제거
        df = df.drop_duplicates(subset=['timestamp'])
        
        # 시간순 정렬
        df = df.sort_values('timestamp')
        
        # 배터리 전압 범위 체크 (OnBoard 로그는 더 넓은 범위)
        if 'source' in df.columns and df['source'].iloc[0] == 'onboard_monitor':
            # OnBoard 모니터 로그는 더 넓은 전압 범위 허용 (0V ~ 30V)
            df = df[(df['battery'] >= 0) & (df['battery'] <= 30)]
        else:
            # 일반 배터리 로그 (0V ~ 5V)
            df = df[(df['battery'] >= 0) & (df['battery'] <= 5)]
        
        # 극값 제거 (IQR 방법) - 너무 많은 데이터가 제거되지 않도록 조정
        Q1 = df['battery'].quantile(0.05)  # 5% 분위수
        Q3 = df['battery'].quantile(0.95)  # 95% 분위수
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 3 * IQR  # 더 관대한 범위
        upper_bound = Q3 + 3 * IQR
        
        # 극값은 제거하지 않고 플래그만 추가
        df['is_outlier'] = (df['battery'] < lower_bound) | (df['battery'] > upper_bound)
        
        # 인덱스 리셋
        df = df.reset_index(drop=True)
        
        return df
    
    def generate_test_data(self, num_points: int = 1000, 
                          duration_hours: int = 24) -> pd.DataFrame:
        """테스트용 데이터 생성"""
        start_time = datetime.now() - timedelta(hours=duration_hours)
        time_interval = timedelta(hours=duration_hours) / num_points
        
        timestamps = [start_time + i * time_interval for i in range(num_points)]
        
        # 배터리 방전 곡선 시뮬레이션
        base_voltage = 4.2  # 만충 전압
        min_voltage = 3.0   # 최소 전압
        
        # 지수적 감소 + 노이즈
        decay_rate = 0.1
        voltages = []
        
        for i in range(num_points):
            # 기본 방전 곡선
            progress = i / num_points
            voltage = min_voltage + (base_voltage - min_voltage) * np.exp(-decay_rate * progress * 10)
            
            # 노이즈 추가
            noise = np.random.normal(0, 0.02)
            voltage += noise
            
            # 가끔 스파이크 추가 (충전 등)
            if np.random.random() < 0.01:
                voltage += np.random.uniform(0.1, 0.3)
            
            # 범위 제한
            voltage = max(min_voltage, min(base_voltage, voltage))
            voltages.append(voltage)
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'battery': voltages
        })
        
        return self.validate_data(df)
    
    def generate_onboard_test_data(self, num_points: int = 500, 
                                  duration_hours: int = 12) -> pd.DataFrame:
        """OnBoard 모니터 스타일 테스트 데이터 생성"""
        start_time = datetime.now() - timedelta(hours=duration_hours)
        time_interval = timedelta(hours=duration_hours) / num_points
        
        timestamps = [start_time + i * time_interval for i in range(num_points)]
        
        # OnBoard 모니터 전압 시뮬레이션 (20V ~ 25V 범위)
        base_voltage = 25.0
        min_voltage = 20.0
        
        voltages = []
        statuses = ['STANDBY', 'ACTIVE', 'CHARGING', 'DISCHARGING']
        l1_states = ['X', 'O']
        l2_states = ['X', 'O']
        
        data = []
        
        for i in range(num_points):
            # 전압 생성 (더 안정적인 패턴)
            progress = i / num_points
            voltage = min_voltage + (base_voltage - min_voltage) * (1 - progress * 0.2)
            
            # 노이즈 추가 (작은 변동)
            noise = np.random.normal(0, 0.02)
            voltage += noise
            
            # 범위 제한
            voltage = max(min_voltage, min(base_voltage, voltage))
            
            data.append({
                'timestamp': timestamps[i],
                'battery': voltage,
                'timer': '00:00',
                'status': np.random.choice(statuses, p=[0.7, 0.1, 0.1, 0.1]),
                'L1': np.random.choice(l1_states, p=[0.8, 0.2]),
                'L2': np.random.choice(l2_states, p=[0.8, 0.2]),
                'memo': str(np.random.randint(3500, 4000)),
                'source': 'onboard_monitor'
            })
        
        df = pd.DataFrame(data)
        return self.validate_data(df)
    
    def get_file_info(self, file_path: str) -> Dict:
        """파일 정보 반환"""
        try:
            import os
            stat = os.stat(file_path)
            
            return {
                'path': file_path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'encoding': self.detect_encoding(file_path),
                'type': 'csv' if file_path.endswith('.csv') else 
                       'json' if file_path.endswith('.json') else 'text'
            }
        except Exception as e:
            return {'error': str(e)}

# 사용 예시
if __name__ == '__main__':
    parser = BatteryLogParser()
    
    # 테스트 데이터 생성
    test_data = parser.generate_test_data(500, 12)
    print(f"일반 테스트 데이터 생성: {len(test_data)}개 포인트")
    print(test_data.head())
    print(f"시간 범위: {test_data['timestamp'].min()} ~ {test_data['timestamp'].max()}")
    print(f"전압 범위: {test_data['battery'].min():.3f}V ~ {test_data['battery'].max():.3f}V")
    
    print("\n" + "="*50)
    
    # OnBoard 테스트 데이터 생성
    onboard_data = parser.generate_onboard_test_data(100, 6)
    print(f"OnBoard 테스트 데이터 생성: {len(onboard_data)}개 포인트")
    print(onboard_data.head())
    print(f"시간 범위: {onboard_data['timestamp'].min()} ~ {onboard_data['timestamp'].max()}")
    print(f"전압 범위: {onboard_data['battery'].min():.3f}V ~ {onboard_data['battery'].max():.3f}V") 