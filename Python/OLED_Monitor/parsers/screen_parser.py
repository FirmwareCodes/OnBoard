# -*- coding: utf-8 -*-
"""
OLED 화면 데이터 파서
"""

import numpy as np
from typing import Optional, Dict, Any
import re
import logging

from core.interfaces import DataParserInterface
from core.constants import OLED_WIDTH, OLED_HEIGHT, OLED_PAGES, BYTES_PER_PAGE
from core.exceptions import ScreenDataError, ValidationError

class ScreenDataParser(DataParserInterface):
    """화면 데이터 파싱 최적화 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._compiled_patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """정규식 패턴 미리 컴파일"""
        return {
            'screen_data': re.compile(rb'SCREEN_START(.*?)SCREEN_END', re.DOTALL),
            'screen_size': re.compile(rb'SIZE:(\d+)x(\d+)'),
            'hex_data': re.compile(rb'[0-9A-Fa-f]{2}'),
            'raw_hex': re.compile(rb'([0-9A-Fa-f]{2})+'),
        }
    
    def parse_screen_data(self, data: bytes) -> Optional[np.ndarray]:
        """화면 데이터 파싱 - 펌웨어 호환 버전"""
        try:
            # 1. SCREEN_START/SCREEN_END 패턴 매칭
            screen_match = self._compiled_patterns['screen_data'].search(data)
            if not screen_match:
                return self._try_fallback_parsing(data)
            
            # 2. 화면 데이터 추출
            screen_data = screen_match.group(1)
            
            # 3. 크기 정보 파싱
            size_match = self._compiled_patterns['screen_size'].search(screen_data)
            if size_match:
                width = int(size_match.group(1))
                height = int(size_match.group(2))
                
                # 크기 정보 다음부터 실제 이미지 데이터
                img_start = size_match.end() + 1
                img_data = screen_data[img_start:]
                
                # OLED 데이터를 이미지 배열로 변환
                return self._convert_oled_to_array_firmware(img_data, width, height)
            
            # 4. 크기 정보가 없으면 기본 크기로 처리
            return self._parse_hex_data_optimized(screen_data)
            
        except Exception as e:
            self.logger.error(f"화면 데이터 파싱 실패: {e}")
            raise ScreenDataError(f"화면 데이터 파싱 실패: {e}")
    
    def _parse_hex_data_optimized(self, hex_data: bytes) -> Optional[np.ndarray]:
        """헥스 데이터 파싱 최적화"""
        try:
            # 헥스 문자열 정리
            hex_str = hex_data.decode('ascii', errors='ignore')
            hex_str = ''.join(c for c in hex_str if c in '0123456789ABCDEFabcdef')
            
            # 길이 검증
            expected_length = OLED_WIDTH * OLED_PAGES * 2  # 각 바이트는 2개 헥스 문자
            if len(hex_str) < expected_length:
                self.logger.warning(f"헥스 데이터 길이 부족: {len(hex_str)} < {expected_length}")
                hex_str = hex_str.ljust(expected_length, '0')
            
            # 바이트 배열로 변환 (벡터화)
            hex_pairs = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
            byte_array = np.array([int(pair, 16) for pair in hex_pairs[:OLED_WIDTH * OLED_PAGES]], dtype=np.uint8)
            
            # OLED 형식으로 변환
            return self._convert_to_oled_format(byte_array)
            
        except Exception as e:
            self.logger.error(f"헥스 데이터 변환 실패: {e}")
            return None
    
    def _convert_to_oled_format(self, byte_array: np.ndarray) -> np.ndarray:
        """바이트 배열을 OLED 화면 형식으로 변환"""
        try:
            # 페이지별로 재구성
            screen = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
            
            for page in range(OLED_PAGES):
                page_start = page * OLED_WIDTH
                page_end = page_start + OLED_WIDTH
                page_data = byte_array[page_start:page_end]
                
                # 각 바이트를 8개 픽셀로 변환
                for x in range(OLED_WIDTH):
                    if x < len(page_data):
                        byte_val = page_data[x]
                        for bit in range(8):
                            y = page * 8 + bit
                            if y < OLED_HEIGHT:
                                screen[y, x] = 255 if (byte_val & (1 << bit)) else 0
            
            return screen
            
        except Exception as e:
            self.logger.error(f"OLED 형식 변환 실패: {e}")
            return None
    
    def _convert_oled_to_array_firmware(self, data: bytes, width: int, height: int) -> np.ndarray:
        """펌웨어 호환 OLED 데이터 변환"""
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
            self.logger.error(f"펌웨어 OLED 데이터 변환 실패: {e}")
            
        return img_array
    
    def _try_fallback_parsing(self, data: bytes) -> Optional[np.ndarray]:
        """대체 파싱 방법들"""
        parsers = [
            self._parse_raw_hex,
            self._parse_legacy_format,
            self._parse_without_markers,
        ]
        
        for parser in parsers:
            try:
                result = parser(data)
                if result is not None:
                    self.logger.info(f"대체 파싱 성공: {parser.__name__}")
                    return result
            except Exception as e:
                self.logger.debug(f"대체 파싱 실패 {parser.__name__}: {e}")
                continue
        
        return None
    
    def _parse_raw_hex(self, data: bytes) -> Optional[np.ndarray]:
        """원시 헥스 데이터 파싱"""
        hex_matches = self._compiled_patterns['hex_data'].findall(data)
        if len(hex_matches) >= OLED_WIDTH * OLED_PAGES:
            hex_str = b''.join(hex_matches[:OLED_WIDTH * OLED_PAGES]).decode('ascii')
            return self._parse_hex_data_optimized(hex_str.encode())
        return None
    
    def _parse_legacy_format(self, data: bytes) -> Optional[np.ndarray]:
        """레거시 형식 파싱"""
        try:
            # 레거시 패턴 시도
            lines = data.decode('ascii', errors='ignore').split('\n')
            hex_data = ''.join(line.strip() for line in lines if line.strip())
            
            if len(hex_data) >= OLED_WIDTH * OLED_PAGES * 2:
                return self._parse_hex_data_optimized(hex_data.encode())
        except:
            pass
        return None
    
    def _parse_without_markers(self, data: bytes) -> Optional[np.ndarray]:
        """마커 없는 데이터 파싱"""
        try:
            # 연속된 헥스 문자열 찾기
            hex_match = self._compiled_patterns['raw_hex'].search(data)
            if hex_match:
                hex_data = hex_match.group(0)
                if len(hex_data) >= OLED_WIDTH * OLED_PAGES * 2:
                    return self._parse_hex_data_optimized(hex_data)
        except:
            pass
        return None
    
    def parse_status_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """상태 데이터 파싱 (인터페이스 구현)"""
        # 화면 파서에서는 상태 데이터 파싱 안함
        return None
    
    def validate_data(self, data: Any) -> bool:
        """화면 데이터 유효성 검증"""
        if not isinstance(data, np.ndarray):
            return False
        
        if data.shape != (OLED_HEIGHT, OLED_WIDTH):
            return False
        
        if data.dtype != np.uint8:
            return False
        
        # 값 범위 검증
        if not np.all((data == 0) | (data == 255)):
            return False
        
        return True
    
    def create_test_screen(self, pattern: str = "checkerboard") -> np.ndarray:
        """테스트용 화면 데이터 생성"""
        screen = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
        
        if pattern == "checkerboard":
            for y in range(OLED_HEIGHT):
                for x in range(OLED_WIDTH):
                    if (x + y) % 2 == 0:
                        screen[y, x] = 255
        
        elif pattern == "gradient":
            for x in range(OLED_WIDTH):
                intensity = int((x / OLED_WIDTH) * 255)
                screen[:, x] = intensity
        
        elif pattern == "border":
            screen[0, :] = 255
            screen[-1, :] = 255
            screen[:, 0] = 255
            screen[:, -1] = 255
        
        return screen 