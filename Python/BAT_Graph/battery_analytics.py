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
        배터리 데이터 종합 분석
        
        Args:
            data: 배터리 데이터 (timestamp, battery 컬럼 필요)
            
        Returns:
            Dict: 분석 결과
        """
        if data is None or len(data) == 0:
            return {}
        
        try:
            # OnBoard 모니터 로그인지 확인
            is_onboard = 'source' in data.columns and data['source'].iloc[0] == 'onboard_monitor'
            
            results = {
                'statistics': self.calculate_statistics(data),
                'anomalies': self.detect_anomalies(data),
                'trends': self.analyze_trends(data),
                'patterns': self.find_patterns(data),
                'health': self.assess_battery_health(data),
                'predictions': self.predict_discharge_time(data),
                'segments': self.segment_analysis(data)
            }
            
            # OnBoard 특화 분석 추가
            if is_onboard:
                results['onboard_analysis'] = self.analyze_onboard_specific(data)
            
            return results
            
        except Exception as e:
            print(f"분석 오류: {e}")
            return {}
    
    def calculate_statistics(self, data: pd.DataFrame) -> Dict:
        """기본 통계 계산"""
        battery_data = data['battery']
        
        stats = {
            '평균 전압 (V)': f"{battery_data.mean():.3f}",
            '중앙값 전압 (V)': f"{battery_data.median():.3f}",
            '표준편차 (V)': f"{battery_data.std():.3f}",
            '최소 전압 (V)': f"{battery_data.min():.3f}",
            '최대 전압 (V)': f"{battery_data.max():.3f}",
            '전압 범위 (V)': f"{battery_data.max() - battery_data.min():.3f}",
            '변동계수 (%)': f"{(battery_data.std() / battery_data.mean()) * 100:.2f}",
            '데이터 포인트 수': f"{len(data):,}",
            '측정 기간': f"{self.get_duration_str(data)}",
            '평균 측정 간격': f"{self.get_average_interval(data)}"
        }
        
        # 백분위수 추가
        percentiles = [10, 25, 75, 90, 95, 99]
        for p in percentiles:
            stats[f'{p}% 백분위수 (V)'] = f"{battery_data.quantile(p/100):.3f}"
        
        return stats
    
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
        """평균 측정 간격 반환"""
        if len(data) < 2:
            return "계산 불가"
        
        intervals = data['timestamp'].diff().dropna()
        avg_interval = intervals.mean()
        
        if avg_interval.total_seconds() < 60:
            return f"{avg_interval.total_seconds():.1f}초"
        elif avg_interval.total_seconds() < 3600:
            return f"{avg_interval.total_seconds() / 60:.1f}분"
        else:
            return f"{avg_interval.total_seconds() / 3600:.1f}시간"

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