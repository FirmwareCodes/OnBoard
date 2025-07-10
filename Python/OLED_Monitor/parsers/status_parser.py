# -*- coding: utf-8 -*-
"""
OLED 상태 데이터 파서
"""

import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import random
import time

from core.interfaces import DataParserInterface
from core.constants import STATUS_VALUES, BATTERY_MIN, BATTERY_MAX, BATTERY_ADC_MIN, BATTERY_ADC_MAX
from core.exceptions import StatusDataError, ValidationError

class StatusDataParser(DataParserInterface):
    """상태 데이터 파싱 최적화 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._compiled_patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """정규식 패턴 미리 컴파일"""
        return {
            'status_block': re.compile(rb'STATUS:(.*?)(?=\n|$)', re.DOTALL),
            'battery_percent': re.compile(rb'BAT:(\d+(?:\.\d+)?)V?%?', re.IGNORECASE),
            'battery_adc': re.compile(rb'BAT_ADC:(\d+)', re.IGNORECASE),
            'timer': re.compile(rb'TIMER:(\d{1,2}):(\d{2})', re.IGNORECASE),
            'status': re.compile(rb'STATUS:(\w+)', re.IGNORECASE),
            'l1_connection': re.compile(rb'L1:([01])', re.IGNORECASE),
            'l2_connection': re.compile(rb'L2:([01])', re.IGNORECASE),
            'key_value': re.compile(rb'(\w+):([^,\r\n]+)', re.IGNORECASE),
        }
    
    def parse_status_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """상태 데이터 파싱 - 펌웨어 호환 버전"""
        try:
            # 파싱 시간 제한 (무한루프 방지)
            start_time = time.time()
            max_parse_time = 1.5  # 1.5초 파싱 시간 제한
            
            # 원본 RAW 데이터 보존
            raw_data = data
            
            # 데이터 크기 검증 (과도한 데이터 방지)
            if len(data) > 2048:  # 2KB 제한
                data = data[:2048]  # 잘라내기
            
            try:
                data_str = data.decode('utf-8', errors='ignore').strip()
            except UnicodeDecodeError:
                data_str = str(data, errors='replace').strip()
            
            # 파싱 시간 체크
            if time.time() - start_time > max_parse_time:
                return None
            
            # STATUS: 형식인지 확인
            if not data_str.startswith('STATUS:'):
                return None
            
            # STATUS: 제거
            status_part = data_str[7:]  # "STATUS:" 제거
            
            # 기본 상태 정보 초기화
            result = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'firmware',
                'raw_data': raw_data,  # 원본 RAW 데이터 추가
                'raw_string': data_str  # 문자열 형태도 추가
            }
            
            # 안전한 파싱 처리
            return self._parse_status_items_safe(status_part, result, start_time, max_parse_time)
            
        except Exception as e:
            self.logger.error(f"상태 데이터 파싱 실패: {e}")
            return self._generate_safe_status()
    
    def _parse_status_items_safe(self, status_part: str, result: Dict[str, Any], start_time: float, max_parse_time: float) -> Dict[str, Any]:
        """안전한 상태 아이템 파싱"""
        try:
            # 안전한 분할 처리
            items = status_part.split(',')
            
            # 최대 아이템 수 제한 (무한루프 방지)
            if len(items) > 15:
                items = items[:15]  # 최대 15개로 제한
            
            parse_count = 0
            max_parse_count = 30  # 최대 파싱 횟수 제한
            
            for item in items:
                parse_count += 1
                if parse_count > max_parse_count:
                    break
                
                # 파싱 시간 체크
                if time.time() - start_time > max_parse_time:
                    break
                
                item = item.strip()
                if not item or ':' not in item:
                    continue
                
                try:
                    # 안전한 키-값 분할
                    parts = item.split(':', 1)
                    if len(parts) != 2:
                        continue
                        
                    key, value = parts
                    key = key.strip()
                    value = value.strip()
                    
                    # 키와 값 길이 검증
                    if len(key) > 20 or len(value) > 50:
                        continue
                    
                    # 각 필드별 안전한 파싱
                    self._parse_individual_field(key, value, result)
                    
                except Exception as item_error:
                    # 개별 아이템 파싱 오류시 계속 진행
                    continue
            
            # 필수 필드 기본값 설정
            self._fill_missing_fields(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"상태 아이템 파싱 실패: {e}")
            return self._generate_safe_status()
    
    def _parse_individual_field(self, key: str, value: str, result: Dict[str, Any]):
        """개별 필드 파싱 - 원본 로직 적용"""
        if key == 'BAT':
            # 배터리 파싱 (원본 로직: RAW 값을 /100해서 전압으로)
            try:
                battery_str = value.replace('V', '').replace('%', '').strip()
                if battery_str.isdigit():
                    battery_raw = int(battery_str)
                    # 원본 로직: /100해서 전압으로 변환
                    battery_voltage = battery_raw / 100.0
                    result['battery'] = battery_voltage
                else:
                    result['battery'] = 0
            except (ValueError, TypeError):
                result['battery'] = 0
                
        elif key == 'TIMER':
            # 타이머 파싱 (형식 검증)
            if len(value) <= 8 and ':' in value:
                result['timer'] = value
            else:
                result['timer'] = '00:00'
                
        elif key == 'STATUS':
            # 상태 파싱 (길이 제한)
            if len(value) <= 15:
                result['status'] = value
            else:
                result['status'] = 'UNKNOWN'
                
        elif key == 'L1':
            # L1 연결 상태 (안전한 변환)
            result['l1_connected'] = (value == '1')
            
        elif key == 'L2':
            # L2 연결 상태 (안전한 변환)
            result['l2_connected'] = (value == '1')
            
        elif key == 'BAT_ADC':
            # BAT ADC 파싱 (원본 로직: ADC 값 그대로 표시)
            try:
                # 숫자 문자열 검증
                if value.isdigit() and len(value) <= 5:  # 최대 5자리
                    adc_val = int(value)
                    # 12-bit ADC 범위 검증 (0-4095)
                    if 0 <= adc_val <= 4095:
                        result['bat_adc'] = adc_val
                    else:
                        # 범위 벗어나면 보정
                        result['bat_adc'] = max(0, min(4095, adc_val))
                else:
                    # 잘못된 형식
                    result['bat_adc'] = 0
            except (ValueError, TypeError, OverflowError):
                # 모든 변환 오류 처리
                result['bat_adc'] = 0
    
    def _fill_missing_fields(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """누락된 필드 채우기"""
        defaults = {
            'battery': 0,
            'bat_adc': 0,
            'timer': '00:00',
            'status': 'UNKNOWN',
            'l1_connected': False,
            'l2_connected': False,
        }
        
        for key, default_value in defaults.items():
            if key not in status_data:
                status_data[key] = default_value
        
        return status_data
    
    def _try_fallback_parsing(self, data: bytes) -> Optional[Dict[str, Any]]:
        """대체 파싱 방법들"""
        parsers = [
            self._parse_key_value_format,
            self._parse_simple_format,
            self._parse_legacy_format,
        ]
        
        for parser in parsers:
            try:
                result = parser(data)
                if result:
                    self.logger.info(f"대체 파싱 성공: {parser.__name__}")
                    return result
            except Exception as e:
                self.logger.debug(f"대체 파싱 실패 {parser.__name__}: {e}")
                continue
        
        return self._generate_safe_status()
    
    def _parse_key_value_format(self, data: bytes) -> Optional[Dict[str, Any]]:
        """키-값 형식 파싱"""
        try:
            result = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'key_value_format',
                'raw_data': data,
                'raw_string': data.decode('ascii', errors='ignore').strip()
            }
            
            # 모든 키-값 쌍 추출
            kv_matches = self._compiled_patterns['key_value'].findall(data)
            
            for key_bytes, value_bytes in kv_matches:
                key = key_bytes.decode('ascii', errors='ignore').upper()
                value = value_bytes.decode('ascii', errors='ignore').strip()
                
                if key == 'BAT' and value.endswith('%'):
                    result['battery'] = int(value[:-1])
                elif key == 'BAT_ADC':
                    result['bat_adc'] = int(value)
                elif key == 'TIMER':
                    result['timer'] = value
                elif key == 'STATUS':
                    result['status'] = value.upper()
                elif key == 'L1':
                    result['l1_connected'] = value == '1'
                elif key == 'L2':
                    result['l2_connected'] = value == '1'
            
            return self._fill_missing_fields(result) if result else None
            
        except Exception as e:
            self.logger.debug(f"키-값 형식 파싱 실패: {e}")
            return None
    
    def _parse_simple_format(self, data: bytes) -> Optional[Dict[str, Any]]:
        """단순 형식 파싱"""
        try:
            data_str = data.decode('ascii', errors='ignore')
            
            # 숫자 패턴들 찾기
            numbers = re.findall(r'\d+', data_str)
            if not numbers:
                return None
            
            result = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'simple_format',
                'raw_data': data,
                'raw_string': data_str.strip()
            }
            
            # 첫 번째 숫자를 배터리로 가정
            if numbers:
                first_num = int(numbers[0])
                if BATTERY_MIN <= first_num <= BATTERY_MAX:
                    result['battery'] = first_num/100
                elif BATTERY_ADC_MIN <= first_num <= BATTERY_ADC_MAX:
                    result['bat_adc'] = first_num
            
            return self._fill_missing_fields(result)
            
        except Exception as e:
            self.logger.debug(f"단순 형식 파싱 실패: {e}")
            return None
    
    def _parse_legacy_format(self, data: bytes) -> Optional[Dict[str, Any]]:
        """레거시 형식 파싱"""
        try:
            # 콤마나 세미콜론으로 구분된 데이터
            data_str = data.decode('ascii', errors='ignore')
            parts = re.split(r'[,;]', data_str)
            
            result = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'legacy_format',
                'raw_data': data,
                'raw_string': data_str.strip()
            }
            
            for part in parts:
                part = part.strip()
                if ':' in part:
                    key, value = part.split(':', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    
                    if key == 'BAT' and value.endswith('V'):
                        result['battery'] = int(value[:-1]) / 100
                    elif key == 'TIMER':
                        result['timer'] = value
                    elif key == 'STATUS':
                        result['status'] = value.upper()
            
            return self._fill_missing_fields(result)
            
        except Exception as e:
            self.logger.debug(f"레거시 형식 파싱 실패: {e}")
            return None
    
    def _generate_safe_status(self) -> Dict[str, Any]:
        """안전한 기본 상태 생성"""
        return {
            'battery': random.randint(18, 25),
            'bat_adc': random.randint(0, 4095),
            'timer': f"{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            'status': 'STANDBY',
            'l1_connected': False,
            'l2_connected': False,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': 'safe_fallback',
            'raw_data': b'SAFE_FALLBACK_DATA',
            'raw_string': 'SAFE_FALLBACK_DATA'
        }
    
    def parse_screen_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """화면 데이터 파싱 (인터페이스 구현)"""
        # 상태 파서에서는 화면 데이터 파싱 안함
        return None
    
    def validate_data(self, data: Any) -> bool:
        """상태 데이터 유효성 검증"""
        if not isinstance(data, dict):
            return False
        
        required_fields = ['battery', 'timer', 'status']
        if not all(field in data for field in required_fields):
            return False
        
        # 배터리 범위 검증
        if not (BATTERY_MIN <= data['battery'] <= BATTERY_MAX):
            return False
        
        # 상태 값 검증
        if data['status'] not in STATUS_VALUES:
            return False
        
        # 타이머 형식 검증
        if not re.match(r'^\d{2}:\d{2}$', data['timer']):
            return False
        
        return True
    
    def create_test_status(self) -> Dict[str, Any]:
        """테스트용 상태 데이터 생성"""
        statuses = list(STATUS_VALUES.keys())
        
        return {
            'battery': random.randint(18, 25),
            'bat_adc': random.randint(0, 4095),
            'timer': f"{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            'status': random.choice(statuses),
            'l1_connected': random.choice([True, False]),
            'l2_connected': random.choice([True, False]),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': 'test_data',
            'raw_data': b'TEST_DATA',
            'raw_string': 'TEST_DATA'
        } 