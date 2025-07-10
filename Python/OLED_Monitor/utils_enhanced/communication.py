# -*- coding: utf-8 -*-
"""
통신 관리자 - 시리얼 통신 및 데이터 송수신
"""

import serial
import serial.tools.list_ports
import threading
import time
import logging
from typing import Dict, Any, Optional, List, Callable
import queue
from queue import Queue, Empty
import re

from core.interfaces import CommunicationInterface
from core.constants import SERIAL_BAUDRATE, SERIAL_TIMEOUT, COMMANDS, RESPONSE_PATTERNS, SUPPORTED_BAUDRATES
from core.exceptions import SerialCommunicationError, TimeoutError

class SerialCommunicator(CommunicationInterface):
    """향상된 시리얼 통신 클래스"""
    
    def __init__(self, auto_reconnect: bool = True, reconnect_interval: float = 5.0):
        self.logger = logging.getLogger(__name__)
        self.serial_port = None
        self.is_connected_flag = False
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        
        # 통신 통계
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'commands_sent': 0,
            'responses_received': 0,
            'connection_attempts': 0,
            'connection_failures': 0,
            'last_activity': None
        }
        
        # 비동기 처리
        self.receive_queue = Queue()
        self.send_queue = Queue()
        self.receive_thread = None
        self.send_thread = None
        self.stop_threads = False
        
        # 콜백 함수들
        self.data_callbacks = {}
        self.event_callbacks = {}
        
    def connect(self, port: str, baudrate: int = SERIAL_BAUDRATE) -> bool:
        """장치 연결"""
        try:
            self.stats['connection_attempts'] += 1
            
            if self.is_connected_flag:
                self.disconnect()
            
            # 지원되는 통신속도 확인
            if baudrate not in SUPPORTED_BAUDRATES:
                self.logger.warning(f"지원되지 않는 통신속도: {baudrate}, 기본값 사용: {SERIAL_BAUDRATE}")
                baudrate = SERIAL_BAUDRATE
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=SERIAL_TIMEOUT,
                write_timeout=SERIAL_TIMEOUT
            )
            
            # 연결 확인
            if self.serial_port.is_open:
                self.is_connected_flag = True
                self.logger.info(f"시리얼 연결 성공: {port} @ {baudrate} bps")
                
                # 통신 스레드 시작
                self._start_communication_threads()
                
                # 연결 이벤트 콜백
                self._trigger_event_callback('connected', {'port': port, 'baudrate': baudrate})
                
                return True
            else:
                self.stats['connection_failures'] += 1
                return False
                
        except Exception as e:
            self.stats['connection_failures'] += 1
            self.logger.error(f"시리얼 연결 실패: {e}")
            raise SerialCommunicationError(f"연결 실패: {e}")
    
    def disconnect(self) -> bool:
        """장치 연결 해제"""
        try:
            self.is_connected_flag = False
            self._stop_communication_threads()
            
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.logger.info("시리얼 연결 해제")
                
                # 연결 해제 이벤트 콜백
                self._trigger_event_callback('disconnected', {})
                
            return True
            
        except Exception as e:
            self.logger.error(f"시리얼 연결 해제 실패: {e}")
            return False
    
    def send_command(self, command: bytes) -> bool:
        """명령 전송 - 직접 전송 방식"""
        if not self.is_connected_flag or not self.serial_port:
            self.logger.error("시리얼 포트가 연결되지 않음")
            return False
        
        try:
            # 명령어 로그 (바이트와 문자열 모두)
            try:
                cmd_str = command.decode('utf-8', errors='ignore')
                self.logger.info(f"명령 전송: '{cmd_str.strip()}' ({len(command)} bytes)")
            except:
                self.logger.info(f"명령 전송: {command} ({len(command)} bytes)")
            
            # 전송 전 포트 상태 확인
            if not self.serial_port.is_open:
                self.logger.error("시리얼 포트가 닫혀있음")
                return False
            
            # 직접 전송 (큐 사용하지 않음)
            bytes_written = self.serial_port.write(command)
            self.serial_port.flush()  # 즉시 전송 보장
            
            # 전송 결과 확인
            if bytes_written != len(command):
                self.logger.warning(f"명령 전송 불완전: {bytes_written}/{len(command)} bytes")
            else:
                self.logger.debug(f"명령 전송 완료: {bytes_written} bytes")
            
            self.stats['bytes_sent'] += len(command)
            self.stats['commands_sent'] += 1
            self.stats['last_activity'] = time.time()
            
            return True
            
        except Exception as e:
            self.logger.error(f"명령 전송 실패: {e}")
            return False
    
    def send_command_sync(self, command: bytes) -> bool:
        """동기 명령 전송"""
        if not self.is_connected_flag or not self.serial_port:
            return False
        
        try:
            self.serial_port.write(command)
            self.serial_port.flush()
            
            self.stats['bytes_sent'] += len(command)
            self.stats['commands_sent'] += 1
            self.stats['last_activity'] = time.time()
            
            self.logger.debug(f"명령 전송: {command}")
            return True
            
        except Exception as e:
            self.logger.error(f"동기 명령 전송 실패: {e}")
            return False
    
    def receive_data(self, timeout: float = SERIAL_TIMEOUT) -> Optional[bytes]:
        """데이터 수신"""
        try:
            data = self.receive_queue.get(timeout=timeout)
            return data
            
        except Empty:
            return None
        except Exception as e:
            self.logger.error(f"데이터 수신 실패: {e}")
            return None
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.is_connected_flag and self.serial_port and self.serial_port.is_open
    
    def _start_communication_threads(self):
        """통신 스레드 시작"""
        self.stop_threads = False
        
        # 수신 스레드
        self.receive_thread = threading.Thread(target=self._receive_worker, daemon=True)
        self.receive_thread.start()
        
        # 송신 스레드
        self.send_thread = threading.Thread(target=self._send_worker, daemon=True)
        self.send_thread.start()
        
        self.logger.debug("통신 스레드 시작")
    
    def _stop_communication_threads(self):
        """통신 스레드 중지"""
        self.stop_threads = True
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)
        
        if self.send_thread and self.send_thread.is_alive():
            self.send_thread.join(timeout=2)
        
        self.logger.debug("통신 스레드 중지")
    
    def _receive_worker(self):
        """수신 작업자 스레드"""
        while not self.stop_threads and self.is_connected_flag:
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    
                    if data:
                        self.stats['bytes_received'] += len(data)
                        self.stats['responses_received'] += 1
                        self.stats['last_activity'] = time.time()
                        
                        # 디버깅 로그 추가
                        try:
                            data_str = data.decode('utf-8', errors='ignore')
                            self.logger.debug(f"수신 데이터: {data_str[:100]}...")
                        except:
                            self.logger.debug(f"수신 데이터 (바이트): {data[:50]}...")
                        
                        # 큐에 데이터 추가
                        self.receive_queue.put(data)
                        
                        # 데이터 콜백 호출
                        self._trigger_data_callbacks(data)
                        
                        self.logger.debug(f"데이터 수신: {len(data)} bytes")
                
                time.sleep(0.01)  # CPU 사용량 제한
                
            except Exception as e:
                self.logger.error(f"수신 스레드 오류: {e}")
                if self.auto_reconnect:
                    self._attempt_reconnect()
                break
    
    def _send_worker(self):
        """송신 작업자 스레드"""
        while not self.stop_threads and self.is_connected_flag:
            try:
                command = self.send_queue.get(timeout=1)
                if command and self.serial_port:
                    self.serial_port.write(command)
                    self.serial_port.flush()
                    
                    self.stats['bytes_sent'] += len(command)
                    self.stats['commands_sent'] += 1
                    self.stats['last_activity'] = time.time()
                    
                    self.logger.debug(f"명령 전송: {command}")
                    
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"송신 스레드 오류: {e}")
                if self.auto_reconnect:
                    self._attempt_reconnect()
                break
    
    def _attempt_reconnect(self):
        """재연결 시도"""
        if not self.auto_reconnect:
            return
        
        self.logger.info("재연결 시도 중...")
        
        # 현재 연결 정리
        old_port = self.serial_port.port if self.serial_port else None
        old_baudrate = self.serial_port.baudrate if self.serial_port else SERIAL_BAUDRATE
        
        self.disconnect()
        
        # 재연결 시도
        time.sleep(self.reconnect_interval)
        
        try:
            if old_port:
                self.connect(old_port, old_baudrate)
        except Exception as e:
            self.logger.error(f"재연결 실패: {e}")
    
    def register_data_callback(self, callback_id: str, callback: Callable[[bytes], None]):
        """데이터 콜백 등록"""
        self.data_callbacks[callback_id] = callback
    
    def register_event_callback(self, callback_id: str, callback: Callable[[str, Dict], None]):
        """이벤트 콜백 등록"""
        self.event_callbacks[callback_id] = callback
    
    def _trigger_data_callbacks(self, data: bytes):
        """데이터 콜백 호출"""
        for callback_id, callback in self.data_callbacks.items():
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"데이터 콜백 오류 ({callback_id}): {e}")
    
    def _trigger_event_callback(self, event_type: str, event_data: Dict):
        """이벤트 콜백 호출"""
        for callback_id, callback in self.event_callbacks.items():
            try:
                callback(event_type, event_data)
            except Exception as e:
                self.logger.error(f"이벤트 콜백 오류 ({callback_id}): {e}")
    
    @staticmethod
    def get_available_ports() -> List[Dict[str, str]]:
        """사용 가능한 포트 목록"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
    
    @staticmethod
    def find_device_port(description_keywords: List[str]) -> Optional[str]:
        """장치 포트 자동 찾기"""
        for port in serial.tools.list_ports.comports():
            for keyword in description_keywords:
                if keyword.lower() in port.description.lower():
                    return port.device
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """통신 통계 정보"""
        stats = self.stats.copy()
        stats['is_connected'] = self.is_connected()
        stats['port_info'] = {
            'device': self.serial_port.port if self.serial_port else None,
            'baudrate': self.serial_port.baudrate if self.serial_port else None,
            'timeout': self.serial_port.timeout if self.serial_port else None,
        }
        stats['queue_sizes'] = {
            'receive': self.receive_queue.qsize(),
            'send': self.send_queue.qsize()
        }
        return stats
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'commands_sent': 0,
            'responses_received': 0,
            'connection_attempts': 0,
            'connection_failures': 0,
            'last_activity': None
        }
    
    def clear_buffers(self):
        """버퍼 비우기"""
        if self.serial_port:
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
        
        # 큐 비우기
        while not self.receive_queue.empty():
            try:
                self.receive_queue.get_nowait()
            except Empty:
                break
        
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except Empty:
                break
    
    def close(self):
        """통신 종료"""
        self.disconnect()
        self.data_callbacks.clear()
        self.event_callbacks.clear() 