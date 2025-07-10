# -*- coding: utf-8 -*-
"""
통합 데이터 파서 - 화면과 상태 데이터를 모두 처리
"""

import logging
from typing import Optional, Dict, Any, Tuple
import numpy as np
import time
import signal

from parsers.screen_parser import ScreenDataParser
from parsers.status_parser import StatusDataParser
from core.interfaces import DataParserInterface
from core.constants import PARSING_TIMEOUT
from core.exceptions import ParsingError, TimeoutError

class UnifiedDataParser(DataParserInterface):
    """통합 데이터 파서 - 모든 파싱 기능을 하나로 통합"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.screen_parser = ScreenDataParser()
        self.status_parser = StatusDataParser()
        self.parsing_stats = {
            'screen_success': 0,
            'screen_failure': 0,
            'status_success': 0,
            'status_failure': 0,
            'total_parsing_time': 0.0,
            'average_parsing_time': 0.0
        }
        
    def parse_screen_data(self, data: bytes) -> Optional[np.ndarray]:
        """화면 데이터 파싱"""
        try:
            self.logger.debug(f"화면 데이터 파싱 시작: {len(data)} bytes")
            
            # 화면 파서 사용
            screen_data = self.screen_parser.parse(data)
            
            if screen_data is not None:
                self.parsing_stats['screen_success'] += 1
                self.logger.debug(f"화면 파싱 성공: {screen_data.shape}")
                return screen_data
            else:
                self.parsing_stats['screen_failure'] += 1
                self.logger.warning("화면 파싱 실패")
                return None
                
        except Exception as e:
            self.parsing_stats['screen_failure'] += 1
            self.logger.error(f"화면 데이터 파싱 오류: {e}")
            return None
    
    def parse_status_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """상태 데이터 파싱"""
        start_time = time.time()
        try:
            result = self._safe_parse_with_timeout(
                self.status_parser.parse_status_data, 
                data, 
                "상태 데이터 파싱"
            )
            
            if result is not None:
                self.parsing_stats['status_success'] += 1
                return result
            else:
                self.parsing_stats['status_failure'] += 1
                return self.status_parser._generate_safe_status()
                
        except Exception as e:
            self.parsing_stats['status_failure'] += 1
            self.logger.error(f"상태 데이터 파싱 실패: {e}")
            return self.status_parser._generate_safe_status()
        finally:
            parsing_time = time.time() - start_time
            self._update_parsing_stats(parsing_time)
    
    def parse_combined_data(self, data: bytes) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """화면과 상태 데이터를 동시에 파싱"""
        screen_data = None
        status_data = None
        
        try:
            # 데이터 로깅 (디버깅용)
            try:
                data_str = data.decode('utf-8', errors='ignore')
                self.logger.debug(f"파싱 대상 데이터: {data_str[:200]}...")
            except:
                self.logger.debug(f"파싱 대상 데이터 (바이트): {data[:100]}...")
            
            # 화면 데이터 파싱 시도
            if b'SCREEN_START' in data:
                self.logger.debug("화면 데이터 감지됨")
                screen_data = self.parse_screen_data(data)
                if screen_data is not None:
                    self.logger.debug(f"화면 데이터 파싱 성공: {screen_data.shape}")
                else:
                    self.logger.debug("화면 데이터 파싱 실패")
            
            # 상태 데이터 파싱 시도
            if b'STATUS:' in data:
                self.logger.debug("상태 데이터 감지됨")
                status_data = self.parse_status_data(data)
                if status_data is not None:
                    self.logger.debug(f"상태 데이터 파싱 성공: {status_data.get('status', 'UNKNOWN')}")
                else:
                    self.logger.debug("상태 데이터 파싱 실패")
            
            # 데이터 타입 자동 감지
            if screen_data is None and status_data is None:
                self.logger.debug("자동 감지 모드 시작")
                screen_data, status_data = self._auto_detect_and_parse(data)
            
            return screen_data, status_data
            
        except Exception as e:
            self.logger.error(f"통합 데이터 파싱 실패: {e}")
            return None, self.status_parser._generate_safe_status()
    
    def _auto_detect_and_parse(self, data: bytes) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """데이터 타입 자동 감지 및 파싱"""
        screen_data = None
        status_data = None
        
        # 헥스 데이터 패턴 확인 (화면 데이터 가능성)
        hex_ratio = self._calculate_hex_ratio(data)
        if hex_ratio > 0.5:  # 50% 이상이 헥스 문자
            screen_data = self.parse_screen_data(data)
        
        # 키-값 패턴 확인 (상태 데이터 가능성)
        if b':' in data or b'=' in data:
            status_data = self.parse_status_data(data)
        
        # 숫자 패턴 확인
        if status_data is None:
            import re
            numbers = re.findall(rb'\d+', data)
            if numbers:
                status_data = self.parse_status_data(data)
        
        return screen_data, status_data
    
    def _calculate_hex_ratio(self, data: bytes) -> float:
        """헥스 문자 비율 계산"""
        try:
            text = data.decode('ascii', errors='ignore')
            if not text:
                return 0.0
            
            hex_chars = sum(1 for c in text if c in '0123456789ABCDEFabcdef')
            return hex_chars / len(text)
        except:
            return 0.0
    
    def _safe_parse_with_timeout(self, parse_func, data: bytes, operation_name: str):
        """타임아웃이 있는 안전한 파싱"""
        result = None
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"{operation_name} 타임아웃")
        
        try:
            # Windows에서는 signal.alarm이 지원되지 않음
            if hasattr(signal, 'alarm'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(PARSING_TIMEOUT)
            
            result = parse_func(data)
            
        except TimeoutError:
            self.logger.warning(f"{operation_name} 타임아웃 발생")
            result = None
        except Exception as e:
            self.logger.error(f"{operation_name} 중 오류 발생: {e}")
            result = None
        finally:
            try:
                if hasattr(signal, 'alarm'):
                    signal.alarm(0)  # 타임아웃 해제
            except:
                pass
        
        return result
    
    def _update_parsing_stats(self, parsing_time: float):
        """파싱 통계 업데이트"""
        self.parsing_stats['total_parsing_time'] += parsing_time
        total_operations = (
            self.parsing_stats['screen_success'] + 
            self.parsing_stats['screen_failure'] + 
            self.parsing_stats['status_success'] + 
            self.parsing_stats['status_failure']
        )
        
        if total_operations > 0:
            self.parsing_stats['average_parsing_time'] = (
                self.parsing_stats['total_parsing_time'] / total_operations
            )
    
    def validate_data(self, data: Any) -> bool:
        """데이터 유효성 검증"""
        if isinstance(data, np.ndarray):
            return self.screen_parser.validate_data(data)
        elif isinstance(data, dict):
            return self.status_parser.validate_data(data)
        else:
            return False
    
    def get_parsing_stats(self) -> Dict[str, Any]:
        """파싱 통계 정보 반환"""
        stats = self.parsing_stats.copy()
        
        # 성공률 계산
        total_screen = stats['screen_success'] + stats['screen_failure']
        total_status = stats['status_success'] + stats['status_failure']
        
        if total_screen > 0:
            stats['screen_success_rate'] = stats['screen_success'] / total_screen
        else:
            stats['screen_success_rate'] = 0.0
        
        if total_status > 0:
            stats['status_success_rate'] = stats['status_success'] / total_status
        else:
            stats['status_success_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """통계 초기화"""
        self.parsing_stats = {
            'screen_success': 0,
            'screen_failure': 0,
            'status_success': 0,
            'status_failure': 0,
            'total_parsing_time': 0.0,
            'average_parsing_time': 0.0
        }
    
    def create_test_data(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """테스트용 데이터 생성"""
        test_screen = self.screen_parser.create_test_screen("checkerboard")
        test_status = self.status_parser.create_test_status()
        return test_screen, test_status 