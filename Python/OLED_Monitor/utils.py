#!/usr/bin/env python3
"""
Utility Functions for OnBoard OLED Monitor
공통으로 사용되는 유틸리티 함수들

Author: OnBoard LED Timer Project
Date: 2024-01-01
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
import serial.tools.list_ports
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class StatusLogger:
    """상태 로그 전용 클래스 - RAW 데이터 기록 지원"""
    
    def __init__(self, log_dir: str = "LOG"):
        self.log_dir = log_dir
        self.ensure_log_directory()
        self.status_log_file = None
        self.raw_log_file = None  # RAW 데이터 전용 로그 파일
        self.log_lock = threading.Lock()
        self.setup_daily_log()
        
    def ensure_log_directory(self):
        """LOG 디렉토리 생성"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
    
    def setup_daily_log(self):
        """일일 상태 로그 파일 설정"""
        today = datetime.now().strftime("%Y%m%d")
        self.status_log_file = os.path.join(self.log_dir, f"status_log_{today}.txt")
        self.raw_log_file = os.path.join(self.log_dir, f"raw_data_log_{today}.txt")
        
        # 새 파일인 경우에만 헤더 작성
        if not os.path.exists(self.status_log_file):
            self.write_header()
            
        if not os.path.exists(self.raw_log_file):
            self.write_raw_header()
    
    def write_header(self):
        """상태 로그 파일 헤더 작성"""
        try:
            with self.log_lock:
                with open(self.status_log_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 140 + "\n")
                    f.write(f"OnBoard OLED Monitor 상태 로그 - {datetime.now().strftime('%Y년 %m월 %d일')}\n")
                    f.write("=" * 140 + "\n")
                    f.write("시간\t\t\t배터리\t타이머\t\t상태\t\tL1\tL2\tBAT_ADC\t비고\t\t\tRAW 데이터\n")
                    f.write("-" * 140 + "\n")
        except Exception as e:
            print(f"상태 로그 헤더 작성 실패: {e}")
    
    def write_raw_header(self):
        """RAW 데이터 로그 파일 헤더 작성"""
        try:
            with self.log_lock:
                with open(self.raw_log_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 100 + "\n")
                    f.write(f"OnBoard OLED Monitor RAW 데이터 로그 - {datetime.now().strftime('%Y년 %m월 %d일')}\n")
                    f.write("=" * 100 + "\n")
                    f.write("시간\t\t\t데이터 타입\t\t길이\tRAW 데이터 (HEX)\n")
                    f.write("-" * 100 + "\n")
        except Exception as e:
            print(f"RAW 로그 헤더 작성 실패: {e}")
    
    def log_status(self, status_data: Dict):
        """상태 데이터 로그 기록 - RAW 데이터 포함"""
        if not self.status_log_file:
            return
            
        try:
            with self.log_lock:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                battery = status_data.get('battery', 'N/A')
                timer = status_data.get('timer', 'N/A')
                status = status_data.get('status', 'N/A')
                l1_connected = '연결' if status_data.get('l1_connected', False) else '해제'
                l2_connected = '연결' if status_data.get('l2_connected', False) else '해제'
                bat_adc = status_data.get('bat_adc', 'N/A')  # BAT ADC 값 추가
                source = status_data.get('source', 'unknown')
                
                # RAW 데이터 추출 (ASCII 값 그대로 저장)
                raw_data = status_data.get('raw_data', '')
                if isinstance(raw_data, bytes):
                    # ASCII 값 그대로 디코딩
                    raw_display = raw_data.decode('ascii', errors='replace')[:100] + '...' if len(raw_data) > 100 else raw_data.decode('ascii', errors='replace')
                elif isinstance(raw_data, str):
                    raw_display = raw_data[:100] + '...' if len(raw_data) > 100 else raw_data
                else:
                    raw_display = str(raw_data)[:100] + '...' if len(str(raw_data)) > 100 else str(raw_data)
                
                # 상태 로그 라인 구성 (BAT ADC 및 RAW 데이터 포함)
                log_line = f"{timestamp}\t{battery}%\t{timer}\t\t{status}\t\t{l1_connected}\t{l2_connected}\t{bat_adc}\t{source}\t{raw_display}\n"
                
                # 파일에 기록
                with open(self.status_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                    
                # RAW 데이터가 있으면 별도 파일에도 기록
                if raw_data:
                    self.log_raw_data('STATUS', raw_data)
                    
        except Exception as e:
            print(f"상태 로그 기록 실패: {e}")
    
    def log_raw_data(self, data_type: str, raw_data: Any):
        """RAW 데이터를 별도 파일에 상세 기록 - ASCII 값 그대로 저장"""
        if not self.raw_log_file:
            return
            
        try:
            with self.log_lock:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # 데이터 타입별 처리 - ASCII 값 그대로 저장
                if isinstance(raw_data, bytes):
                    data_length = len(raw_data)
                    # ASCII 값 그대로 디코딩
                    ascii_data = raw_data.decode('ascii', errors='replace')
                    # HEX 값도 함께 저장
                    hex_data = raw_data.hex().upper()
                    
                    # 긴 데이터는 줄바꿈 처리
                    if len(ascii_data) > 80:
                        ascii_display = ascii_data[:80] + f"... (총 {data_length} bytes)"
                    else:
                        ascii_display = ascii_data
                        
                elif isinstance(raw_data, str):
                    data_length = len(raw_data.encode('utf-8'))
                    ascii_display = raw_data[:80] + f"... (총 {data_length} bytes)" if len(raw_data) > 80 else raw_data
                    hex_data = raw_data.encode('utf-8').hex().upper()
                else:
                    str_data = str(raw_data)
                    data_length = len(str_data.encode('utf-8'))
                    ascii_display = str_data[:80] + f"... (총 {data_length} bytes)" if len(str_data) > 80 else str_data
                    hex_data = str_data.encode('utf-8').hex().upper()
                
                # ASCII 값 우선 기록
                log_line = f"{timestamp}\t{data_type}\t\t{data_length}\t{ascii_display}\n"
                
                with open(self.raw_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                    
                    # HEX 값도 별도 라인에 기록
                    if len(hex_data) > 80:
                        hex_display = hex_data[:80] + f"... (총 {data_length} bytes)"
                        f.write(f"{timestamp}\t{data_type}_HEX\t{data_length}\t{hex_display}\n")
                        f.write(f"{timestamp}\t{data_type}_HEX_FULL\t{data_length}\t{hex_data}\n")
                    else:
                        f.write(f"{timestamp}\t{data_type}_HEX\t{data_length}\t{hex_data}\n")
                    
        except Exception as e:
            print(f"RAW 데이터 로그 기록 실패: {e}")
    
    def log_event(self, event_type: str, message: str, raw_data: Any = None):
        """이벤트 로그 기록 - RAW 데이터 선택적 포함"""
        if not self.status_log_file:
            return
            
        try:
            with self.log_lock:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # RAW 데이터가 있으면 간단히 표시
                if raw_data:
                    if isinstance(raw_data, bytes):
                        raw_info = f" [RAW: {len(raw_data)}bytes]"
                    elif isinstance(raw_data, str):
                        raw_info = f" [RAW: {len(raw_data)}chars]"
                    else:
                        raw_info = f" [RAW: {type(raw_data).__name__}]"
                    message_with_raw = message + raw_info
                else:
                    message_with_raw = message
                
                log_line = f"{timestamp}\t[{event_type}]\t{message_with_raw}\n"
                
                with open(self.status_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                    
                # RAW 데이터가 있으면 별도 로그에도 기록
                if raw_data:
                    self.log_raw_data(f"EVENT_{event_type}", raw_data)
                    
        except Exception as e:
            print(f"이벤트 로그 기록 실패: {e}")
    
    def log_screen_capture(self, success: bool, data_size: int = 0, raw_data: Any = None):
        """화면 캡처 결과 로그 기록"""
        event_type = "SCREEN_CAPTURE_SUCCESS" if success else "SCREEN_CAPTURE_FAIL"
        message = f"화면 캡처 {'성공' if success else '실패'}"
        if data_size > 0:
            message += f" (데이터 크기: {data_size} bytes)"
            
        self.log_event(event_type, message, raw_data)
    
    def get_log_file_path(self) -> str:
        """현재 상태 로그 파일 경로 반환"""
        return self.status_log_file
    
    def get_raw_log_file_path(self) -> str:
        """현재 RAW 로그 파일 경로 반환"""
        return self.raw_log_file

class FileManager:
    """파일 관리 클래스"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.ensure_directories()
        
    def ensure_directories(self):
        """필요한 디렉토리 생성"""
        dirs = [
            os.path.join(self.base_dir, "captures"),
            os.path.join(self.base_dir, "sessions"),
            os.path.join(self.base_dir, "logs"),
            os.path.join(self.base_dir, "config"),
            os.path.join(self.base_dir, "LOG")  # 상태 로그용 디렉토리 추가
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def get_capture_filename(self, prefix: str = "oled_capture") -> str:
        """캡처 파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        return os.path.join(self.base_dir, "captures", f"{prefix}_{timestamp}.png")
    
    def get_session_filename(self, prefix: str = "session") -> str:
        """세션 파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.base_dir, "sessions", f"{prefix}_{timestamp}.json")
    
    def get_log_filename(self, prefix: str = "monitor_log") -> str:
        """로그 파일명 생성"""
        date_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.base_dir, "logs", f"{prefix}_{date_str}.txt")
    
    def get_status_log_filename(self) -> str:
        """상태 로그 파일명 생성"""
        date_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.base_dir, "LOG", f"status_log_{date_str}.txt")
    
    def save_image(self, image_data: np.ndarray, filename: str = None) -> str:
        """이미지 저장"""
        if filename is None:
            filename = self.get_capture_filename()
            
        try:
            if image_data.dtype != np.uint8:
                image_data = image_data.astype(np.uint8)
                
            img = Image.fromarray(image_data)
            img.save(filename)
            return filename
        except Exception as e:
            raise Exception(f"이미지 저장 실패: {e}")
    
    def save_json(self, data: Dict, filename: str = None) -> str:
        """JSON 데이터 저장"""
        if filename is None:
            filename = self.get_session_filename()
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            return filename
        except Exception as e:
            raise Exception(f"JSON 저장 실패: {e}")
    
    def load_json(self, filename: str) -> Dict:
        """JSON 데이터 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"JSON 로드 실패: {e}")

class Logger:
    """로깅 클래스"""
    
    def __init__(self, log_file: str = None, console_output: bool = True):
        self.log_file = log_file
        self.console_output = console_output
        self.log_lock = threading.Lock()
        
        if self.log_file:
            file_manager = FileManager()
            self.log_file = file_manager.get_log_filename()
    
    def log(self, level: str, message: str, category: str = "GENERAL"):
        """로그 메시지 기록"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] [{category}] {message}"
        
        with self.log_lock:
            if self.console_output:
                print(log_entry)
            
            if self.log_file:
                try:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(log_entry + '\n')
                except Exception as e:
                    print(f"로그 파일 쓰기 실패: {e}")
    
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

class SerialPortManager:
    """시리얼 포트 관리 클래스"""
    
    @staticmethod
    def get_available_ports() -> List[Dict[str, str]]:
        """사용 가능한 시리얼 포트 목록 반환"""
        ports = []
        for port in serial.tools.list_ports.comports():
            port_info = {
                'device': port.device,
                'description': port.description,
                'manufacturer': port.manufacturer or "Unknown",
                'vid_pid': f"{port.vid:04X}:{port.pid:04X}" if port.vid and port.pid else "Unknown"
            }
            ports.append(port_info)
        return ports
    
    @staticmethod
    def is_port_available(port_name: str) -> bool:
        """포트 사용 가능 여부 확인"""
        available_ports = SerialPortManager.get_available_ports()
        return any(port['device'] == port_name for port in available_ports)
    
    @staticmethod
    def find_onboard_device() -> Optional[str]:
        """OnBoard 디바이스 자동 검색"""
        # STM32 관련 VID/PID 또는 제조사 정보로 필터링
        stm32_manufacturers = ['STMicroelectronics', 'ST-LINK']
        
        for port in SerialPortManager.get_available_ports():
            if any(mfg in port['manufacturer'] for mfg in stm32_manufacturers):
                return port['device']
        return None

class ImageProcessor:
    """이미지 처리 클래스"""
    
    @staticmethod
    def enhance_oled_image(image: np.ndarray, scale: int = 4) -> np.ndarray:
        """OLED 이미지 향상 처리"""
        # 스케일링
        if scale > 1:
            img = Image.fromarray(image)
            new_size = (image.shape[1] * scale, image.shape[0] * scale)
            img = img.resize(new_size, Image.NEAREST)
            image = np.array(img)
        
        return image
    
    @staticmethod
    def add_border(image: np.ndarray, border_width: int = 2, border_color: int = 128) -> np.ndarray:
        """이미지에 테두리 추가"""
        bordered = np.full((image.shape[0] + 2*border_width, 
                           image.shape[1] + 2*border_width), 
                          border_color, dtype=image.dtype)
        
        bordered[border_width:-border_width, border_width:-border_width] = image
        return bordered
    
    @staticmethod
    def create_comparison_image(images: List[np.ndarray], labels: List[str] = None) -> np.ndarray:
        """여러 이미지를 비교할 수 있는 이미지 생성"""
        if not images:
            return np.zeros((64, 128), dtype=np.uint8)
        
        # 모든 이미지를 같은 크기로 맞춤
        max_height = max(img.shape[0] for img in images)
        max_width = max(img.shape[1] for img in images)
        
        # 라벨 공간 추가 (있는 경우)
        label_height = 20 if labels else 0
        
        # 수평으로 배열
        total_width = sum(max_width for _ in images) + (len(images) - 1) * 10
        total_height = max_height + label_height
        
        result = np.zeros((total_height, total_width), dtype=np.uint8)
        
        x_offset = 0
        for i, img in enumerate(images):
            # 이미지 배치
            y_offset = label_height
            result[y_offset:y_offset+img.shape[0], 
                   x_offset:x_offset+img.shape[1]] = img
            
            # 라벨 추가 (간단한 텍스트)
            if labels and i < len(labels):
                # 여기서는 간단히 흰색 점으로 표시
                # 실제로는 PIL의 ImageDraw를 사용하여 텍스트 렌더링
                pass
            
            x_offset += max_width + 10
        
        return result

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            file_manager = FileManager()
            self.config_file = os.path.join(file_manager.base_dir, "config", "monitor_config.json")
        else:
            self.config_file = config_file
        
        self.default_config = {
            'serial': {
                'port': 'COM3',
                'baudrate': 115200,
                'timeout': 1.0
            },
            'display': {
                'scale': 4,
                'refresh_rate': 10,
                'auto_save': False
            },
            'capture': {
                'auto_save_interval': 60,
                'max_captures': 1000,
                'image_format': 'PNG'
            },
            'logging': {
                'level': 'INFO',
                'console_output': True,
                'file_output': True
            },
            'ui': {
                'window_size': '800x600',
                'theme': 'default',
                'language': 'ko'
            }
        }
        
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 기본 설정과 병합
                return self.merge_configs(self.default_config, loaded_config)
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"설정 로드 실패: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """설정 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 실패: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """설정 값 가져오기 (점으로 구분된 경로)"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """설정 값 설정 (점으로 구분된 경로)"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def merge_configs(self, base: Dict, update: Dict) -> Dict:
        """설정 딕셔너리 병합"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.stats = {
            'frames_captured': 0,
            'frames_dropped': 0,
            'avg_capture_time': 0.0,
            'avg_display_time': 0.0,
            'start_time': time.time()
        }
        self.capture_times = []
        self.display_times = []
        self.max_samples = 100
    
    def record_capture_time(self, capture_time: float):
        """캡처 시간 기록"""
        self.capture_times.append(capture_time)
        if len(self.capture_times) > self.max_samples:
            self.capture_times.pop(0)
        
        self.stats['frames_captured'] += 1
        self.stats['avg_capture_time'] = sum(self.capture_times) / len(self.capture_times)
    
    def record_display_time(self, display_time: float):
        """디스플레이 시간 기록"""
        self.display_times.append(display_time)
        if len(self.display_times) > self.max_samples:
            self.display_times.pop(0)
        
        self.stats['avg_display_time'] = sum(self.display_times) / len(self.display_times)
    
    def record_dropped_frame(self):
        """드롭된 프레임 기록"""
        self.stats['frames_dropped'] += 1
    
    def get_fps(self) -> float:
        """FPS 계산"""
        elapsed = time.time() - self.stats['start_time']
        if elapsed > 0:
            return self.stats['frames_captured'] / elapsed
        return 0.0
    
    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        stats = self.stats.copy()
        stats['fps'] = self.get_fps()
        stats['runtime'] = time.time() - self.stats['start_time']
        return stats
    
    def reset(self):
        """통계 초기화"""
        self.__init__()

class DataBuffer:
    """순환 데이터 버퍼"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = []
        self.index = 0
        self.is_full = False
    
    def append(self, data: Any):
        """데이터 추가"""
        if len(self.buffer) < self.max_size:
            self.buffer.append(data)
        else:
            self.buffer[self.index] = data
            self.index = (self.index + 1) % self.max_size
            self.is_full = True
    
    def get_latest(self, count: int = 1) -> List[Any]:
        """최신 데이터 가져오기"""
        if not self.buffer:
            return []
        
        if not self.is_full:
            return self.buffer[-count:]
        
        # 순환 버퍼에서 최신 데이터 추출
        result = []
        for i in range(count):
            idx = (self.index - 1 - i) % self.max_size
            if idx >= 0:
                result.insert(0, self.buffer[idx])
        
        return result
    
    def get_all(self) -> List[Any]:
        """모든 데이터 가져오기 (시간순)"""
        if not self.is_full:
            return self.buffer.copy()
        
        # 순환 버퍼 정렬
        return self.buffer[self.index:] + self.buffer[:self.index]
    
    def clear(self):
        """버퍼 클리어"""
        self.buffer.clear()
        self.index = 0
        self.is_full = False

class LogAnalyzer:
    """상태 로그 분석 클래스"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        
    def parse_log_entries(self) -> List[Dict]:
        """로그 엔트리 파싱"""
        entries = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith('=') or line.startswith('-') or '시간' in line:
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 6:
                    entry = {
                        'timestamp': parts[0],
                        'battery': parts[1],
                        'timer': parts[2],
                        'status': parts[3],
                        'l1': parts[4],
                        'l2': parts[5],
                        'note': parts[6] if len(parts) > 6 else ''
                    }
                    entries.append(entry)
                    
        except Exception as e:
            print(f"로그 파싱 오류: {e}")
            
        return entries
    
    def get_battery_stats(self) -> Dict:
        """배터리 통계 분석"""
        entries = self.parse_log_entries()
        
        battery_levels = []
        for entry in entries:
            try:
                if entry['battery'] != 'N/A' and '%' in entry['battery']:
                    level = int(entry['battery'].replace('%', ''))
                    battery_levels.append(level)
            except ValueError:
                continue
        
        if not battery_levels:
            return {'min': 0, 'max': 0, 'avg': 0, 'count': 0}
            
        return {
            'min': min(battery_levels),
            'max': max(battery_levels),
            'avg': sum(battery_levels) / len(battery_levels),
            'count': len(battery_levels)
        }
    
    def get_status_distribution(self) -> Dict:
        """상태 분포 분석"""
        entries = self.parse_log_entries()
        
        status_count = {}
        for entry in entries:
            status = entry['status'].strip()
            if status and status != 'N/A':
                status_count[status] = status_count.get(status, 0) + 1
                
        return status_count
    
    def get_connection_events(self) -> List[Dict]:
        """연결 이벤트 분석"""
        entries = self.parse_log_entries()
        
        events = []
        for entry in entries:
            note = entry.get('note', '')
            if any(keyword in note for keyword in ['CONNECT', 'DISCONNECT', 'START', 'STOP']):
                events.append({
                    'timestamp': entry['timestamp'],
                    'event': note
                })
                
        return events

if __name__ == "__main__":
    # 테스트 코드
    print("=== OLED Monitor Utils 테스트 ===")
    
    # StatusLogger 테스트
    status_logger = StatusLogger()
    test_status = {
        'battery': 75,
        'timer': '05:30',
        'status': 'RUNNING',
        'l1_connected': True,
        'l2_connected': False,
        'source': 'test'
    }
    status_logger.log_status(test_status)
    status_logger.log_event("TEST", "테스트 이벤트")
    print(f"상태 로그 파일: {status_logger.get_log_file_path()}")
    
    # FileManager 테스트
    fm = FileManager()
    print(f"캡처 파일명: {fm.get_capture_filename()}")
    print(f"상태 로그 파일명: {fm.get_status_log_filename()}")
    
    # SerialPortManager 테스트
    ports = SerialPortManager.get_available_ports()
    print(f"사용 가능한 포트: {len(ports)}개")
    for port in ports:
        print(f"  - {port['device']}: {port['description']}")
    
    print("테스트 완료!") 