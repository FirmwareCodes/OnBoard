# -*- coding: utf-8 -*-
"""
파일 관리자 - 이미지 저장, 로그 관리 등 (간소화)
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np
from PIL import Image
import logging

class FileManager:
    """간소화된 파일 관리자 클래스"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.logger = logging.getLogger(__name__)
        
        # 로그 디렉토리만 관리
        self.log_dir = os.path.join(base_dir, "logs")
        
    def ensure_log_directory(self):
        """로그 디렉토리만 생성"""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"로그 디렉토리 생성 실패: {e}")
    
    def get_unique_filename(self, base_name: str, extension: str = "", directory: str = None) -> str:
        """중복되지 않는 파일명 생성"""
        if directory is None:
            directory = self.base_dir
        
        if not extension.startswith('.') and extension:
            extension = '.' + extension
        
        # 기본 파일명
        filename = f"{base_name}{extension}"
        filepath = os.path.join(directory, filename)
        
        # 중복 검사 및 번호 추가
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base_name}_{counter}{extension}"
            filepath = os.path.join(directory, filename)
            counter += 1
        
        return filepath
    
    def save_image(self, image_data: np.ndarray, filename: str = None, scale: int = 4) -> str:
        """이미지 저장 - 실행 폴더에 바로 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"oled_screen_{timestamp}.png"
            
            # 실행 폴더에 바로 저장
            filepath = self.get_unique_filename(
                os.path.splitext(filename)[0],
                os.path.splitext(filename)[1] or '.png',
                self.base_dir
            )
            
            # numpy 배열을 PIL 이미지로 변환
            if image_data.dtype != np.uint8:
                image_data = image_data.astype(np.uint8)
            
            img = Image.fromarray(image_data, mode='L')
            
            # 스케일링
            if scale > 1:
                new_size = (img.width * scale, img.height * scale)
                img = img.resize(new_size, Image.NEAREST)
            
            # 이미지 저장
            img.save(filepath)
            
            self.logger.info(f"이미지 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"이미지 저장 실패: {e}")
            raise
    
    def save_json(self, data: Dict[str, Any], filename: str = None) -> str:
        """JSON 데이터 저장 - 실행 폴더에 바로 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"session_{timestamp}.json"
            
            # 실행 폴더에 바로 저장
            filepath = self.get_unique_filename(
                os.path.splitext(filename)[0],
                os.path.splitext(filename)[1] or '.json',
                self.base_dir
            )
            
            # JSON 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=self._json_serializer)
            
            self.logger.info(f"JSON 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"JSON 저장 실패: {e}")
            raise
    
    def _json_serializer(self, obj):
        """JSON 직렬화를 위한 커스텀 변환기"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable") 