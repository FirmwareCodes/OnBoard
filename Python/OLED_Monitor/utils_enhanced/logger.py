# -*- coding: utf-8 -*-
"""
향상된 로거 - 구조화된 로깅과 성능 모니터링
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading
import time
import queue
from queue import Queue, Empty

from core.interfaces import LoggerInterface
from core.constants import DEFAULT_LOG_DIR, LOG_LEVELS

class EnhancedLogger(LoggerInterface):
    """향상된 로거 클래스 - 비동기 로깅 지원"""
    
    def __init__(self, name: str = "OLEDMonitor", log_dir: str = DEFAULT_LOG_DIR):
        self.name = name
        self.log_dir = log_dir
        self.log_queue = Queue()
        self.log_thread = None
        self.stop_logging = False
        
        self._setup_directories()
        self._setup_loggers()
        self._start_log_thread()
        
    def _setup_directories(self):
        """로그 디렉토리 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _setup_loggers(self):
        """로거 설정"""
        # 메인 로거
        self.main_logger = logging.getLogger(f"{self.name}.main")
        self.main_logger.setLevel(logging.DEBUG)
        
        # 상태 로거
        self.status_logger = logging.getLogger(f"{self.name}.status")
        self.status_logger.setLevel(logging.INFO)
        
        # 이벤트 로거
        self.event_logger = logging.getLogger(f"{self.name}.event")
        self.event_logger.setLevel(logging.INFO)
        
        # 핸들러 설정
        self._setup_handlers()
        
    def _setup_handlers(self):
        """핸들러 설정"""
        # 파일 핸들러
        today = datetime.now().strftime('%Y%m%d')
        
        # 메인 로그
        main_handler = logging.FileHandler(
            os.path.join(self.log_dir, f"{self.name}_{today}.log"),
            encoding='utf-8'
        )
        main_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.main_logger.addHandler(main_handler)
        
        # 상태 로그
        status_handler = logging.FileHandler(
            os.path.join(self.log_dir, f"status_{today}.log"),
            encoding='utf-8'
        )
        status_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        self.status_logger.addHandler(status_handler)
        
        # 이벤트 로그
        event_handler = logging.FileHandler(
            os.path.join(self.log_dir, f"events_{today}.log"),
            encoding='utf-8'
        )
        event_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.event_logger.addHandler(event_handler)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.main_logger.addHandler(console_handler)
        
    def _start_log_thread(self):
        """로그 스레드 시작"""
        self.log_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.log_thread.start()
        
    def _log_worker(self):
        """로그 작업자 스레드"""
        while not self.stop_logging:
            try:
                log_item = self.log_queue.get(timeout=1)
                if log_item is None:
                    break
                    
                logger_name, level, message, category = log_item
                logger = getattr(self, f"{logger_name}_logger")
                
                log_level = getattr(logging, level.upper())
                if category:
                    message = f"[{category}] {message}"
                    
                logger.log(log_level, message)
                
            except Empty:
                continue
            except Exception as e:
                print(f"로그 스레드 오류: {e}")
                
    def log(self, level: str, message: str, category: str = "GENERAL"):
        """로그 기록"""
        if not self.stop_logging:
            self.log_queue.put(("main", level, message, category))
    
    def log_status(self, status_data: Dict[str, Any]):
        """상태 로그 기록"""
        try:
            # JSON 형태로 상태 데이터 기록
            status_json = json.dumps(status_data, ensure_ascii=False, default=str)
            if not self.stop_logging:
                self.log_queue.put(("status", "INFO", status_json, None))
        except Exception as e:
            self.log("ERROR", f"상태 로그 기록 실패: {e}")
    
    def log_event(self, event_type: str, message: str, details: Any = None):
        """이벤트 로그 기록"""
        try:
            event_data = {
                'type': event_type,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'details': details
            }
            event_json = json.dumps(event_data, ensure_ascii=False, default=str)
            if not self.stop_logging:
                self.log_queue.put(("event", "INFO", event_json, None))
        except Exception as e:
            self.log("ERROR", f"이벤트 로그 기록 실패: {e}")
    
    def info(self, message: str, category: str = "GENERAL"):
        """정보 로그"""
        self.log("INFO", message, category)
    
    def warning(self, message: str, category: str = "GENERAL"):
        """경고 로그"""
        self.log("WARNING", message, category)
    
    def error(self, message: str, category: str = "GENERAL"):
        """오류 로그"""
        self.log("ERROR", message, category)
    
    def debug(self, message: str, category: str = "GENERAL"):
        """디버그 로그"""
        self.log("DEBUG", message, category)
    
    def critical(self, message: str, category: str = "GENERAL"):
        """치명적 오류 로그"""
        self.log("CRITICAL", message, category)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """로그 통계 정보"""
        return {
            'queue_size': self.log_queue.qsize(),
            'thread_alive': self.log_thread.is_alive() if self.log_thread else False,
            'log_dir': self.log_dir,
            'loggers': {
                'main': self.main_logger.name,
                'status': self.status_logger.name,
                'event': self.event_logger.name
            }
        }
    
    def flush_logs(self):
        """로그 버퍼 비우기"""
        try:
            # 큐가 비워질 때까지 대기
            while not self.log_queue.empty():
                time.sleep(0.1)
        except Exception as e:
            print(f"로그 플러시 오류: {e}")
    
    def close(self):
        """로거 종료"""
        self.stop_logging = True
        if self.log_thread and self.log_thread.is_alive():
            self.log_queue.put(None)  # 종료 신호
            self.log_thread.join(timeout=5)
        
        # 핸들러 정리
        for logger in [self.main_logger, self.status_logger, self.event_logger]:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler) 