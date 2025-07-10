# -*- coding: utf-8 -*-
"""
간단한 로거 - 필요한 로그만 기록
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any

from core.interfaces import LoggerInterface
from core.constants import DEFAULT_LOG_DIR

class EnhancedLogger(LoggerInterface):
    """간소화된 로거 클래스"""
    
    def __init__(self, name: str = "OLEDMonitor", log_dir: str = DEFAULT_LOG_DIR):
        self.name = name
        self.log_dir = log_dir
        
        self._setup_directories()
        self._setup_logger()
        
    def _setup_directories(self):
        """로그 디렉토리만 생성"""
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _setup_logger(self):
        """로거 설정 - 간단한 구조"""
        self.logger = logging.getLogger(f"{self.name}")
        
        # 이미 핸들러가 있으면 제거 (중복 방지)
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        self.logger.setLevel(logging.INFO)  # INFO 레벨 이상만 기록
        
        # 파일 핸들러만 설정
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(self.log_dir, f"{self.name}_{today}.log")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'  # 시간만 표시
        ))
        
        self.logger.addHandler(file_handler)
        
        # 상태 로그용 별도 파일
        self.status_log_file = os.path.join(self.log_dir, f"status_{today}.log")
        
    def log_status(self, status_data: Dict[str, Any]):
        """상태 로그 기록 - 원본 방식"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # 간단한 형태로 상태 기록
            battery = status_data.get('battery', 0)
            timer = status_data.get('timer', '00:00')
            status = status_data.get('status', 'UNKNOWN')
            
            log_line = f"{timestamp} - BAT:{battery:.1f}V TIMER:{timer} STATUS:{status}\n"
            
            with open(self.status_log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
                
        except Exception as e:
            self.error(f"상태 로그 기록 실패: {e}")
    
    def info(self, message: str):
        """정보 로그"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """경고 로그"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """오류 로그"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """디버그 로그 - 기록하지 않음"""
        pass  # 디버그 로그는 무시
    
    def critical(self, message: str):
        """치명적 오류 로그"""
        self.logger.critical(message)
    
    def close(self):
        """로거 종료"""
        # 핸들러 정리
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler) 