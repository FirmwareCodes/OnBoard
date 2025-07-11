import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class BatteryAnalytics:
    """배터리 데이터 분석 클래스"""
    
    def __init__(self):
        self.analysis_cache = {}
        
    def analyze(self, data: pd.DataFrame) -> Dict:
        """
        배터리 데이터 종합 분석 (OnBoard 로그 특화)
        
        Args:
            data: 배터리 데이터 (timestamp, battery 컬럼 필요)
            
        Returns:
            Dict: 분석 결과
        """
        if data is None or len(data) == 0:
            return {}
        
        try:
            # OnBoard 모니터 로그인지 확인
            is_onboard = self.is_onboard_log(data)
            
            if is_onboard:
                # OnBoard 로그 전용 분석
                results = {
                    'statistics': self.calculate_onboard_statistics(data),
                    'anomalies': self.detect_anomalies(data),
                    'trends': self.analyze_trends(data),
                    'patterns': self.find_onboard_patterns(data),
                    'health': self.assess_onboard_battery_health(data),
                    'predictions': self.predict_discharge_time(data),
                    'segments': self.segment_analysis(data),
                    'onboard_analysis': self.analyze_onboard_specific(data)
                }
            else:
                # 일반 배터리 로그 분석
                results = {
                    'statistics': self.calculate_statistics(data),
                    'anomalies': self.detect_anomalies(data),
                    'trends': self.analyze_trends(data),
                    'patterns': self.find_patterns(data),
                    'health': self.assess_battery_health(data),
                    'predictions': self.predict_discharge_time(data),
                    'segments': self.segment_analysis(data)
                }
            
            return results
            
        except Exception as e:
            print(f"분석 오류: {e}")
            return {}
    
    def is_onboard_log(self, data: pd.DataFrame) -> bool:
        """OnBoard 로그인지 확인"""
        if data is None or len(data) == 0:
            return False
        
        # OnBoard 로그의 특징적인 컬럼들 확인
        required_columns = ['timestamp', 'battery', 'timer', 'status', 'L1', 'L2', 'memo']
        has_onboard_columns = all(col in data.columns for col in required_columns)
        
        # 전압 범위 확인 (OnBoard는 20V~26V)
        if 'battery' in data.columns:
            avg_voltage = data['battery'].mean()
            voltage_in_onboard_range = 18.0 <= avg_voltage <= 28.0
        else:
            voltage_in_onboard_range = False
        
        return has_onboard_columns and voltage_in_onboard_range
    
    def calculate_onboard_statistics(self, data: pd.DataFrame) -> Dict:
        """OnBoard 로그 전용 통계 계산"""
        battery_data = data['battery']
        
        stats = {
            '평균 전압 (V)': f"{battery_data.mean():.3f}",
            '중앙값 전압 (V)': f"{battery_data.median():.3f}",
            '표준편차 (V)': f"{battery_data.std():.3f}",
            '최소 전압 (V)': f"{battery_data.min():.3f}",
            '최대 전압 (V)': f"{battery_data.max():.3f}",
            '전압 범위 (V)': f"{battery_data.max() - battery_data.min():.3f}",
            '변동계수 (%)': f"{(battery_data.std() / battery_data.mean()) * 100:.2f}",
            '데이터 포인트 수': f"{len(data):,}개",
            '측정 기간': f"{self.get_duration_str(data)}",
            '평균 측정 간격': f"{self.get_average_interval(data)}"
        }
        
        # OnBoard 특화 백분위수
        percentiles = [25, 50, 75, 90, 95, 99]
        for p in percentiles:
            stats[f'{p}% 백분위수 (V)'] = f"{battery_data.quantile(p/100):.3f}"
        
        # OnBoard 상태 통계
        if 'status' in data.columns:
            standby_ratio = (data['status'] == 'STANDBY').sum() / len(data) * 100
            stats['STANDBY 비율 (%)'] = f"{standby_ratio:.1f}"
            
            # 상태별 전압 평균
            status_voltage = data.groupby('status')['battery'].mean()
            for status, voltage in status_voltage.items():
                stats[f'{status} 평균전압 (V)'] = f"{voltage:.3f}"
        
        # LED 상태 통계
        if 'L1' in data.columns and 'L2' in data.columns:
            normal_led_ratio = ((data['L1'] == 'X') & (data['L2'] == 'X')).sum() / len(data) * 100
            stats['정상 LED 상태 (%)'] = f"{normal_led_ratio:.1f}"
        
        # 메모 통계
        if 'memo' in data.columns:
            try:
                memo_numeric = pd.to_numeric(data['memo'], errors='coerce').dropna()
                if len(memo_numeric) > 0:
                    stats['메모 평균값'] = f"{memo_numeric.mean():.1f}"
                    stats['메모 범위'] = f"{memo_numeric.min():.0f} ~ {memo_numeric.max():.0f}"
                    stats['메모 표준편차'] = f"{memo_numeric.std():.1f}"
            except:
                pass
        
        return stats
    
    def calculate_statistics(self, data: pd.DataFrame) -> Dict:
        """일반 배터리 로그 통계 계산"""
        battery_data = data['battery']
        
        stats = {
            '평균 전압 (V)': f"{battery_data.mean():.3f}",
            '중앙값 전압 (V)': f"{battery_data.median():.3f}",
            '표준편차 (V)': f"{battery_data.std():.3f}",
            '최소 전압 (V)': f"{battery_data.min():.3f}",
            '최대 전압 (V)': f"{battery_data.max():.3f}",
            '전압 범위 (V)': f"{battery_data.max() - battery_data.min():.3f}",
            '변동계수 (%)': f"{(battery_data.std() / battery_data.mean()) * 100:.2f}",
            '데이터 포인트 수': f"{len(data):,}개",
            '측정 기간': f"{self.get_duration_str(data)}",
            '평균 측정 간격': f"{self.get_average_interval(data)}"
        }
        
        # 백분위수
        percentiles = [25, 50, 75, 90, 95, 99]
        for p in percentiles:
            stats[f'{p}% 백분위수 (V)'] = f"{battery_data.quantile(p/100):.3f}"
        
        return stats
    
    def find_onboard_patterns(self, data: pd.DataFrame) -> Dict:
        """OnBoard 로그 특화 패턴 찾기"""
        patterns = {}
        
        # 전압 패턴 분석
        patterns['voltage'] = self.analyze_voltage_patterns(data)
        
        # 상태 패턴 분석
        if 'status' in data.columns:
            patterns['status'] = self.analyze_status_patterns(data)
        
        # LED 패턴 분석
        if 'L1' in data.columns and 'L2' in data.columns:
            patterns['led'] = self.analyze_led_patterns(data)
        
        # 메모 패턴 분석
        if 'memo' in data.columns:
            patterns['memo'] = self.analyze_memo_patterns(data)
        
        # 시간대별 패턴
        patterns['hourly'] = self.analyze_hourly_patterns(data)
        
        return patterns
    
    def analyze_voltage_patterns(self, data: pd.DataFrame) -> Dict:
        """전압 패턴 분석"""
        battery_data = data['battery']
        
        # 충전/방전 구간 감지
        voltage_diff = battery_data.diff()
        
        # 충전 구간 (0.01V 이상 증가)
        charging_points = (voltage_diff > 0.01).sum()
        
        # 방전 구간 (0.01V 이상 감소)
        discharging_points = (voltage_diff < -0.01).sum()
        
        # 안정 구간 (변화 미미)
        stable_points = (voltage_diff.abs() <= 0.01).sum()
        
        return {
            '충전 포인트': f"{charging_points}개",
            '방전 포인트': f"{discharging_points}개",
            '안정 포인트': f"{stable_points}개",
            '충전 비율': f"{charging_points/len(data)*100:.1f}%",
            '방전 비율': f"{discharging_points/len(data)*100:.1f}%",
            '안정 비율': f"{stable_points/len(data)*100:.1f}%"
        }
    
    def analyze_memo_patterns(self, data: pd.DataFrame) -> Dict:
        """메모 패턴 분석"""
        try:
            memo_numeric = pd.to_numeric(data['memo'], errors='coerce').dropna()
            
            if len(memo_numeric) == 0:
                return {'error': '숫자 메모 데이터 없음'}
            
            # 메모 값의 트렌드
            memo_trend = self.calculate_memo_trend(memo_numeric)
            
            # 메모-전압 상관관계
            memo_battery_corr = memo_numeric.corr(data.loc[memo_numeric.index, 'battery'])
            
            return {
                '메모 범위': f"{memo_numeric.min():.0f} ~ {memo_numeric.max():.0f}",
                '메모 평균': f"{memo_numeric.mean():.1f}",
                '메모 변동성': f"{memo_numeric.std():.1f}",
                '메모 트렌드': memo_trend,
                '전압 상관관계': f"{memo_battery_corr:.3f}",
                '메모 변화 빈도': f"{(memo_numeric.diff().abs() > 1).sum()}회"
            }
        except Exception as e:
            return {'error': f'메모 분석 오류: {str(e)}'}
    
    def calculate_memo_trend(self, memo_series: pd.Series) -> str:
        """메모 값의 트렌드 계산"""
        if len(memo_series) < 2:
            return '데이터 부족'
        
        # 선형 회귀로 트렌드 계산
        x = np.arange(len(memo_series))
        coeffs = np.polyfit(x, memo_series.values, 1)
        slope = coeffs[0]
        
        if abs(slope) < 0.1:
            return f'안정 (기울기: {slope:.3f})'
        elif slope > 0:
            return f'상승 (기울기: {slope:.3f})'
        else:
            return f'하락 (기울기: {slope:.3f})'
    
    def detect_anomalies(self, data: pd.DataFrame, method: str = 'iqr') -> pd.DataFrame:
        """이상치 감지"""
        battery_data = data['battery']
        
        if method == 'iqr':
            # IQR 방법
            Q1 = battery_data.quantile(0.25)
            Q3 = battery_data.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            anomaly_mask = (battery_data < lower_bound) | (battery_data > upper_bound)
            
        elif method == 'zscore':
            # Z-점수 방법
            z_scores = np.abs((battery_data - battery_data.mean()) / battery_data.std())
            anomaly_mask = z_scores > 3
            
        elif method == 'isolation':
            try:
                from sklearn.ensemble import IsolationForest
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                anomaly_predictions = iso_forest.fit_predict(battery_data.values.reshape(-1, 1))
                anomaly_mask = anomaly_predictions == -1
            except ImportError:
                # sklearn이 없으면 IQR 방법 사용
                return self.detect_anomalies(data, 'iqr')
        
        else:
            # 기본값은 IQR
            return self.detect_anomalies(data, 'iqr')
        
        anomalies = data[anomaly_mask].copy()
        
        # 이상치 분류
        if len(anomalies) > 0:
            anomalies['anomaly_type'] = self.classify_anomalies(anomalies, data)
        
        return anomalies
    
    def classify_anomalies(self, anomalies: pd.DataFrame, full_data: pd.DataFrame) -> List[str]:
        """이상치 분류"""
        battery_mean = full_data['battery'].mean()
        classifications = []
        
        for _, anomaly in anomalies.iterrows():
            if anomaly['battery'] > battery_mean * 1.2:
                classifications.append('충전 스파이크')
            elif anomaly['battery'] < battery_mean * 0.8:
                classifications.append('급격한 방전')
            else:
                classifications.append('일반 이상치')
        
        return classifications
    
    def analyze_trends(self, data: pd.DataFrame) -> Dict:
        """트렌드 분석"""
        battery_data = data['battery'].values
        time_numeric = np.arange(len(battery_data))
        
        # 선형 회귀
        coeffs = np.polyfit(time_numeric, battery_data, 1)
        slope = coeffs[0]
        
        # 방전률 계산 (V/hour)
        if len(data) > 1:
            time_span_hours = (data['timestamp'].max() - data['timestamp'].min()).total_seconds() / 3600
            discharge_rate = slope * len(data) / time_span_hours if time_span_hours > 0 else 0
        else:
            discharge_rate = 0
        
        # 트렌드 방향 결정
        if abs(slope) < 1e-6:
            trend_direction = '안정'
        elif slope < 0:
            trend_direction = '하락 (방전)'
        else:
            trend_direction = '상승 (충전)'
        
        # 변화 패턴 분석
        changes = np.diff(battery_data)
        positive_changes = np.sum(changes > 0)
        negative_changes = np.sum(changes < 0)
        
        return {
            '전체 트렌드': trend_direction,
            '기울기': f"{slope:.6f}",
            '방전률 (V/h)': f"{discharge_rate:.4f}",
            '상승 구간': f"{positive_changes}개",
            '하락 구간': f"{negative_changes}개",
            '변동성': f"{np.std(changes):.4f}",
            'R² 값': f"{self.calculate_r_squared(time_numeric, battery_data, coeffs):.4f}"
        }
    
    def calculate_r_squared(self, x: np.ndarray, y: np.ndarray, coeffs: np.ndarray) -> float:
        """R² 값 계산"""
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        
        if ss_tot == 0:
            return 1.0
        
        return 1 - (ss_res / ss_tot)
    
    def find_patterns(self, data: pd.DataFrame) -> Dict:
        """패턴 찾기"""
        patterns = {}
        
        # 주기적 패턴 감지
        patterns['periodic'] = self.detect_periodic_patterns(data)
        
        # 충전 패턴 감지
        patterns['charging'] = self.detect_charging_patterns(data)
        
        # 방전 패턴 감지
        patterns['discharging'] = self.detect_discharging_patterns(data)
        
        # 시간대별 패턴
        patterns['hourly'] = self.analyze_hourly_patterns(data)
        
        return patterns
    
    def detect_periodic_patterns(self, data: pd.DataFrame) -> Dict:
        """주기적 패턴 감지"""
        try:
            from scipy import signal
            
            # 리샘플링하여 등간격 데이터 생성
            resampled = data.set_index('timestamp').resample('1min')['battery'].mean().dropna()
            
            if len(resampled) < 10:
                return {'detected': False, 'reason': '데이터 부족'}
            
            # FFT를 이용한 주파수 분석
            frequencies, power = signal.periodogram(resampled.values)
            
            # 주요 주파수 찾기
            dominant_freq_idx = np.argmax(power[1:]) + 1  # DC 성분 제외
            dominant_frequency = frequencies[dominant_freq_idx]
            dominant_period = 1 / dominant_frequency if dominant_frequency > 0 else float('inf')
            
            # 주기성 강도 계산
            periodicity_strength = power[dominant_freq_idx] / np.sum(power)
            
            return {
                'detected': periodicity_strength > 0.1,
                'dominant_period_minutes': f"{dominant_period:.2f}",
                'strength': f"{periodicity_strength:.3f}",
                'frequency': f"{dominant_frequency:.6f}"
            }
            
        except ImportError:
            return {'detected': False, 'reason': 'scipy 모듈 필요'}
        except Exception as e:
            return {'detected': False, 'reason': f'분석 오류: {str(e)}'}
    
    def detect_charging_patterns(self, data: pd.DataFrame) -> Dict:
        """충전 패턴 감지"""
        # 전압 증가 구간 찾기
        voltage_diff = data['battery'].diff()
        charging_threshold = 0.01  # 0.01V 이상 증가
        
        charging_segments = []
        current_segment = []
        
        for i, diff in enumerate(voltage_diff):
            if diff > charging_threshold:
                current_segment.append(i)
            else:
                if len(current_segment) > 2:  # 최소 3개 포인트
                    charging_segments.append(current_segment)
                current_segment = []
        
        # 마지막 세그먼트 처리
        if len(current_segment) > 2:
            charging_segments.append(current_segment)
        
        if len(charging_segments) == 0:
            return {
                'count': 0,
                'total_duration': '0분',
                'average_rate': '0 V/h',
                'detected': False
            }
        
        # 충전 통계 계산
        total_duration = timedelta()
        total_voltage_increase = 0
        
        for segment in charging_segments:
            start_idx, end_idx = segment[0], segment[-1]
            duration = data.loc[end_idx, 'timestamp'] - data.loc[start_idx, 'timestamp']
            voltage_increase = data.loc[end_idx, 'battery'] - data.loc[start_idx, 'battery']
            
            total_duration += duration
            total_voltage_increase += voltage_increase
        
        average_rate = total_voltage_increase / (total_duration.total_seconds() / 3600) if total_duration.total_seconds() > 0 else 0
        
        return {
            'count': len(charging_segments),
            'total_duration': f"{total_duration.total_seconds() / 60:.1f}분",
            'average_rate': f"{average_rate:.3f} V/h",
            'total_increase': f"{total_voltage_increase:.3f} V",
            'detected': True
        }
    
    def detect_discharging_patterns(self, data: pd.DataFrame) -> Dict:
        """방전 패턴 감지"""
        # 전압 감소 구간 찾기
        voltage_diff = data['battery'].diff()
        discharge_threshold = -0.005  # 0.005V 이상 감소
        
        discharge_segments = []
        current_segment = []
        
        for i, diff in enumerate(voltage_diff):
            if diff < discharge_threshold:
                current_segment.append(i)
            else:
                if len(current_segment) > 5:  # 최소 6개 포인트
                    discharge_segments.append(current_segment)
                current_segment = []
        
        # 마지막 세그먼트 처리
        if len(current_segment) > 5:
            discharge_segments.append(current_segment)
        
        if len(discharge_segments) == 0:
            return {
                'count': 0,
                'total_duration': '0분',
                'average_rate': '0 V/h',
                'detected': False
            }
        
        # 방전 통계 계산
        total_duration = timedelta()
        total_voltage_decrease = 0
        
        for segment in discharge_segments:
            start_idx, end_idx = segment[0], segment[-1]
            duration = data.loc[end_idx, 'timestamp'] - data.loc[start_idx, 'timestamp']
            voltage_decrease = data.loc[start_idx, 'battery'] - data.loc[end_idx, 'battery']
            
            total_duration += duration
            total_voltage_decrease += voltage_decrease
        
        average_rate = total_voltage_decrease / (total_duration.total_seconds() / 3600) if total_duration.total_seconds() > 0 else 0
        
        return {
            'count': len(discharge_segments),
            'total_duration': f"{total_duration.total_seconds() / 60:.1f}분",
            'average_rate': f"{average_rate:.3f} V/h",
            'total_decrease': f"{total_voltage_decrease:.3f} V",
            'detected': True
        }
    
    def analyze_hourly_patterns(self, data: pd.DataFrame) -> Dict:
        """시간대별 패턴 분석"""
        data_copy = data.copy()
        data_copy['hour'] = data_copy['timestamp'].dt.hour
        
        hourly_stats = data_copy.groupby('hour')['battery'].agg(['mean', 'std', 'count']).round(3)
        
        # 가장 높은/낮은 평균 전압 시간대
        peak_hour = hourly_stats['mean'].idxmax()
        valley_hour = hourly_stats['mean'].idxmin()
        
        return {
            'peak_hour': f"{peak_hour}시",
            'peak_voltage': f"{hourly_stats.loc[peak_hour, 'mean']:.3f} V",
            'valley_hour': f"{valley_hour}시",
            'valley_voltage': f"{hourly_stats.loc[valley_hour, 'mean']:.3f} V",
            'daily_variation': f"{hourly_stats['mean'].max() - hourly_stats['mean'].min():.3f} V",
            'hourly_data': hourly_stats.to_dict()
        }
    
    def analyze_onboard_specific(self, data: pd.DataFrame) -> Dict:
        """OnBoard 모니터 로그 특화 분석"""
        onboard_results = {}
        
        # 상태별 분석
        if 'status' in data.columns:
            onboard_results['status_analysis'] = self.analyze_status_patterns(data)
        
        # L1, L2 상태 분석
        if 'L1' in data.columns and 'L2' in data.columns:
            onboard_results['led_analysis'] = self.analyze_led_patterns(data)
        
        # 메모 필드 분석 (숫자 값)
        if 'memo' in data.columns:
            onboard_results['memo_analysis'] = self.analyze_memo_values(data)
        
        # 타이머 분석
        if 'timer' in data.columns:
            onboard_results['timer_analysis'] = self.analyze_timer_patterns(data)
        
        return onboard_results
    
    def analyze_status_patterns(self, data: pd.DataFrame) -> Dict:
        """상태 패턴 분석"""
        status_counts = data['status'].value_counts()
        total_count = len(data)
        
        # 상태별 평균 전압
        status_voltage = data.groupby('status')['battery'].agg(['mean', 'std', 'count']).round(3)
        
        # 상태 변화 분석
        status_changes = data['status'].ne(data['status'].shift()).sum() - 1
        
        return {
            'status_distribution': {
                status: f"{count}회 ({count/total_count*100:.1f}%)" 
                for status, count in status_counts.items()
            },
            'status_voltage_stats': status_voltage.to_dict(),
            'status_changes': f"{status_changes}회",
            'most_common_status': status_counts.index[0],
            'status_stability': f"{(1 - status_changes/total_count)*100:.1f}%"
        }
    
    def analyze_led_patterns(self, data: pd.DataFrame) -> Dict:
        """LED 상태 패턴 분석"""
        # L1, L2 조합 분석
        led_combinations = data.groupby(['L1', 'L2']).size()
        total_count = len(data)
        
        # L1, L2 각각의 상태 분석
        l1_counts = data['L1'].value_counts()
        l2_counts = data['L2'].value_counts()
        
        # 상태 변화 분석
        l1_changes = data['L1'].ne(data['L1'].shift()).sum() - 1
        l2_changes = data['L2'].ne(data['L2'].shift()).sum() - 1
        
        return {
            'led_combinations': {
                f"L1:{l1}, L2:{l2}": f"{count}회 ({count/total_count*100:.1f}%)" 
                for (l1, l2), count in led_combinations.items()
            },
            'L1_distribution': {
                state: f"{count}회 ({count/total_count*100:.1f}%)" 
                for state, count in l1_counts.items()
            },
            'L2_distribution': {
                state: f"{count}회 ({count/total_count*100:.1f}%)" 
                for state, count in l2_counts.items()
            },
            'L1_changes': f"{l1_changes}회",
            'L2_changes': f"{l2_changes}회",
            'led_activity': f"{(l1_changes + l2_changes)/(total_count*2)*100:.1f}% 변화율"
        }
    
    def analyze_memo_values(self, data: pd.DataFrame) -> Dict:
        """메모 값(숫자) 분석"""
        try:
            # 숫자로 변환 가능한 메모만 분석
            numeric_memos = pd.to_numeric(data['memo'], errors='coerce').dropna()
            
            if len(numeric_memos) == 0:
                return {'error': '숫자 메모 데이터 없음'}
            
            return {
                'memo_range': f"{numeric_memos.min()} ~ {numeric_memos.max()}",
                'memo_mean': f"{numeric_memos.mean():.1f}",
                'memo_std': f"{numeric_memos.std():.1f}",
                'memo_trend': self.analyze_memo_trend(numeric_memos),
                'memo_battery_correlation': f"{numeric_memos.corr(data.loc[numeric_memos.index, 'battery']):.3f}"
            }
        except Exception as e:
            return {'error': f'메모 분석 오류: {str(e)}'}
    
    def analyze_memo_trend(self, memo_series: pd.Series) -> str:
        """메모 값의 트렌드 분석"""
        if len(memo_series) < 2:
            return '데이터 부족'
        
        # 선형 회귀로 트렌드 계산
        x = np.arange(len(memo_series))
        coeffs = np.polyfit(x, memo_series.values, 1)
        slope = coeffs[0]
        
        if abs(slope) < 0.1:
            return '안정'
        elif slope > 0:
            return f'상승 ({slope:.2f}/단위)'
        else:
            return f'하락 ({slope:.2f}/단위)'
    
    def analyze_timer_patterns(self, data: pd.DataFrame) -> Dict:
        """타이머 패턴 분석"""
        timer_counts = data['timer'].value_counts()
        
        # 타이머 값을 초 단위로 변환하여 분석
        timer_seconds = []
        for timer_str in data['timer']:
            try:
                if ':' in timer_str:
                    parts = timer_str.split(':')
                    if len(parts) == 2:
                        minutes, seconds = map(int, parts)
                        timer_seconds.append(minutes * 60 + seconds)
            except:
                continue
        
        if timer_seconds:
            timer_series = pd.Series(timer_seconds)
            return {
                'timer_distribution': {
                    timer: f"{count}회" for timer, count in timer_counts.head(10).items()
                },
                'timer_range_seconds': f"{min(timer_seconds)} ~ {max(timer_seconds)}초",
                'average_timer': f"{np.mean(timer_seconds):.1f}초",
                'timer_activity': f"{(timer_series > 0).sum()}/{len(timer_series)} 활성"
            }
        else:
            return {
                'timer_distribution': {
                    timer: f"{count}회" for timer, count in timer_counts.head(5).items()
                },
                'note': '대부분 00:00 상태'
            }
    
    def assess_battery_health(self, data: pd.DataFrame) -> Dict:
        """배터리 건강도 평가 (OnBoard 로그 고려)"""
        battery_data = data['battery']
        
        # OnBoard 로그인지 확인
        is_onboard = 'source' in data.columns and data['source'].iloc[0] == 'onboard_monitor'
        
        if is_onboard:
            # OnBoard 모니터용 건강도 평가 (20V~25V 범위)
            voltage_health = self.assess_onboard_voltage_health(battery_data)
        else:
            # 일반 배터리용 건강도 평가
            voltage_health = self.assess_voltage_health(battery_data)
        
        # 변동성 기반 건강도
        stability_health = self.assess_stability_health(battery_data)
        
        # 방전 패턴 기반 건강도
        discharge_health = self.assess_discharge_health(data)
        
        # 종합 건강도 (가중 평균)
        overall_health = (voltage_health * 0.4 + stability_health * 0.3 + discharge_health * 0.3)
        
        health_grade = self.get_health_grade(overall_health)
        
        return {
            '종합 건강도': f"{overall_health:.1f}/100",
            '건강도 등급': health_grade,
            '전압 건강도': f"{voltage_health:.1f}/100",
            '안정성 건강도': f"{stability_health:.1f}/100",
            '방전 건강도': f"{discharge_health:.1f}/100",
            '권장사항': self.get_health_recommendations(overall_health, is_onboard)
        }
    
    def assess_onboard_voltage_health(self, battery_data: pd.Series) -> float:
        """OnBoard 모니터 전압 건강도 평가 (20V~25V 기준)"""
        mean_voltage = battery_data.mean()
        
        # OnBoard 모니터 전압 기준 (20V ~ 25V)
        if mean_voltage >= 24.5:
            return 100.0
        elif mean_voltage >= 23.0:
            return 85.0
        elif mean_voltage >= 22.0:
            return 70.0
        elif mean_voltage >= 21.0:
            return 55.0
        elif mean_voltage >= 20.0:
            return 40.0
        else:
            return 20.0
    
    def assess_voltage_health(self, battery_data: pd.Series) -> float:
        """전압 레벨 기반 건강도"""
        mean_voltage = battery_data.mean()
        
        # 리튬 배터리 기준 (3.0V ~ 4.2V)
        if mean_voltage >= 3.8:
            return 100.0
        elif mean_voltage >= 3.5:
            return 80.0
        elif mean_voltage >= 3.2:
            return 60.0
        elif mean_voltage >= 3.0:
            return 40.0
        else:
            return 20.0
    
    def assess_stability_health(self, battery_data: pd.Series) -> float:
        """안정성 기반 건강도"""
        cv = battery_data.std() / battery_data.mean()  # 변동계수
        
        if cv <= 0.02:  # 2% 이하
            return 100.0
        elif cv <= 0.05:  # 5% 이하
            return 80.0
        elif cv <= 0.10:  # 10% 이하
            return 60.0
        elif cv <= 0.15:  # 15% 이하
            return 40.0
        else:
            return 20.0
    
    def assess_discharge_health(self, data: pd.DataFrame) -> float:
        """방전 패턴 기반 건강도"""
        # 방전 기울기 계산
        time_numeric = np.arange(len(data))
        coeffs = np.polyfit(time_numeric, data['battery'].values, 1)
        slope = coeffs[0]
        
        # 정상적인 방전 기울기인지 확인
        if -0.0001 <= slope <= 0.0001:  # 거의 변화 없음 (좋음)
            return 100.0
        elif -0.0005 <= slope < -0.0001:  # 천천히 방전 (좋음)
            return 90.0
        elif -0.001 <= slope < -0.0005:  # 보통 방전
            return 70.0
        elif -0.002 <= slope < -0.001:  # 빠른 방전
            return 50.0
        else:  # 매우 빠른 방전 또는 비정상적 패턴
            return 30.0
    
    def get_health_grade(self, health_score: float) -> str:
        """건강도 등급 변환"""
        if health_score >= 90:
            return "우수"
        elif health_score >= 80:
            return "양호"
        elif health_score >= 70:
            return "보통"
        elif health_score >= 60:
            return "주의"
        else:
            return "교체 필요"
    
    def get_health_recommendations(self, health_score: float, is_onboard: bool = False) -> str:
        """건강도 기반 권장사항 (OnBoard 고려)"""
        base_recommendations = {
            90: "전압 상태가 우수합니다. 현재 모니터링 패턴을 유지하세요.",
            80: "전압 상태가 양호합니다. 정기적인 모니터링을 권장합니다.",
            70: "전압이 다소 불안정합니다. 시스템 점검이 필요할 수 있습니다.",
            60: "전압 상태에 주의가 필요합니다. 전원 공급 시스템을 확인하세요.",
            0: "전압 상태가 불안정합니다. 즉시 시스템 점검을 권장합니다."
        }
        
        if is_onboard:
            onboard_suffix = " OnBoard 모니터 시스템의 전원 공급 상태를 확인하세요."
        else:
            onboard_suffix = ""
        
        for threshold in sorted(base_recommendations.keys(), reverse=True):
            if health_score >= threshold:
                return base_recommendations[threshold] + onboard_suffix
        
        return base_recommendations[0] + onboard_suffix
    
    def predict_discharge_time(self, data: pd.DataFrame) -> Dict:
        """방전 시간 예측"""
        if len(data) < 10:
            return {'predicted': False, 'reason': '데이터 부족'}
        
        try:
            # 최근 데이터로 트렌드 계산
            recent_data = data.tail(min(100, len(data)))
            time_numeric = np.arange(len(recent_data))
            
            # 선형 회귀로 방전 기울기 계산
            coeffs = np.polyfit(time_numeric, recent_data['battery'].values, 1)
            slope = coeffs[0]
            
            if slope >= 0:
                return {
                    'predicted': False,
                    'reason': '방전 중이 아님 (전압 증가 또는 안정)',
                    'current_trend': '충전 또는 안정'
                }
            
            # 현재 전압
            current_voltage = recent_data['battery'].iloc[-1]
            
            # 방전 종료 전압 (보통 3.0V)
            cutoff_voltage = 3.0
            
            if current_voltage <= cutoff_voltage:
                return {
                    'predicted': True,
                    'remaining_time': '0분 (이미 방전됨)',
                    'current_voltage': f"{current_voltage:.3f}V"
                }
            
            # 예상 방전 시간 계산
            voltage_to_discharge = current_voltage - cutoff_voltage
            time_interval = (recent_data['timestamp'].iloc[-1] - recent_data['timestamp'].iloc[0]).total_seconds() / len(recent_data)
            
            # 방전에 필요한 단계 수
            steps_to_discharge = voltage_to_discharge / abs(slope)
            time_to_discharge = steps_to_discharge * time_interval
            
            # 시간 포맷팅
            hours = int(time_to_discharge // 3600)
            minutes = int((time_to_discharge % 3600) // 60)
            
            prediction_confidence = self.calculate_prediction_confidence(recent_data, coeffs)
            
            return {
                'predicted': True,
                'remaining_time': f"{hours}시간 {minutes}분",
                'current_voltage': f"{current_voltage:.3f}V",
                'cutoff_voltage': f"{cutoff_voltage:.3f}V",
                'discharge_rate': f"{abs(slope * 3600):.4f} V/h",
                'confidence': f"{prediction_confidence:.1f}%"
            }
            
        except Exception as e:
            return {'predicted': False, 'reason': f'예측 오류: {str(e)}'}
    
    def calculate_prediction_confidence(self, data: pd.DataFrame, coeffs: np.ndarray) -> float:
        """예측 신뢰도 계산"""
        time_numeric = np.arange(len(data))
        r_squared = self.calculate_r_squared(time_numeric, data['battery'].values, coeffs)
        
        # R² 값을 신뢰도 퍼센티지로 변환
        return min(100.0, r_squared * 100)
    
    def segment_analysis(self, data: pd.DataFrame) -> Dict:
        """구간별 분석"""
        if len(data) < 10:
            return {}
        
        # 데이터를 시간 기준으로 여러 구간으로 나누기
        num_segments = min(5, len(data) // 10)
        segment_size = len(data) // num_segments
        
        segments = []
        for i in range(num_segments):
            start_idx = i * segment_size
            end_idx = (i + 1) * segment_size if i < num_segments - 1 else len(data)
            
            segment_data = data.iloc[start_idx:end_idx]
            
            segment_stats = {
                'index': i + 1,
                'start_time': segment_data['timestamp'].min(),
                'end_time': segment_data['timestamp'].max(),
                'duration': str(segment_data['timestamp'].max() - segment_data['timestamp'].min()),
                'start_voltage': f"{segment_data['battery'].iloc[0]:.3f}V",
                'end_voltage': f"{segment_data['battery'].iloc[-1]:.3f}V",
                'min_voltage': f"{segment_data['battery'].min():.3f}V",
                'max_voltage': f"{segment_data['battery'].max():.3f}V",
                'avg_voltage': f"{segment_data['battery'].mean():.3f}V",
                'voltage_change': f"{segment_data['battery'].iloc[-1] - segment_data['battery'].iloc[0]:.3f}V",
                'trend': '상승' if segment_data['battery'].iloc[-1] > segment_data['battery'].iloc[0] else '하락'
            }
            
            segments.append(segment_stats)
        
        return {
            'total_segments': num_segments,
            'segments': segments,
            'summary': self.summarize_segments(segments)
        }
    
    def summarize_segments(self, segments: List[Dict]) -> Dict:
        """구간 요약"""
        if not segments:
            return {}
        
        rising_segments = sum(1 for s in segments if s['trend'] == '상승')
        falling_segments = sum(1 for s in segments if s['trend'] == '하락')
        
        total_voltage_change = sum(float(s['voltage_change'].replace('V', '')) for s in segments)
        
        return {
            '상승 구간': f"{rising_segments}개",
            '하락 구간': f"{falling_segments}개",
            '총 전압 변화': f"{total_voltage_change:.3f}V",
            '평균 구간 변화': f"{total_voltage_change / len(segments):.3f}V"
        }
    
    def get_duration_str(self, data: pd.DataFrame) -> str:
        """측정 기간 문자열 반환"""
        duration = data['timestamp'].max() - data['timestamp'].min()
        
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0:
            parts.append(f"{minutes}분")
        
        return " ".join(parts) if parts else "1분 미만"
    
    def get_average_interval(self, data: pd.DataFrame) -> str:
        """평균 측정 간격 계산"""
        if len(data) < 2:
            return "계산 불가"
        
        time_diffs = data['timestamp'].diff().dropna()
        avg_interval = time_diffs.mean()
        
        if avg_interval.total_seconds() < 60:
            return f"{avg_interval.total_seconds():.1f}초"
        elif avg_interval.total_seconds() < 3600:
            return f"{avg_interval.total_seconds()/60:.1f}분"
        else:
            return f"{avg_interval.total_seconds()/3600:.1f}시간"

    def comprehensive_battery_diagnostic(self, data: pd.DataFrame) -> Dict:
        """종합 배터리 진단"""
        battery_data = data['battery']
        
        # 기본 진단 항목
        diagnostic = {
            '배터리 타입 추정': self.estimate_battery_type(battery_data),
            '전압 안정성': self.assess_voltage_stability(battery_data),
            '내부 저항 추정': self.estimate_internal_resistance(data),
            '셀 균형도': self.assess_cell_balance(battery_data),
            '온도 영향 분석': self.analyze_temperature_effects(data),
            '메모리 효과': self.detect_memory_effect(battery_data),
            '자가방전율': self.calculate_self_discharge_rate(data),
            '충전 효율성': self.assess_charging_efficiency(data)
        }
        
        return diagnostic

    def estimate_battery_type(self, battery_data: pd.Series) -> str:
        """배터리 타입 추정"""
        avg_voltage = battery_data.mean()
        max_voltage = battery_data.max()
        
        if 20 <= avg_voltage <= 26:
            return "리튬이온 6S (OnBoard 시스템)"
        elif 3.0 <= avg_voltage <= 4.2:
            return "리튬이온 1S"
        elif 11 <= avg_voltage <= 13:
            return "리튬이온 3S 또는 납산"
        elif 22 <= avg_voltage <= 26:
            return "리튬이온 6S"
        else:
            return f"커스텀 ({avg_voltage:.1f}V 평균)"

    def assess_voltage_stability(self, battery_data: pd.Series) -> str:
        """전압 안정성 평가"""
        cv = (battery_data.std() / battery_data.mean()) * 100
        
        if cv < 1:
            return f"매우 안정 (CV: {cv:.2f}%)"
        elif cv < 3:
            return f"안정 (CV: {cv:.2f}%)"
        elif cv < 5:
            return f"보통 (CV: {cv:.2f}%)"
        else:
            return f"불안정 (CV: {cv:.2f}%)"

    def estimate_internal_resistance(self, data: pd.DataFrame) -> str:
        """내부 저항 추정"""
        # 전압 변화율로 내부 저항 추정
        voltage_changes = data['battery'].diff().abs()
        resistance_indicator = voltage_changes.mean()
        
        if resistance_indicator < 0.01:
            return f"낮음 (~{resistance_indicator*100:.2f}mΩ 추정)"
        elif resistance_indicator < 0.05:
            return f"보통 (~{resistance_indicator*100:.2f}mΩ 추정)"
        else:
            return f"높음 (~{resistance_indicator*100:.2f}mΩ 추정)"

    def assess_cell_balance(self, battery_data: pd.Series) -> str:
        """셀 균형도 평가"""
        voltage_range = battery_data.max() - battery_data.min()
        
        if voltage_range < 0.1:
            return f"우수 (범위: {voltage_range:.3f}V)"
        elif voltage_range < 0.3:
            return f"양호 (범위: {voltage_range:.3f}V)"
        else:
            return f"주의 필요 (범위: {voltage_range:.3f}V)"

    def analyze_temperature_effects(self, data: pd.DataFrame) -> str:
        """온도 영향 분석"""
        # 시간대별 전압 변화로 온도 영향 추정
        if 'timestamp' in data.columns:
            data['hour'] = data['timestamp'].dt.hour
            hourly_avg = data.groupby('hour')['battery'].mean()
            temp_variation = hourly_avg.std()
            
            if temp_variation < 0.05:
                return f"온도 영향 미미 (변동: {temp_variation:.3f}V)"
            elif temp_variation < 0.1:
                return f"온도 영향 보통 (변동: {temp_variation:.3f}V)"
            else:
                return f"온도 영향 큼 (변동: {temp_variation:.3f}V)"
        
        return "온도 영향 분석 불가"

    def detect_memory_effect(self, battery_data: pd.Series) -> str:
        """메모리 효과 감지"""
        # 전압 플래토 구간 감지
        voltage_diff = battery_data.diff().abs()
        plateau_points = (voltage_diff < 0.001).sum()
        plateau_ratio = plateau_points / len(battery_data)
        
        if plateau_ratio > 0.3:
            return f"메모리 효과 의심 ({plateau_ratio*100:.1f}% 플래토)"
        else:
            return f"메모리 효과 없음 ({plateau_ratio*100:.1f}% 플래토)"

    def calculate_self_discharge_rate(self, data: pd.DataFrame) -> str:
        """자가방전율 계산"""
        # 장기간 비활성 구간에서의 전압 감소 분석
        if len(data) < 100:
            return "데이터 부족"
        
        # 안정된 구간 찾기
        voltage_changes = data['battery'].diff().abs()
        stable_periods = voltage_changes < voltage_changes.quantile(0.1)
        
        if stable_periods.sum() > 50:
            stable_data = data[stable_periods]
            if len(stable_data) > 1:
                time_span = (stable_data['timestamp'].max() - stable_data['timestamp'].min()).total_seconds() / 3600
                voltage_drop = stable_data['battery'].iloc[0] - stable_data['battery'].iloc[-1]
                
                if time_span > 0:
                    discharge_rate = (voltage_drop / time_span) * 24  # V/day
                    return f"{discharge_rate:.4f} V/일"
        
        return "측정 불가"

    def assess_charging_efficiency(self, data: pd.DataFrame) -> str:
        """충전 효율성 평가"""
        # 충전 구간 감지
        voltage_increases = data['battery'].diff() > 0.01
        charging_periods = voltage_increases.sum()
        
        if charging_periods > 0:
            efficiency_ratio = charging_periods / len(data)
            if efficiency_ratio > 0.8:
                return f"매우 높음 ({efficiency_ratio*100:.1f}%)"
            elif efficiency_ratio > 0.6:
                return f"높음 ({efficiency_ratio*100:.1f}%)"
            elif efficiency_ratio > 0.4:
                return f"보통 ({efficiency_ratio*100:.1f}%)"
            else:
                return f"낮음 ({efficiency_ratio*100:.1f}%)"
        
        return "충전 구간 없음"

    def analyze_battery_performance(self, data: pd.DataFrame) -> Dict:
        """배터리 성능 분석"""
        battery_data = data['battery']
        
        performance = {
            '응답성': self.assess_response_time(data),
            '회복력': self.assess_recovery_capability(data),
            '부하 처리 능력': self.assess_load_handling(data),
            '전압 유지 능력': self.assess_voltage_maintenance(battery_data),
            '피크 성능': self.analyze_peak_performance(battery_data),
            '지속 성능': self.analyze_sustained_performance(data)
        }
        
        return performance

    def assess_response_time(self, data: pd.DataFrame) -> str:
        """응답 시간 평가"""
        voltage_changes = data['battery'].diff().abs()
        response_time = voltage_changes.mean()
        
        if response_time > 0.1:
            return f"빠름 ({response_time:.3f}V/측정)"
        elif response_time > 0.05:
            return f"보통 ({response_time:.3f}V/측정)"
        else:
            return f"느림 ({response_time:.3f}V/측정)"

    def assess_recovery_capability(self, data: pd.DataFrame) -> str:
        """회복 능력 평가"""
        # 전압 하락 후 회복 패턴 분석
        battery_data = data['battery']
        drops = battery_data.diff() < -0.05
        
        if drops.sum() > 0:
            recovery_periods = []
            in_drop = False
            drop_start = None
            
            for i, is_drop in enumerate(drops):
                if is_drop and not in_drop:
                    in_drop = True
                    drop_start = i
                elif not is_drop and in_drop:
                    in_drop = False
                    if drop_start is not None:
                        recovery_periods.append(i - drop_start)
            
            if recovery_periods:
                avg_recovery = np.mean(recovery_periods)
                return f"회복 시간: {avg_recovery:.1f} 측정주기"
            
        return "회복 패턴 없음"

    def assess_load_handling(self, data: pd.DataFrame) -> str:
        """부하 처리 능력 평가"""
        voltage_variance = data['battery'].var()
        
        if voltage_variance < 0.01:
            return f"우수 (분산: {voltage_variance:.4f})"
        elif voltage_variance < 0.05:
            return f"양호 (분산: {voltage_variance:.4f})"
        else:
            return f"개선 필요 (분산: {voltage_variance:.4f})"

    def assess_voltage_maintenance(self, battery_data: pd.Series) -> str:
        """전압 유지 능력 평가"""
        voltage_drop = battery_data.iloc[0] - battery_data.iloc[-1]
        maintenance_ratio = 1 - abs(voltage_drop) / battery_data.iloc[0]
        
        if maintenance_ratio > 0.98:
            return f"탁월 ({maintenance_ratio*100:.2f}%)"
        elif maintenance_ratio > 0.95:
            return f"우수 ({maintenance_ratio*100:.2f}%)"
        elif maintenance_ratio > 0.90:
            return f"양호 ({maintenance_ratio*100:.2f}%)"
        else:
            return f"주의 ({maintenance_ratio*100:.2f}%)"

    def analyze_peak_performance(self, battery_data: pd.Series) -> str:
        """피크 성능 분석"""
        peak_voltage = battery_data.max()
        peak_ratio = peak_voltage / battery_data.mean()
        
        return f"피크: {peak_voltage:.3f}V (평균 대비 {peak_ratio:.2f}배)"

    def analyze_sustained_performance(self, data: pd.DataFrame) -> str:
        """지속 성능 분석"""
        # 90% 이상 성능 유지 시간 계산
        target_voltage = data['battery'].max() * 0.9
        sustained_periods = (data['battery'] >= target_voltage).sum()
        sustained_ratio = sustained_periods / len(data)
        
        return f"90% 이상 성능 유지: {sustained_ratio*100:.1f}%"

    def analyze_capacity_metrics(self, data: pd.DataFrame) -> Dict:
        """용량 메트릭 분석"""
        battery_data = data['battery']
        
        capacity = {
            '명목 용량 추정': self.estimate_nominal_capacity(data),
            '실제 용량': self.calculate_actual_capacity(data),
            '용량 손실률': self.calculate_capacity_loss(data),
            '용량 편차': self.calculate_capacity_deviation(battery_data),
            '에너지 밀도': self.estimate_energy_density(data),
            '방전 깊이': self.calculate_discharge_depth(battery_data)
        }
        
        return capacity

    def estimate_nominal_capacity(self, data: pd.DataFrame) -> str:
        """명목 용량 추정"""
        avg_voltage = data['battery'].mean()
        
        # 전압 기반 용량 추정 (리튬이온 기준)
        if 20 <= avg_voltage <= 26:
            estimated_capacity = "5000-10000mAh (6S 시스템)"
        elif 11 <= avg_voltage <= 13:
            estimated_capacity = "2000-5000mAh (3S 시스템)"
        elif 3.0 <= avg_voltage <= 4.2:
            estimated_capacity = "1000-3000mAh (1S 시스템)"
        else:
            estimated_capacity = "추정 불가"
        
        return estimated_capacity

    def calculate_actual_capacity(self, data: pd.DataFrame) -> str:
        """실제 용량 계산"""
        # 방전 곡선 기반 용량 계산
        voltage_drop = data['battery'].iloc[0] - data['battery'].iloc[-1]
        time_span = (data['timestamp'].max() - data['timestamp'].min()).total_seconds() / 3600
        
        if time_span > 0 and voltage_drop > 0:
            discharge_rate = voltage_drop / time_span
            return f"방전률 기반: {discharge_rate:.3f}V/h"
        
        return "계산 불가"

    def calculate_capacity_loss(self, data: pd.DataFrame) -> str:
        """용량 손실률 계산"""
        # 첫 번째와 마지막 구간 비교
        first_quarter = data.iloc[:len(data)//4]
        last_quarter = data.iloc[-len(data)//4:]
        
        first_avg = first_quarter['battery'].mean()
        last_avg = last_quarter['battery'].mean()
        
        capacity_loss = (first_avg - last_avg) / first_avg * 100
        
        return f"{capacity_loss:.2f}%"

    def calculate_capacity_deviation(self, battery_data: pd.Series) -> str:
        """용량 편차 계산"""
        deviation = battery_data.std() / battery_data.mean() * 100
        return f"{deviation:.2f}%"

    def estimate_energy_density(self, data: pd.DataFrame) -> str:
        """에너지 밀도 추정"""
        avg_voltage = data['battery'].mean()
        
        # 일반적인 리튬이온 배터리 기준
        if avg_voltage > 20:
            energy_density = "150-250 Wh/kg"
        elif avg_voltage > 10:
            energy_density = "200-300 Wh/kg"
        else:
            energy_density = "250-350 Wh/kg"
        
        return energy_density

    def calculate_discharge_depth(self, battery_data: pd.Series) -> str:
        """방전 깊이 계산"""
        min_voltage = battery_data.min()
        max_voltage = battery_data.max()
        
        if max_voltage > min_voltage:
            discharge_depth = (max_voltage - min_voltage) / max_voltage * 100
            return f"{discharge_depth:.2f}%"
        
        return "0%"

    def analyze_thermal_behavior(self, data: pd.DataFrame) -> Dict:
        """열적 거동 분석"""
        thermal = {
            '열적 안정성': self.assess_thermal_stability(data),
            '온도 계수': self.calculate_temperature_coefficient(data),
            '열 방출 특성': self.analyze_heat_dissipation(data),
            '온도 민감도': self.assess_temperature_sensitivity(data)
        }
        
        return thermal

    def assess_thermal_stability(self, data: pd.DataFrame) -> str:
        """열적 안정성 평가"""
        # 시간대별 전압 변화로 열적 안정성 평가
        if len(data) > 24:
            voltage_hourly_std = data.groupby(data['timestamp'].dt.hour)['battery'].std().mean()
            
            if voltage_hourly_std < 0.01:
                return "매우 안정"
            elif voltage_hourly_std < 0.05:
                return "안정"
            else:
                return "불안정"
        
        return "데이터 부족"

    def calculate_temperature_coefficient(self, data: pd.DataFrame) -> str:
        """온도 계수 계산"""
        # 시간 기반 온도 계수 추정
        if len(data) > 100:
            hourly_changes = data.groupby(data['timestamp'].dt.hour)['battery'].mean().diff().mean()
            temp_coefficient = hourly_changes * 1000  # mV/°C 추정
            
            return f"{temp_coefficient:.2f} mV/°C (추정)"
        
        return "계산 불가"

    def analyze_heat_dissipation(self, data: pd.DataFrame) -> str:
        """열 방출 특성 분석"""
        voltage_changes = data['battery'].diff().abs()
        heat_indicator = voltage_changes.mean() * 1000  # mV 단위
        
        if heat_indicator < 1:
            return f"낮음 ({heat_indicator:.2f}mV 변화)"
        elif heat_indicator < 5:
            return f"보통 ({heat_indicator:.2f}mV 변화)"
        else:
            return f"높음 ({heat_indicator:.2f}mV 변화)"

    def assess_temperature_sensitivity(self, data: pd.DataFrame) -> str:
        """온도 민감도 평가"""
        daily_variance = data.groupby(data['timestamp'].dt.date)['battery'].var().mean()
        
        if daily_variance < 0.001:
            return "낮음"
        elif daily_variance < 0.01:
            return "보통"
        else:
            return "높음"

    def analyze_charging_cycles(self, data: pd.DataFrame) -> Dict:
        """충전 사이클 분석"""
        cycles = {
            '충전 사이클 수': self.count_charging_cycles(data),
            '평균 충전 시간': self.calculate_average_charge_time(data),
            '충전 효율성': self.calculate_charge_efficiency(data),
            '사이클 수명 추정': self.estimate_cycle_life(data)
        }
        
        return cycles

    def count_charging_cycles(self, data: pd.DataFrame) -> str:
        """충전 사이클 수 계산"""
        # 전압 증가 구간을 충전으로 간주
        voltage_increases = data['battery'].diff() > 0.1
        cycles = 0
        in_charge = False
        
        for increase in voltage_increases:
            if increase and not in_charge:
                cycles += 1
                in_charge = True
            elif not increase:
                in_charge = False
        
        return f"{cycles}회"

    def calculate_average_charge_time(self, data: pd.DataFrame) -> str:
        """평균 충전 시간 계산"""
        charge_periods = []
        voltage_increases = data['battery'].diff() > 0.05
        
        current_period = 0
        for increase in voltage_increases:
            if increase:
                current_period += 1
            else:
                if current_period > 0:
                    charge_periods.append(current_period)
                current_period = 0
        
        if charge_periods:
            avg_period = np.mean(charge_periods)
            return f"{avg_period:.1f} 측정주기"
        
        return "충전 구간 없음"

    def calculate_charge_efficiency(self, data: pd.DataFrame) -> str:
        """충전 효율성 계산"""
        voltage_increases = (data['battery'].diff() > 0).sum()
        total_periods = len(data) - 1
        
        if total_periods > 0:
            efficiency = voltage_increases / total_periods * 100
            return f"{efficiency:.1f}%"
        
        return "0%"

    def estimate_cycle_life(self, data: pd.DataFrame) -> str:
        """사이클 수명 추정"""
        voltage_degradation = (data['battery'].iloc[0] - data['battery'].iloc[-1]) / data['battery'].iloc[0]
        
        if voltage_degradation > 0:
            # 단순 추정: 20% 용량 손실까지의 사이클 수
            estimated_cycles = int(0.2 / voltage_degradation)
            return f"약 {estimated_cycles:,}회 (추정)"
        
        return "수명 저하 미감지"

    def analyze_battery_degradation(self, data: pd.DataFrame) -> Dict:
        """배터리 열화 분석"""
        degradation = {
            '열화 정도': self.assess_degradation_level(data),
            '열화 속도': self.calculate_degradation_rate(data),
            '잔여 수명': self.estimate_remaining_life(data),
            '열화 원인': self.identify_degradation_causes(data)
        }
        
        return degradation

    def assess_degradation_level(self, data: pd.DataFrame) -> str:
        """열화 정도 평가"""
        voltage_loss = (data['battery'].iloc[0] - data['battery'].iloc[-1]) / data['battery'].iloc[0] * 100
        
        if voltage_loss < 1:
            return f"미미 ({voltage_loss:.2f}%)"
        elif voltage_loss < 5:
            return f"경미 ({voltage_loss:.2f}%)"
        elif voltage_loss < 10:
            return f"보통 ({voltage_loss:.2f}%)"
        else:
            return f"심각 ({voltage_loss:.2f}%)"

    def calculate_degradation_rate(self, data: pd.DataFrame) -> str:
        """열화 속도 계산"""
        time_span = (data['timestamp'].max() - data['timestamp'].min()).total_seconds() / (24 * 3600)  # 일
        voltage_loss = data['battery'].iloc[0] - data['battery'].iloc[-1]
        
        if time_span > 0:
            degradation_rate = voltage_loss / time_span
            return f"{degradation_rate:.4f} V/일"
        
        return "계산 불가"

    def estimate_remaining_life(self, data: pd.DataFrame) -> str:
        """잔여 수명 추정"""
        current_voltage = data['battery'].iloc[-1]
        voltage_loss_rate = (data['battery'].iloc[0] - current_voltage) / len(data)
        
        # 20% 추가 손실까지의 시간 계산
        target_loss = current_voltage * 0.2
        
        if voltage_loss_rate > 0:
            remaining_measurements = target_loss / voltage_loss_rate
            return f"약 {remaining_measurements:.0f} 측정주기"
        
        return "수명 저하 미감지"

    def identify_degradation_causes(self, data: pd.DataFrame) -> str:
        """열화 원인 식별"""
        causes = []
        
        # 과방전 확인
        if data['battery'].min() < data['battery'].mean() * 0.7:
            causes.append("과방전")
        
        # 과충전 확인
        if data['battery'].max() > data['battery'].mean() * 1.3:
            causes.append("과충전")
        
        # 고온 사용 추정
        voltage_variance = data['battery'].var()
        if voltage_variance > 0.1:
            causes.append("온도 스트레스")
        
        # 빈번한 사이클링
        voltage_changes = (data['battery'].diff().abs() > 0.1).sum()
        if voltage_changes > len(data) * 0.1:
            causes.append("빈번한 사이클링")
        
        if causes:
            return ", ".join(causes)
        else:
            return "특별한 원인 없음"

    def assess_battery_risks(self, data: pd.DataFrame) -> Dict:
        """배터리 위험 평가"""
        risks = {
            '안전성 등급': self.assess_safety_level(data),
            '과방전 위험': self.assess_over_discharge_risk(data),
            '과충전 위험': self.assess_over_charge_risk(data),
            '열폭주 위험': self.assess_thermal_runaway_risk(data),
            '단락 위험': self.assess_short_circuit_risk(data)
        }
        
        return risks

    def assess_safety_level(self, data: pd.DataFrame) -> str:
        """안전성 등급 평가"""
        battery_data = data['battery']
        
        # 전압 안정성, 변동성 등을 종합 평가
        stability = battery_data.std() / battery_data.mean()
        voltage_range = (battery_data.max() - battery_data.min()) / battery_data.mean()
        
        safety_score = 100 - (stability * 100 + voltage_range * 50)
        
        if safety_score > 90:
            return f"A급 (안전) - {safety_score:.1f}점"
        elif safety_score > 80:
            return f"B급 (양호) - {safety_score:.1f}점"
        elif safety_score > 70:
            return f"C급 (주의) - {safety_score:.1f}점"
        else:
            return f"D급 (위험) - {safety_score:.1f}점"

    def assess_over_discharge_risk(self, data: pd.DataFrame) -> str:
        """과방전 위험 평가"""
        min_voltage = data['battery'].min()
        mean_voltage = data['battery'].mean()
        
        risk_ratio = min_voltage / mean_voltage
        
        if risk_ratio > 0.9:
            return "낮음"
        elif risk_ratio > 0.8:
            return "보통"
        else:
            return f"높음 (최저: {min_voltage:.2f}V)"

    def assess_over_charge_risk(self, data: pd.DataFrame) -> str:
        """과충전 위험 평가"""
        max_voltage = data['battery'].max()
        mean_voltage = data['battery'].mean()
        
        risk_ratio = max_voltage / mean_voltage
        
        if risk_ratio < 1.1:
            return "낮음"
        elif risk_ratio < 1.2:
            return "보통"
        else:
            return f"높음 (최고: {max_voltage:.2f}V)"

    def assess_thermal_runaway_risk(self, data: pd.DataFrame) -> str:
        """열폭주 위험 평가"""
        voltage_spikes = (data['battery'].diff().abs() > 0.5).sum()
        
        if voltage_spikes == 0:
            return "낮음"
        elif voltage_spikes < 5:
            return f"보통 ({voltage_spikes}회 스파이크)"
        else:
            return f"높음 ({voltage_spikes}회 스파이크)"

    def assess_short_circuit_risk(self, data: pd.DataFrame) -> str:
        """단락 위험 평가"""
        sudden_drops = (data['battery'].diff() < -1.0).sum()
        
        if sudden_drops == 0:
            return "낮음"
        elif sudden_drops < 3:
            return f"보통 ({sudden_drops}회 급강하)"
        else:
            return f"높음 ({sudden_drops}회 급강하)"

    def calculate_efficiency_metrics(self, data: pd.DataFrame) -> Dict:
        """효율성 메트릭 계산"""
        efficiency = {
            '에너지 효율성': self.calculate_energy_efficiency(data),
            '전력 효율성': self.calculate_power_efficiency(data),
            '충방전 효율성': self.calculate_charge_discharge_efficiency(data),
            '시스템 효율성': self.calculate_system_efficiency(data)
        }
        
        return efficiency

    def calculate_energy_efficiency(self, data: pd.DataFrame) -> str:
        """에너지 효율성 계산"""
        voltage_stability = 1 - (data['battery'].std() / data['battery'].mean())
        efficiency_percentage = voltage_stability * 100
        
        return f"{efficiency_percentage:.1f}%"

    def calculate_power_efficiency(self, data: pd.DataFrame) -> str:
        """전력 효율성 계산"""
        # 전압 변화의 부드러움으로 효율성 평가
        voltage_smoothness = 1 - (data['battery'].diff().abs().mean() / data['battery'].mean())
        efficiency_percentage = voltage_smoothness * 100
        
        return f"{efficiency_percentage:.1f}%"

    def calculate_charge_discharge_efficiency(self, data: pd.DataFrame) -> str:
        """충방전 효율성 계산"""
        # 충전과 방전 구간의 균형성 평가
        increases = (data['battery'].diff() > 0).sum()
        decreases = (data['battery'].diff() < 0).sum()
        
        if increases + decreases > 0:
            balance = 1 - abs(increases - decreases) / (increases + decreases)
            efficiency_percentage = balance * 100
            return f"{efficiency_percentage:.1f}%"
        
        return "계산 불가"

    def calculate_system_efficiency(self, data: pd.DataFrame) -> str:
        """시스템 효율성 계산"""
        # 전체적인 시스템 효율성 종합 평가
        voltage_efficiency = 1 - (data['battery'].std() / data['battery'].mean())
        stability_efficiency = 1 - ((data['battery'].max() - data['battery'].min()) / data['battery'].mean())
        
        system_efficiency = (voltage_efficiency + stability_efficiency) / 2 * 100
        
        return f"{system_efficiency:.1f}%"

    def assess_onboard_battery_health(self, data: pd.DataFrame) -> Dict:
        """OnBoard 배터리 건강도 평가"""
        battery_data = data['battery']
        
        # OnBoard 전압 건강도 (20V~26V 기준)
        voltage_health = self.assess_onboard_voltage_health(battery_data)
        
        # 변동성 기반 건강도
        stability_health = self.assess_stability_health(battery_data)
        
        # OnBoard 상태 기반 건강도
        status_health = self.assess_onboard_status_health(data)
        
        # 종합 건강도 (가중 평균)
        overall_health = (voltage_health * 0.5 + stability_health * 0.3 + status_health * 0.2)
        
        health_grade = self.get_health_grade(overall_health)
        
        return {
            '종합 건강도': f"{overall_health:.1f}/100",
            '건강도 등급': health_grade,
            '전압 건강도': f"{voltage_health:.1f}/100",
            '안정성 건강도': f"{stability_health:.1f}/100",
            '시스템 건강도': f"{status_health:.1f}/100",
            '권장사항': self.get_onboard_health_recommendations(overall_health)
        }
    
    def assess_onboard_status_health(self, data: pd.DataFrame) -> float:
        """OnBoard 상태 기반 건강도"""
        if 'status' not in data.columns:
            return 80.0  # 기본값
        
        # STANDBY 비율이 높을수록 안정적
        standby_ratio = (data['status'] == 'STANDBY').sum() / len(data)
        
        # LED 상태 정상 비율
        led_health = 80.0  # 기본값
        if 'L1' in data.columns and 'L2' in data.columns:
            normal_led_ratio = ((data['L1'] == 'X') & (data['L2'] == 'X')).sum() / len(data)
            led_health = normal_led_ratio * 100
        
        # 종합 상태 건강도
        status_health = (standby_ratio * 0.7 + led_health/100 * 0.3) * 100
        
        return min(100.0, status_health)
    
    def get_onboard_health_recommendations(self, health_score: float) -> str:
        """OnBoard 건강도 기반 권장사항"""
        if health_score >= 90:
            return "OnBoard 시스템이 우수한 상태입니다. 현재 모니터링 수준을 유지하세요."
        elif health_score >= 80:
            return "OnBoard 시스템이 양호한 상태입니다. 주간 점검을 권장합니다."
        elif health_score >= 70:
            return "OnBoard 시스템 상태가 보통입니다. 3일 내 상세 점검이 필요합니다."
        elif health_score >= 60:
            return "OnBoard 시스템에 주의가 필요합니다. 24시간 내 점검을 권장합니다."
        else:
            return "OnBoard 시스템이 위험 상태입니다. 즉시 전문가 점검 및 배터리 교체를 검토하세요."

# 사용 예시
if __name__ == '__main__':
    from battery_log_parser import BatteryLogParser
    
    # 테스트 데이터 생성
    parser = BatteryLogParser()
    test_data = parser.generate_test_data(200, 6)
    
    # 분석 수행
    analytics = BatteryAnalytics()
    results = analytics.analyze(test_data)
    
    # 결과 출력
    print("=== 배터리 분석 결과 ===")
    for category, data in results.items():
        print(f"\n[{category.upper()}]")
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {data}") 