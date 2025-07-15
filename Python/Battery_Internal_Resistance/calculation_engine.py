#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배터리 내부저항 계산 엔진
Battery Internal Resistance Calculation Engine

배터리 내부저항 계산을 위한 핵심 로직과 검증 기능을 제공합니다.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime

@dataclass
class BatteryMeasurement:
    """배터리 측정 데이터 클래스"""
    no_load_voltage: float  # 무부하 전압 (V)
    load_voltage: float     # 부하 전압 (V)
    load_resistance: float  # 부하 저항 (Ω)
    measured_current: Optional[float] = None  # 측정된 부하 전류 (A) - 선택적
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@dataclass
class CalculationResult:
    """계산 결과 데이터 클래스"""
    internal_resistance: float      # 내부저항 (Ω)
    load_current: float            # 부하 전류 (A)
    voltage_drop: float            # 전압 강하 (V)
    power_loss: float              # 전력 손실 (W)
    efficiency: float              # 효율 (%)
    measurement: BatteryMeasurement
    
    def to_dict(self) -> Dict:
        """결과를 딕셔너리로 변환"""
        return {
            'timestamp': self.measurement.timestamp,
            'v_no_load': self.measurement.no_load_voltage,
            'v_load': self.measurement.load_voltage,
            'r_load': self.measurement.load_resistance,
            'r_internal': self.internal_resistance,
            'i_load': self.load_current,
            'v_drop': self.voltage_drop,
            'power_loss': self.power_loss,
            'efficiency': self.efficiency
        }

class BatteryCalculationEngine:
    """배터리 내부저항 계산 엔진"""
    
    @staticmethod
    def validate_measurement(measurement: BatteryMeasurement) -> Tuple[bool, str]:
        """측정값 검증
        
        Args:
            measurement: 측정 데이터
            
        Returns:
            (검증 성공 여부, 오류 메시지)
        """
        if measurement.no_load_voltage <= 0:
            return False, "무부하 전압은 양수여야 합니다."
        
        if measurement.load_voltage <= 0:
            return False, "부하 전압은 양수여야 합니다."
        
        if measurement.load_resistance <= 0:
            return False, "부하 저항은 양수여야 합니다."
        
        if measurement.load_voltage >= measurement.no_load_voltage:
            return False, "부하 전압은 무부하 전압보다 작아야 합니다."
        
        # 전압 차이가 너무 작은 경우 경고
        voltage_diff = measurement.no_load_voltage - measurement.load_voltage
        if voltage_diff < 0.001:  # 1mV 미만
            return False, "전압 차이가 너무 작습니다. 더 큰 부하를 사용하세요."
        
        return True, ""
    
    @staticmethod
    def calculate_internal_resistance(measurement: BatteryMeasurement) -> CalculationResult:
        """직류부하법(DC Load Method)을 이용한 내부저항 계산
        
        직류부하법은 배터리에 일정한 직류 부하를 연결하여 내부저항을 측정하는 방법입니다.
        
        측정 절차:
        1. 무부하 상태에서 개방전압(Open Circuit Voltage, OCV) 측정
        2. 일정한 직류 부하 연결
        3. 안정화 대기 (중요: 부하 연결 후 전압이 안정될 때까지)
        4. 부하 상태에서 단자전압과 부하전류 측정
        
        계산 공식 (직류부하법):
        R_internal = (V_OCV - V_load) / I_load
        
        여기서:
        - V_OCV: 개방전압 (무부하 전압)
        - V_load: 부하 단자전압
        - I_load: 부하 전류
        
        Args:
            measurement: 측정 데이터
            
        Returns:
            계산 결과
            
        Raises:
            ValueError: 입력값이 유효하지 않은 경우
        """
        # 입력값 검증
        is_valid, error_msg = BatteryCalculationEngine.validate_measurement(measurement)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 직류부하법 계산
        v_ocv = measurement.no_load_voltage      # 개방전압 (OCV)
        v_load = measurement.load_voltage        # 부하 단자전압
        r_load = measurement.load_resistance     # 부하 저항
        
        # 부하 전류 결정 (측정값 우선 사용 - 더 정확)
        if measurement.measured_current is not None and measurement.measured_current > 0:
            # 실제 측정된 전류 사용 (권장)
            i_load = measurement.measured_current
            current_source = "measured"
            
            # 옴의 법칙과 비교하여 측정 정확도 확인
            i_calculated = v_load / r_load
            current_deviation = abs(i_load - i_calculated) / i_calculated * 100
            
            if current_deviation > 5:
                print(f"주의: 측정 전류({i_load:.3f}A)와 계산 전류({i_calculated:.3f}A) 편차 {current_deviation:.1f}%")
                print(f"부하 저항값 또는 전류 측정을 재확인하세요.")
        else:
            # 옴의 법칙으로 계산 (부하 저항이 정확한 경우)
            i_load = v_load / r_load
            current_source = "calculated"
            current_deviation = 0
        
        # 직류부하법 공식 적용
        # R_internal = (V_OCV - V_load) / I_load
        voltage_drop = v_ocv - v_load
        internal_resistance = voltage_drop / i_load
        
        # 직류부하법 검증 (키르히호프 전압 법칙)
        # V_OCV = V_load + (I_load × R_internal)
        # 또는: V_load = V_OCV - (I_load × R_internal)
        calculated_load_voltage = v_ocv - (i_load * internal_resistance)
        verification_error = abs(calculated_load_voltage - v_load)
        
        if verification_error > 0.001:  # 1mV 오차
            print(f"경고: 직류부하법 계산 검증 오차 {verification_error*1000:.2f}mV")
        
        # 전력 분석 (직류부하법)
        power_internal_loss = i_load ** 2 * internal_resistance  # 내부저항 전력손실
        power_load = v_load * i_load                             # 부하 전력
        power_total = v_ocv * i_load                             # 총 공급전력 (이론값)
        
        # 효율 계산
        efficiency = (power_load / power_total) * 100 if power_total > 0 else 0
        
        # 직류부하법 특성 분석
        load_factor = i_load * r_load / v_ocv  # 부하율
        internal_drop_ratio = voltage_drop / v_ocv * 100  # 내부전압강하율
        
        result = CalculationResult(
            internal_resistance=internal_resistance,
            load_current=i_load,
            voltage_drop=voltage_drop,
            power_loss=power_internal_loss,
            efficiency=efficiency,
            measurement=measurement
        )
        
        # 직류부하법 관련 추가 정보
        result._method = "DC_Load_Method"
        result._current_source = current_source
        result._current_deviation = current_deviation
        result._verification_error = verification_error
        result._load_factor = load_factor
        result._internal_drop_ratio = internal_drop_ratio
        result._power_load = power_load
        result._power_total = power_total
        
        return result
    
    @staticmethod
    def calculate_multiple_loads(measurements: List[BatteryMeasurement]) -> List[CalculationResult]:
        """여러 부하에 대한 내부저항 계산
        
        Args:
            measurements: 측정 데이터 리스트
            
        Returns:
            계산 결과 리스트
        """
        results = []
        for measurement in measurements:
            try:
                result = BatteryCalculationEngine.calculate_internal_resistance(measurement)
                results.append(result)
            except ValueError as e:
                # 오류가 발생한 측정값은 건너뛰고 로그 남김
                print(f"측정값 오류: {e}")
                continue
        
        return results
    
    @staticmethod
    def estimate_battery_capacity(voltage: float, internal_resistance: float) -> Dict[str, float]:
        """배터리 용량 추정 (대략적인 추정)
        
        Args:
            voltage: 배터리 전압
            internal_resistance: 내부저항 (Ω)
            
        Returns:
            용량 추정 결과
        """
        # 일반적인 배터리 타입별 내부저항 범위 (mΩ)
        battery_types = {
            'Li-ion_18650': (20, 100),      # 리튬이온 18650
            'Li-ion_Cell': (10, 50),        # 리튬이온 셀
            'Li-ion_2S': (40, 200),         # 리튬이온 2S (7.4V)
            'Li-ion_3S': (60, 300),         # 리튬이온 3S (11.1V)
            'Li-ion_4S': (80, 400),         # 리튬이온 4S (14.8V)
            'Li-ion_6S': (120, 600),        # 리튬이온 6S (22.2V)
            'NiMH_AA': (100, 500),          # 니켈수소 AA
            'Lead_Acid_12V': (1, 10),       # 납축전지 12V
            'Lead_Acid_24V': (2, 20),       # 납축전지 24V
            'LiFePO4_1S': (15, 80),         # 리튬인산철 1S
            'LiFePO4_4S': (60, 320),        # 리튬인산철 4S (12.8V)
        }
        
        r_internal_mohm = internal_resistance * 1000  # mΩ 단위로 변환
        
        estimated_type = "Unknown"
        confidence = 0.0
        
        # 전압과 내부저항을 기반으로 배터리 타입 추정
        for battery_type, (min_r, max_r) in battery_types.items():
            if min_r <= r_internal_mohm <= max_r:
                # 전압 범위 확인
                if battery_type == 'Li-ion_18650' and 3.0 <= voltage <= 4.2:
                    estimated_type = battery_type
                    confidence = 0.8
                elif battery_type == 'Li-ion_Cell' and 3.0 <= voltage <= 4.2:
                    estimated_type = battery_type
                    confidence = 0.8
                elif battery_type == 'Li-ion_2S' and 6.0 <= voltage <= 8.4:
                    estimated_type = battery_type
                    confidence = 0.9
                elif battery_type == 'Li-ion_3S' and 9.0 <= voltage <= 12.6:
                    estimated_type = battery_type
                    confidence = 0.9
                elif battery_type == 'Li-ion_4S' and 12.0 <= voltage <= 16.8:
                    estimated_type = battery_type
                    confidence = 0.9
                elif battery_type == 'Li-ion_6S' and 18.0 <= voltage <= 25.2:
                    estimated_type = battery_type
                    confidence = 0.9
                elif battery_type == 'NiMH_AA' and 1.0 <= voltage <= 1.5:
                    estimated_type = battery_type
                    confidence = 0.7
                elif battery_type == 'Lead_Acid_12V' and 10.0 <= voltage <= 15.0:
                    estimated_type = battery_type
                    confidence = 0.8
                elif battery_type == 'Lead_Acid_24V' and 20.0 <= voltage <= 30.0:
                    estimated_type = battery_type
                    confidence = 0.8
                elif battery_type == 'LiFePO4_1S' and 3.0 <= voltage <= 3.6:
                    estimated_type = battery_type
                    confidence = 0.8
                elif battery_type == 'LiFePO4_4S' and 12.0 <= voltage <= 14.4:
                    estimated_type = battery_type
                    confidence = 0.8
        
        # 배터리 상태 추정 (6S 배터리 고려)
        health_status = "Good"
        if "6S" in estimated_type:
            if r_internal_mohm > 500:
                health_status = "Poor"
            elif r_internal_mohm > 300:
                health_status = "Fair"
        else:
            if r_internal_mohm > 200:
                health_status = "Poor"
            elif r_internal_mohm > 100:
                health_status = "Fair"
        
        return {
            'estimated_type': estimated_type,
            'confidence': confidence,
            'health_status': health_status,
            'internal_resistance_mohm': r_internal_mohm
        }
    
    @staticmethod
    def calculate_per_cell_resistance(total_voltage: float, internal_resistance: float, cell_count: int = 1) -> Dict:
        """셀당 내부저항 계산 (직렬 연결 배터리용)
        
        Args:
            total_voltage: 전체 배터리 전압
            internal_resistance: 전체 내부저항 (Ω)
            cell_count: 셀 개수
            
        Returns:
            셀당 분석 결과
        """
        cell_voltage = total_voltage / cell_count
        cell_resistance = internal_resistance / cell_count  # 직렬 연결이므로 저항은 분배되지 않음
        
        # 실제로는 각 셀의 내부저항이 합쳐지므로
        estimated_cell_resistance = internal_resistance / cell_count
        
        return {
            'cell_count': cell_count,
            'cell_voltage': cell_voltage,
            'estimated_cell_resistance': estimated_cell_resistance,
            'estimated_cell_resistance_mohm': estimated_cell_resistance * 1000,
            'total_internal_resistance': internal_resistance,
            'total_internal_resistance_mohm': internal_resistance * 1000
        }
    
    @staticmethod
    def detect_cell_count(voltage: float) -> int:
        """전압을 기반으로 셀 개수 자동 감지
        
        Args:
            voltage: 배터리 전압
            
        Returns:
            추정 셀 개수
        """
        # 리튬이온 배터리 기준 (3.7V nominal per cell)
        if 3.0 <= voltage <= 4.2:
            return 1  # 1S
        elif 6.0 <= voltage <= 8.4:
            return 2  # 2S
        elif 9.0 <= voltage <= 12.6:
            return 3  # 3S
        elif 12.0 <= voltage <= 16.8:
            return 4  # 4S
        elif 15.0 <= voltage <= 21.0:
            return 5  # 5S
        elif 18.0 <= voltage <= 25.2:
            return 6  # 6S
        elif 21.0 <= voltage <= 29.4:
            return 7  # 7S
        elif 24.0 <= voltage <= 33.6:
            return 8  # 8S
        
        # LiFePO4 배터리 기준 (3.2V nominal per cell)
        elif 12.0 <= voltage <= 14.4:
            return 4  # 4S LiFePO4
        
        # 납축전지 기준
        elif 10.0 <= voltage <= 15.0:
            return 6  # 12V 납축전지 (6셀)
        elif 20.0 <= voltage <= 30.0:
            return 12  # 24V 납축전지 (12셀)
        
        return 1  # 기본값
    
    @staticmethod
    def calculate_discharge_curve(measurement: BatteryMeasurement, 
                                time_hours: float = 1.0) -> Dict[str, List[float]]:
        """방전 곡선 계산 (단순 모델)
        
        Args:
            measurement: 측정 데이터
            time_hours: 방전 시간 (시간)
            
        Returns:
            방전 곡선 데이터
        """
        result = BatteryCalculationEngine.calculate_internal_resistance(measurement)
        
        # 시간별 데이터 포인트 생성
        time_points = [i * time_hours / 100 for i in range(101)]
        voltages = []
        currents = []
        
        for t in time_points:
            # 단순 선형 방전 모델 (실제로는 더 복잡함)
            remaining_capacity = max(0, 1 - t / time_hours)
            
            # 전압 감소 (내부저항과 방전에 따른 감소)
            voltage = (measurement.no_load_voltage * remaining_capacity - 
                      result.load_current * result.internal_resistance)
            voltage = max(0, voltage)
            
            # 전류는 부하에 따라 결정
            current = voltage / measurement.load_resistance if voltage > 0 else 0
            
            voltages.append(voltage)
            currents.append(current)
        
        return {
            'time_hours': time_points,
            'voltage': voltages,
            'current': currents
        }

class BatteryDataAnalyzer:
    """배터리 데이터 분석 클래스"""
    
    @staticmethod
    def analyze_resistance_trend(results: List[CalculationResult]) -> Dict:
        """내부저항 변화 추세 분석
        
        Args:
            results: 계산 결과 리스트
            
        Returns:
            분석 결과
        """
        if len(results) < 2:
            return {'trend': 'insufficient_data', 'slope': 0, 'correlation': 0}
        
        resistances = [r.internal_resistance for r in results]
        
        # 선형 회귀를 통한 추세 분석
        n = len(resistances)
        x = list(range(n))
        
        # 평균 계산
        x_mean = sum(x) / n
        y_mean = sum(resistances) / n
        
        # 기울기 계산
        numerator = sum((x[i] - x_mean) * (resistances[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # 상관계수 계산
        y_var = sum((resistances[i] - y_mean) ** 2 for i in range(n))
        correlation = numerator / math.sqrt(denominator * y_var) if denominator * y_var > 0 else 0
        
        # 추세 판정
        if abs(slope) < 0.001:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'slope': slope,
            'correlation': correlation,
            'average_resistance': y_mean,
            'min_resistance': min(resistances),
            'max_resistance': max(resistances)
        }
    
    @staticmethod
    def calculate_statistics(results: List[CalculationResult]) -> Dict:
        """통계 계산
        
        Args:
            results: 계산 결과 리스트
            
        Returns:
            통계 결과
        """
        if not results:
            return {}
        
        resistances = [r.internal_resistance for r in results]
        efficiencies = [r.efficiency for r in results]
        currents = [r.load_current for r in results]
        
        def calculate_stats(data):
            n = len(data)
            mean = sum(data) / n
            variance = sum((x - mean) ** 2 for x in data) / n
            std_dev = math.sqrt(variance)
            return {
                'mean': mean,
                'std_dev': std_dev,
                'min': min(data),
                'max': max(data),
                'range': max(data) - min(data)
            }
        
        return {
            'resistance': calculate_stats(resistances),
            'efficiency': calculate_stats(efficiencies),
            'current': calculate_stats(currents),
            'count': len(results)
        } 