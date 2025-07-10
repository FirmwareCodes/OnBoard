import struct
import numpy as np
from typing import Dict, Optional, Tuple
import re
from datetime import datetime
import time

class SerialDataParser:
    """시리얼 데이터 파싱 클래스"""
    
    def __init__(self):
        self.OLED_WIDTH = 128
        self.OLED_HEIGHT = 64
        self.IMAGE_SIZE = (self.OLED_WIDTH // 8) * self.OLED_HEIGHT  # 1024 bytes
        
        # 명령어 패턴
        self.SCREEN_START_PATTERN = b'SCREEN_START'
        self.SCREEN_END_PATTERN = b'SCREEN_END'
        self.STATUS_PATTERN = b'STATUS:'
        
    def parse_screen_data(self, data: bytes) -> Optional[np.ndarray]:
        """
        화면 데이터 파싱
        
        Args:
            data: 시리얼에서 받은 원시 데이터
            
        Returns:
            np.ndarray: 128x64 화면 데이터 또는 None
        """
        try:
            # 화면 데이터 시작/끝 패턴 찾기
            start_idx = data.find(self.SCREEN_START_PATTERN)
            end_idx = data.find(self.SCREEN_END_PATTERN)
            
            if start_idx == -1 or end_idx == -1:
                return None
                
            # 화면 데이터 추출
            screen_start = start_idx + len(self.SCREEN_START_PATTERN)
            screen_data = data[screen_start:end_idx]
            
            # 크기 정보 파싱
            size_match = re.search(rb'SIZE:(\d+)x(\d+)', screen_data)
            if size_match:
                width = int(size_match.group(1))
                height = int(size_match.group(2))
                
                # 크기 정보 다음부터 실제 이미지 데이터
                img_start = size_match.end() + 1
                img_data = screen_data[img_start:]
                
                # OLED 데이터를 이미지 배열로 변환
                return self.convert_oled_to_array(img_data, width, height)
            
            return None
            
        except Exception as e:
            print(f"화면 데이터 파싱 오류: {e}")
            return None
    
    def convert_oled_to_array(self, data: bytes, width: int, height: int) -> np.ndarray:
        """
        OLED 원시 데이터를 numpy 배열로 변환
        
        Args:
            data: OLED 원시 데이터 (1024 bytes)
            width: 화면 너비
            height: 화면 높이
            
        Returns:
            np.ndarray: 128x64 이미지 배열
        """
        img_array = np.zeros((height, width), dtype=np.uint8)
        
        try:
            # OLED SH1106 컨트롤러 데이터 형식에 맞춰 변환
            for page in range(height // 8):  # 8 pages (64/8)
                for col in range(width // 8):  # 16 columns (128/8)
                    if page * (width // 8) + col < len(data):
                        byte_data = data[page * (width // 8) + col]
                        
                        # 각 비트를 픽셀로 변환
                        for bit in range(8):
                            y = page * 8 + bit
                            x = col * 8
                            
                            if y < height and x < width:
                                # 비트가 설정되어 있으면 흰색(255), 아니면 검은색(0)
                                if byte_data & (1 << bit):
                                    img_array[y, x:x+8] = 255
                                    
        except Exception as e:
            print(f"OLED 데이터 변환 오류: {e}")
            
        return img_array
    
    def parse_status_data(self, data: bytes) -> Optional[Dict]:
        """
        상태 데이터 파싱 - BAT ADC 안전 처리 및 무한루프 방지
        
        Args:
            data: 시리얼에서 받은 상태 데이터
            
        Returns:
            Dict: 파싱된 상태 정보 또는 None (RAW 데이터 포함)
        """
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
            
            # 각 항목 파싱 (안전한 방식)
            status_info = {
                'timestamp': datetime.now().strftime('%H:%M:%S'), 
                'source': 'firmware',
                'raw_data': raw_data,  # 원본 RAW 데이터 추가
                'raw_string': data_str  # 문자열 형태도 추가
            }
            
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
                        if key == 'BAT':
                            # 배터리 파싱 (안전한 처리)
                            try:
                                battery_str = value.replace('V', '').strip()
                                if battery_str.isdigit():
                                    battery_val = int(battery_str)
                                    status_info['battery'] = battery_val/100
                                else:
                                    status_info['battery'] = 0
                            except (ValueError, TypeError):
                                status_info['battery'] = 0
                                
                        elif key == 'TIMER':
                            # 타이머 파싱 (형식 검증)
                            if len(value) <= 8 and ':' in value:
                                status_info['timer'] = value
                            else:
                                status_info['timer'] = '00:00'
                                
                        elif key == 'STATUS':
                            # 상태 파싱 (길이 제한)
                            if len(value) <= 15:
                                status_info['status'] = value
                            else:
                                status_info['status'] = 'UNKNOWN'
                                
                        elif key == 'L1':
                            # L1 연결 상태 (안전한 변환)
                            status_info['l1_connected'] = (value == '1')
                            
                        elif key == 'L2':
                            # L2 연결 상태 (안전한 변환)
                            status_info['l2_connected'] = (value == '1')
                            
                        elif key == 'BAT_ADC':
                            # BAT ADC 파싱 (강화된 안전 처리)
                            try:
                                # 숫자 문자열 검증
                                if value.isdigit() and len(value) <= 5:  # 최대 5자리
                                    adc_val = int(value)
                                    # 12-bit ADC 범위 검증 (0-4095)
                                    if 0 <= adc_val <= 4095:
                                        status_info['bat_adc'] = adc_val
                                    else:
                                        # 범위 벗어나면 보정
                                        status_info['bat_adc'] = max(0, min(4095, adc_val))
                                else:
                                    # 잘못된 형식
                                    status_info['bat_adc'] = 0
                            except (ValueError, TypeError, OverflowError):
                                # 모든 변환 오류 처리
                                status_info['bat_adc'] = 0
                                
                    except Exception as item_error:
                        # 개별 아이템 파싱 오류시 계속 진행
                        continue
                
            except Exception as split_error:
                # 분할 오류시 기본값 반환
                pass
            
            # 필수 필드 기본값 설정
            if 'battery' not in status_info:
                status_info['battery'] = 0
            if 'timer' not in status_info:
                status_info['timer'] = '00:00'
            if 'status' not in status_info:
                status_info['status'] = 'UNKNOWN'
            if 'l1_connected' not in status_info:
                status_info['l1_connected'] = False
            if 'l2_connected' not in status_info:
                status_info['l2_connected'] = False
            if 'bat_adc' not in status_info:
                status_info['bat_adc'] = 0
            
            # 최종 파싱 시간 체크
            parse_duration = time.time() - start_time
            if parse_duration > 0.5:  # 0.5초 이상 걸리면 경고
                print(f"⚠️ 시리얼 파서 지연: {parse_duration:.2f}초")
            
            return status_info
            
        except Exception as e:
            # 모든 예외를 안전하게 처리
            print(f"❌ 시리얼 파서 오류: {str(e)}")
            return None
    
    def create_test_screen_data(self, pattern: str = "checkerboard") -> np.ndarray:
        """
        테스트용 화면 데이터 생성
        
        Args:
            pattern: 패턴 타입 ("checkerboard", "gradient", "text")
            
        Returns:
            np.ndarray: 테스트 화면 데이터
        """
        img = np.zeros((self.OLED_HEIGHT, self.OLED_WIDTH), dtype=np.uint8)
        
        if pattern == "checkerboard":
            # 체크보드 패턴
            for y in range(self.OLED_HEIGHT):
                for x in range(self.OLED_WIDTH):
                    if (x // 8 + y // 8) % 2:
                        img[y, x] = 255
                        
        elif pattern == "gradient":
            # 그라디언트 패턴
            for y in range(self.OLED_HEIGHT):
                for x in range(self.OLED_WIDTH):
                    img[y, x] = int((x / self.OLED_WIDTH) * 255)
                    
        elif pattern == "text":
            # 간단한 텍스트 패턴
            # 중앙에 "OLED" 텍스트 모양 그리기
            center_x, center_y = self.OLED_WIDTH // 2, self.OLED_HEIGHT // 2
            
            # 간단한 "OLED" 비트맵
            for y in range(-8, 8):
                for x in range(-20, 20):
                    if abs(y) < 3 and abs(x) < 15:
                        if center_y + y >= 0 and center_y + y < self.OLED_HEIGHT and \
                           center_x + x >= 0 and center_x + x < self.OLED_WIDTH:
                            img[center_y + y, center_x + x] = 255
                            
        return img
    
    def create_test_status_data(self) -> Dict:
        """테스트용 상태 데이터 생성"""
        import random
        
        statuses = ['STANDBY', 'RUNNING', 'SETTING', 'COOLING']
        
        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': 'test_data',
            'battery': random.randint(20, 100),
            'timer': f"{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            'status': random.choice(statuses),
            'l1_connected': random.choice([True, False]),
            'l2_connected': random.choice([True, False]),
            'bat_adc': random.randint(0, 4095),  # 12-bit ADC 값
            'raw_data': b'STATUS:BAT:75%,TIMER:05:30,STATUS:RUNNING,L1:1,L2:0,BAT_ADC:2048',
            'raw_string': 'STATUS:BAT:75%,TIMER:05:30,STATUS:RUNNING,L1:1,L2:0,BAT_ADC:2048'
        }
    
    def validate_screen_data(self, data: np.ndarray) -> bool:
        """
        화면 데이터 유효성 검증
        
        Args:
            data: 화면 데이터
            
        Returns:
            bool: 유효성 여부
        """
        if data is None:
            return False
            
        if data.shape != (self.OLED_HEIGHT, self.OLED_WIDTH):
            return False
            
        if data.dtype != np.uint8:
            return False
            
        return True
    
    def validate_status_data(self, status: Dict) -> bool:
        """
        상태 데이터 유효성 검증
        
        Args:
            status: 상태 데이터
            
        Returns:
            bool: 유효성 여부
        """
        if not isinstance(status, dict):
            return False
            
        required_fields = ['battery', 'timer', 'status', 'l1_connected', 'l2_connected']
        
        for field in required_fields:
            if field not in status:
                return False
                
        # 배터리 범위 검증
        if not (0 <= status['battery'] <= 100):
            return False
            
        # 타이머 형식 검증
        timer_pattern = r'^\d{1,2}:\d{2}$'
        if not re.match(timer_pattern, status['timer']):
            return False
            
        return True
    
    def encode_command(self, command: str, params: Dict = None) -> bytes:
        """
        펌웨어로 전송할 명령어 인코딩
        
        Args:
            command: 명령어 문자열
            params: 추가 매개변수
            
        Returns:
            bytes: 인코딩된 명령어
        """
        if params:
            param_str = ",".join([f"{k}:{v}" for k, v in params.items()])
            cmd = f"{command}:{param_str}\n"
        else:
            cmd = f"{command}\n"
            
        return cmd.encode('utf-8')
    
    def decode_response(self, data: bytes) -> Tuple[str, Dict]:
        """
        펌웨어 응답 디코딩
        
        Args:
            data: 응답 데이터
            
        Returns:
            Tuple[str, Dict]: (응답 타입, 데이터)
        """
        try:
            data_str = data.decode('utf-8', errors='ignore').strip()
            
            if data_str.startswith('OK:'):
                return 'success', {'message': data_str[3:]}
            elif data_str.startswith('ERROR:'):
                return 'error', {'message': data_str[6:]}
            elif data_str.startswith('STATUS:'):
                status_data = self.parse_status_data(data)
                return 'status', status_data or {}
            elif self.SCREEN_START_PATTERN in data:
                screen_data = self.parse_screen_data(data)
                return 'screen', {'data': screen_data}
            else:
                return 'unknown', {'raw': data_str}
                
        except Exception as e:
            return 'error', {'message': f"디코딩 오류: {e}"}

class ProtocolManager:
    """통신 프로토콜 관리 클래스"""
    
    def __init__(self):
        self.parser = SerialDataParser()
        self.command_queue = []
        self.response_handlers = {}
        self.status_logger = None  # 상태 로거 참조
        
    def set_status_logger(self, logger):
        """상태 로거 설정"""
        self.status_logger = logger
        
    def register_handler(self, response_type: str, handler):
        """응답 타입별 핸들러 등록"""
        self.response_handlers[response_type] = handler
        
    def process_data(self, data: bytes):
        """수신된 데이터 처리"""
        response_type, response_data = self.parser.decode_response(data)
        
        # 상태 데이터인 경우 로거에 기록
        if response_type == 'status' and self.status_logger and response_data:
            self.status_logger.log_status(response_data)
        
        if response_type in self.response_handlers:
            self.response_handlers[response_type](response_data)
        else:
            print(f"처리되지 않은 응답 타입: {response_type}")
            
    def send_command(self, serial_port, command: str, params: Dict = None):
        """명령어 전송"""
        try:
            cmd_data = self.parser.encode_command(command, params)
            serial_port.write(cmd_data)
            
            # 명령어 전송 로그
            if self.status_logger:
                self.status_logger.log_event("COMMAND", f"{command} 전송")
                
            return True
        except Exception as e:
            print(f"명령어 전송 오류: {e}")
            if self.status_logger:
                self.status_logger.log_event("ERROR", f"명령어 전송 오류: {e}")
            return False

if __name__ == "__main__":
    # 테스트 코드
    parser = SerialDataParser()
    
    # 테스트 화면 데이터 생성
    test_screen = parser.create_test_screen_data("checkerboard")
    print(f"테스트 화면 데이터 생성: {test_screen.shape}")
    
    # 테스트 상태 데이터 생성
    test_status = parser.create_test_status_data()
    print(f"테스트 상태 데이터: {test_status}")
    
    # 명령어 인코딩 테스트
    cmd = parser.encode_command("GET_SCREEN")
    print(f"명령어 인코딩: {cmd}")
    
    # 상태 데이터 파싱 테스트
    test_status_raw = b"STATUS:BAT:75%,TIMER:05:30,STATUS:RUNNING,L1:1,L2:0"
    status = parser.parse_status_data(test_status_raw)
    print(f"상태 파싱 결과: {status}")
    
    # 유효성 검증 테스트
    print(f"화면 데이터 유효성: {parser.validate_screen_data(test_screen)}")
    print(f"상태 데이터 유효성: {parser.validate_status_data(status)}") 