# -*- coding: utf-8 -*-
"""
화면 데이터 파서 - OLED 화면 데이터 파싱 및 변환
"""

import numpy as np
from PIL import Image
import logging
from typing import Optional, Tuple, Union, Dict, Any
from core.interfaces import DataParserInterface
from core.constants import OLED_WIDTH, OLED_HEIGHT, OLED_PAGES, BYTES_PER_PAGE

class ScreenDataParser(DataParserInterface):
    """OLED 화면 데이터 파서"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parsing_method = "method5_flipped_v"  # 기본 파싱 방법
        self.last_raw_data = None
        self.numpy_available = True
        
        # 파싱 통계
        self.stats = {
            'total_parses': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'average_parsing_time': 0.0,
            'last_parse_time': 0.0
        }
        
        try:
            import numpy as np
            self.numpy_available = True
        except ImportError:
            self.numpy_available = False
            self.logger.warning("NumPy를 사용할 수 없습니다. 기본 파싱 모드로 전환합니다.")
    
    def parse_screen_data(self, data: bytes) -> Optional[np.ndarray]:
        """화면 데이터 파싱 (인터페이스 구현)"""
        return self.parse(data)
    
    def parse_status_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """상태 데이터 파싱 (인터페이스 구현) - 화면 파서에서는 None 반환"""
        return None
    
    def validate_data(self, data: Any) -> bool:
        """데이터 유효성 검증 (인터페이스 구현)"""
        if isinstance(data, np.ndarray):
            return data.shape == (OLED_HEIGHT, OLED_WIDTH) and data.dtype == np.uint8
        return False
    
    def parse(self, data: bytes) -> Optional[np.ndarray]:
        """화면 데이터 파싱"""
        import time
        start_time = time.time()
        
        try:
            self.stats['total_parses'] += 1
            
            # 펌웨어 화면 데이터 파싱
            result = self.parse_firmware_screen_data(data)
            
            if result is not None:
                self.stats['successful_parses'] += 1
                self.logger.debug(f"화면 파싱 성공: {result.shape}")
            else:
                self.stats['failed_parses'] += 1
                self.logger.warning("화면 파싱 실패")
            
            # 파싱 시간 기록
            parsing_time = time.time() - start_time
            self.stats['last_parse_time'] = parsing_time
            self.stats['average_parsing_time'] = (
                (self.stats['average_parsing_time'] * (self.stats['total_parses'] - 1) + parsing_time) /
                self.stats['total_parses']
            )
            
            return result
            
        except Exception as e:
            self.stats['failed_parses'] += 1
            self.logger.error(f"화면 파싱 오류: {e}")
            return None
    
    def parse_firmware_screen_data(self, data: bytes) -> Optional[np.ndarray]:
        """펌웨어 화면 데이터 파싱 - 원본 로직 적용"""
        try:
            # 새로운 마커 형식 먼저 확인
            if b'<<SCREEN_START>>' in data and b'<<DATA_START>>' in data:
                # 새로운 형식으로 처리
                data_start_pos = data.find(b'<<DATA_START>>')
                data_end_pos = data.find(b'<<DATA_END>>')
                
                if data_start_pos != -1 and data_end_pos != -1:
                    data_start_actual = data.find(b'\n', data_start_pos) + 1
                    img_data = data[data_start_actual:data_end_pos]
                    
                    if len(img_data) >= 1024:
                        return self.parse_firmware_screen_data_enhanced(img_data[:1024])
            
            # 기존 형식 처리 (하위 호환성)
            self.logger.debug("기존 형식으로 파싱 시도")
            
            img_data = None
            
            # 기존 SCREEN_START 찾기
            last_start_idx = data.rfind(b'SCREEN_START')
            if last_start_idx != -1:
                screen_data_part = data[last_start_idx:]
                
                start_idx = screen_data_part.find(b'SCREEN_START')
                size_idx = screen_data_part.find(b'SIZE:128x64')
                format_idx = screen_data_part.find(b'FORMAT:PAINT_IMAGE')
                end_idx = screen_data_part.find(b'SCREEN_END')
                
                if start_idx != -1 and size_idx != -1 and end_idx != -1:
                    if format_idx != -1 and format_idx > size_idx:
                        header_end_pos = screen_data_part.find(b'\n', format_idx)
                    else:
                        header_end_pos = screen_data_part.find(b'\n', size_idx)
                    
                    if header_end_pos != -1:
                        img_start = header_end_pos + 1
                        search_start = max(0, end_idx - 10)
                        newline_before_end = screen_data_part.rfind(b'\n', search_start, end_idx)
                        
                        if newline_before_end != -1:
                            img_end = newline_before_end
                        else:
                            img_end = end_idx
                        
                        img_data = screen_data_part[img_start:img_end]
            
            # 바이너리 데이터 처리
            if img_data is None:
                try:
                    text_ratio = len([b for b in data if 32 <= b <= 126]) / max(len(data), 1)
                    if text_ratio < 0.1:
                        img_data = data
                except:
                    pass
                
                if img_data is None:
                    end_idx = data.rfind(b'SCREEN_END')
                    if end_idx != -1:
                        start_pos = max(0, end_idx - 1024)
                        img_data = data[start_pos:end_idx]
                    else:
                        img_data = data
            
            if img_data is None or len(img_data) == 0:
                return None
            
            # 크기 조정
            if len(img_data) < 1024:
                img_data = img_data + b'\x00' * (1024 - len(img_data))
            elif len(img_data) > 1024:
                img_data = img_data[-1024:]
            
            # 실제 파싱
            return self.parse_firmware_screen_data_enhanced(img_data)
            
        except Exception as e:
            self.logger.error(f"펌웨어 화면 데이터 파싱 오류: {e}")
            return None
    
    def parse_firmware_screen_data_enhanced(self, img_data: bytes) -> Optional[np.ndarray]:
        """강화된 펌웨어 화면 데이터 파싱 - 원본 로직 적용"""
        try:
            if len(img_data) != 1024:
                self.logger.warning(f"잘못된 데이터 크기: {len(img_data)}")
                return None
            
            # 원본 데이터 저장
            self.last_raw_data = img_data
            
            # NumPy 사용 불가능한 경우 기본 파싱
            if not self.numpy_available:
                return self._parse_without_numpy(img_data)
            
            import numpy as np
            
            # OLED 데이터를 PIL 이미지로 변환
            img_array = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
            width_bytes = OLED_WIDTH // 8  # 16 bytes per row
            
            self.logger.debug(f"파싱 방법: {self.parsing_method}")
            
            # 기본 파싱 (원본 데이터)
            temp_array = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
            
            for row in range(OLED_HEIGHT):
                for byte_col in range(width_bytes):
                    byte_idx = byte_col + row * width_bytes
                    
                    if byte_idx < len(img_data):
                        byte_value = img_data[byte_idx]
                        
                        for bit in range(8):
                            x = byte_col * 8 + bit
                            y = row
                            
                            if x < OLED_WIDTH and y < OLED_HEIGHT:
                                bit_value = (byte_value >> (7 - bit)) & 1
                                temp_array[y, x] = 255 if bit_value else 0
            
            # 파싱 방법에 따른 변환 적용 (원본 로직 그대로)
            if self.parsing_method == "method1_direct":
                # 방법 1: 직접 매핑 (변환 없음)
                img_array = temp_array.copy()
                
            elif self.parsing_method == "method2_reversed":
                # 방법 2: reverse 함수 적용
                for row in range(OLED_HEIGHT):
                    for byte_col in range(width_bytes):
                        byte_idx = byte_col + row * width_bytes
                        
                        if byte_idx < len(img_data):
                            byte_value = img_data[byte_idx]
                            reversed_byte = self.reverse_byte(byte_value)
                            
                            for bit in range(8):
                                x = byte_col * 8 + bit
                                y = row
                                
                                if x < OLED_WIDTH and y < OLED_HEIGHT:
                                    bit_value = (reversed_byte >> (7 - bit)) & 1
                                    img_array[y, x] = 255 if bit_value else 0
                                    
            elif self.parsing_method == "method3_rotated_180":
                # 방법 3: 180도 회전
                img_array = np.rot90(temp_array, 2)
                
            elif self.parsing_method == "method4_flipped_h":
                # 방법 4: 가로 뒤집기
                img_array = np.fliplr(temp_array)
                
            elif self.parsing_method == "method5_flipped_v":
                # 방법 5: 세로 뒤집기 (기본, 안정적)
                img_array = np.flipud(temp_array)
                
            elif self.parsing_method == "method5_rotate_90":
                # 방법 5-1: 90도 시계방향 회전
                img_array = np.rot90(temp_array, -1)  # -1은 시계방향
                
            elif self.parsing_method == "method5_rotate_270":
                # 방법 5-2: 270도 시계방향 회전 (90도 반시계방향)
                img_array = np.rot90(temp_array, 1)   # 1은 반시계방향
                
            elif self.parsing_method == "method5_mirror_h":
                # 방법 5-3: 가로 미러링 (좌우 반전)
                img_array = np.fliplr(temp_array)
                
            elif self.parsing_method == "method5_mirror_v":
                # 방법 5-4: 세로 미러링 (상하 반전)
                img_array = np.flipud(temp_array)
                
            elif self.parsing_method == "method5_flip_both":
                # 방법 5-5: 상하좌우 모두 뒤집기
                img_array = np.flipud(np.fliplr(temp_array))
                
            elif self.parsing_method == "method6_transposed":
                # 방법 6: 전치 + 조정
                transposed = temp_array.T
                from PIL import Image
                pil_img = Image.fromarray(transposed.astype(np.uint8), mode='L')
                resized_img = pil_img.resize((OLED_WIDTH, OLED_HEIGHT), Image.NEAREST)
                img_array = np.array(resized_img)
                
            else:
                # 기본값: 세로 뒤집기
                self.logger.warning(f"알 수 없는 파싱 방법: {self.parsing_method}, 기본값 적용")
                img_array = np.flipud(temp_array)
            
            # 데이터 검증
            white_pixels = np.sum(img_array == 255)
            black_pixels = np.sum(img_array == 0)
            total_pixels = OLED_WIDTH * OLED_HEIGHT
            
            if total_pixels == 0:
                self.logger.warning("빈 이미지 데이터")
                return None
                
            white_ratio = (white_pixels / total_pixels) * 100
            # 파싱 완료 로그를 간소화 (과도한 출력 방지)
            if white_ratio > 5:  # 의미있는 데이터가 있을 때만 상세 로그
                self.logger.debug(f"화면 파싱 완료 - 흰색 픽셀: {white_ratio:.1f}%")
            else:
                self.logger.debug("화면 파싱 완료")
            
            self.logger.debug(f"화면 데이터 검증: 흰색={white_pixels}, 검은색={black_pixels}, 전체={total_pixels}")
            
            return img_array
            
        except Exception as e:
            self.logger.error(f"강화된 화면 파싱 오류: {e}")
            return None
    
    def _parse_without_numpy(self, img_data: bytes) -> Optional[list]:
        """NumPy 없이 파싱 - 원본 로직 적용"""
        try:
            # 원본 데이터 저장
            self.last_raw_data = img_data
            
            # 2D 리스트로 이미지 데이터 생성
            img_array = [[0 for _ in range(OLED_WIDTH)] for _ in range(OLED_HEIGHT)]
            width_bytes = OLED_WIDTH // 8
            
            for row in range(OLED_HEIGHT):
                for byte_col in range(width_bytes):
                    byte_idx = byte_col + row * width_bytes
                    
                    if byte_idx < len(img_data):
                        byte_value = img_data[byte_idx]
                        
                        for bit in range(8):
                            x = byte_col * 8 + bit
                            y = row
                            
                            if x < OLED_WIDTH and y < OLED_HEIGHT:
                                bit_value = (byte_value >> (7 - bit)) & 1
                                img_array[y][x] = 255 if bit_value else 0
            
            # 기본 파싱 방법 적용 (세로 뒤집기)
            if self.parsing_method == "method3_rotated_180":
                # 180도 회전 (단순 구현)
                img_array = img_array[::-1]
                for row in img_array:
                    row.reverse()
            elif self.parsing_method == "method4_flipped_h":
                # 가로 뒤집기
                for row in img_array:
                    row.reverse()
            elif self.parsing_method == "method5_flipped_v":
                # 세로 뒤집기 (기본)
                img_array = img_array[::-1]
            
            return img_array
            
        except Exception as e:
            self.logger.error(f"기본 파싱 오류: {e}")
            return None
    
    def reverse_byte(self, byte_val: int) -> int:
        """OLED 드라이버의 reverse() 함수 구현 - 원본 로직"""
        temp = byte_val
        temp = ((temp & 0x55) << 1) | ((temp & 0xaa) >> 1)
        temp = ((temp & 0x33) << 2) | ((temp & 0xcc) >> 2) 
        temp = ((temp & 0x0f) << 4) | ((temp & 0xf0) >> 4)
        return temp
    
    def set_parsing_method(self, method: str):
        """파싱 방법 설정"""
        self.parsing_method = method
        self.logger.info(f"파싱 방법 변경: {method}")
    
    def get_parsing_stats(self) -> dict:
        """파싱 통계 반환"""
        success_rate = 0.0
        if self.stats['total_parses'] > 0:
            success_rate = self.stats['successful_parses'] / self.stats['total_parses']
        
        return {
            **self.stats,
            'success_rate': success_rate
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            'total_parses': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'average_parsing_time': 0.0,
            'last_parse_time': 0.0
        }
    
    def create_test_screen(self, pattern: str = "checkerboard") -> Optional[np.ndarray]:
        """테스트 화면 생성"""
        try:
            if not self.numpy_available:
                return None
            
            import numpy as np
            
            img_array = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
            
            if pattern == "checkerboard":
                # 체스판 패턴
                for y in range(OLED_HEIGHT):
                    for x in range(OLED_WIDTH):
                        if (x // 8 + y // 8) % 2 == 0:
                            img_array[y, x] = 255
                            
            elif pattern == "stripes":
                # 세로 줄무늬
                for y in range(OLED_HEIGHT):
                    for x in range(OLED_WIDTH):
                        if x % 16 < 8:
                            img_array[y, x] = 255
                            
            elif pattern == "border":
                # 테두리
                img_array[0, :] = 255  # 상단
                img_array[-1, :] = 255  # 하단
                img_array[:, 0] = 255  # 좌측
                img_array[:, -1] = 255  # 우측
            
            return img_array
            
        except Exception as e:
            self.logger.error(f"테스트 화면 생성 오류: {e}")
            return None 