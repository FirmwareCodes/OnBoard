# -*- coding: utf-8 -*-
"""
OLED Monitor 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

class DataParserInterface(ABC):
    """데이터 파서 인터페이스"""
    
    @abstractmethod
    def parse_screen_data(self, data: bytes) -> Optional[np.ndarray]:
        """화면 데이터 파싱"""
        pass
    
    @abstractmethod
    def parse_status_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """상태 데이터 파싱"""
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """데이터 유효성 검증"""
        pass

class CommunicationInterface(ABC):
    """통신 인터페이스"""
    
    @abstractmethod
    def connect(self, port: str, baudrate: int) -> bool:
        """장치 연결"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """장치 연결 해제"""
        pass
    
    @abstractmethod
    def send_command(self, command: bytes) -> bool:
        """명령 전송"""
        pass
    
    @abstractmethod
    def receive_data(self, timeout: float) -> Optional[bytes]:
        """데이터 수신"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        pass

class LoggerInterface(ABC):
    """로거 인터페이스"""
    
    @abstractmethod
    def log(self, level: str, message: str, category: str = "GENERAL"):
        """로그 기록"""
        pass
    
    @abstractmethod
    def log_status(self, status_data: Dict[str, Any]):
        """상태 로그 기록"""
        pass
    
    @abstractmethod
    def log_event(self, event_type: str, message: str, details: Any = None):
        """이벤트 로그 기록"""
        pass

class DisplayInterface(ABC):
    """디스플레이 인터페이스"""
    
    @abstractmethod
    def update_screen(self, screen_data: np.ndarray):
        """화면 업데이트"""
        pass
    
    @abstractmethod
    def update_status(self, status_data: Dict[str, Any]):
        """상태 업데이트"""
        pass
    
    @abstractmethod
    def set_scale(self, scale: int):
        """스케일 설정"""
        pass

class ConfigInterface(ABC):
    """설정 인터페이스"""
    
    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """설정 로드"""
        pass
    
    @abstractmethod
    def save_config(self, config: Dict[str, Any]):
        """설정 저장"""
        pass
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any):
        """설정 값 설정"""
        pass

class PerformanceMonitorInterface(ABC):
    """성능 모니터 인터페이스"""
    
    @abstractmethod
    def record_timing(self, operation: str, duration: float):
        """타이밍 기록"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 가져오기"""
        pass
    
    @abstractmethod
    def reset(self):
        """통계 초기화"""
        pass 