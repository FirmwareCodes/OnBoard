# -*- coding: utf-8 -*-
"""
파일 관리자 - 이미지 저장, 로그 관리 등
"""

import os
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
from PIL import Image
import logging

from core.constants import DEFAULT_GRAPHS_DIR, DEFAULT_RUN_DIR

class FileManager:
    """파일 관리자 클래스"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.logger = logging.getLogger(__name__)
        
        # 디렉토리 구조
        self.directories = {
            'graphs': os.path.join(base_dir, DEFAULT_GRAPHS_DIR),
            'logs': os.path.join(base_dir, "logs"),
            'sessions': os.path.join(base_dir, "sessions"),
            'exports': os.path.join(base_dir, "exports"),
            'temp': os.path.join(base_dir, "temp")
        }
        
        # 디렉토리 생성
        self.ensure_directories()
    
    def ensure_directories(self):
        """필요한 디렉토리 생성"""
        for dir_name, dir_path in self.directories.items():
            try:
                os.makedirs(dir_path, exist_ok=True)
                self.logger.debug(f"디렉토리 확인/생성: {dir_path}")
            except Exception as e:
                self.logger.error(f"디렉토리 생성 실패 ({dir_name}): {e}")
    
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
        """이미지 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"oled_screen_{timestamp}.png"
            
            # 파일 경로 생성
            filepath = self.get_unique_filename(
                os.path.splitext(filename)[0],
                os.path.splitext(filename)[1] or '.png',
                self.directories['graphs']
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
    
    def save_json(self, data: Dict[str, Any], filename: str = None, directory: str = None) -> str:
        """JSON 데이터 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"session_{timestamp}.json"
            
            if directory is None:
                directory = self.directories['sessions']
            
            # 파일 경로 생성
            filepath = self.get_unique_filename(
                os.path.splitext(filename)[0],
                os.path.splitext(filename)[1] or '.json',
                directory
            )
            
            # JSON 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=self._json_serializer)
            
            self.logger.info(f"JSON 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"JSON 저장 실패: {e}")
            raise
    
    def load_json(self, filepath: str) -> Dict[str, Any]:
        """JSON 데이터 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"JSON 로드 완료: {filepath}")
            return data
            
        except Exception as e:
            self.logger.error(f"JSON 로드 실패: {e}")
            raise
    
    def save_text(self, text: str, filename: str = None, directory: str = None) -> str:
        """텍스트 파일 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"text_{timestamp}.txt"
            
            if directory is None:
                directory = self.directories['exports']
            
            # 파일 경로 생성
            filepath = self.get_unique_filename(
                os.path.splitext(filename)[0],
                os.path.splitext(filename)[1] or '.txt',
                directory
            )
            
            # 텍스트 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self.logger.info(f"텍스트 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"텍스트 저장 실패: {e}")
            raise
    
    def save_csv(self, data: list, filename: str = None, headers: list = None) -> str:
        """CSV 파일 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"data_{timestamp}.csv"
            
            # 파일 경로 생성
            filepath = self.get_unique_filename(
                os.path.splitext(filename)[0],
                '.csv',
                self.directories['exports']
            )
            
            # CSV 저장
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 헤더 작성
                if headers:
                    writer.writerow(headers)
                
                # 데이터 작성
                writer.writerows(data)
            
            self.logger.info(f"CSV 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"CSV 저장 실패: {e}")
            raise
    
    def create_backup(self, source_file: str, backup_dir: str = None) -> str:
        """파일 백업 생성"""
        try:
            if backup_dir is None:
                backup_dir = os.path.join(self.base_dir, "backups")
                os.makedirs(backup_dir, exist_ok=True)
            
            # 백업 파일명 생성
            source_name = os.path.basename(source_file)
            name, ext = os.path.splitext(source_name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{name}_backup_{timestamp}{ext}"
            
            backup_path = os.path.join(backup_dir, backup_name)
            
            # 파일 복사
            import shutil
            shutil.copy2(source_file, backup_path)
            
            self.logger.info(f"백업 생성 완료: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            raise
    
    def cleanup_old_files(self, directory: str, max_age_days: int = 30, pattern: str = None):
        """오래된 파일 정리"""
        try:
            if not os.path.exists(directory):
                return
            
            import glob
            import time
            
            # 패턴이 없으면 모든 파일
            if pattern is None:
                pattern = "*"
            
            # 파일 목록 가져오기
            file_pattern = os.path.join(directory, pattern)
            files = glob.glob(file_pattern)
            
            # 현재 시간
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            deleted_count = 0
            for file_path in files:
                try:
                    # 파일 수정 시간 확인
                    file_time = os.path.getmtime(file_path)
                    if current_time - file_time > max_age_seconds:
                        os.remove(file_path)
                        deleted_count += 1
                        self.logger.debug(f"오래된 파일 삭제: {file_path}")
                except Exception as e:
                    self.logger.warning(f"파일 삭제 실패: {file_path}, {e}")
            
            if deleted_count > 0:
                self.logger.info(f"오래된 파일 정리 완료: {deleted_count}개 파일 삭제")
            
        except Exception as e:
            self.logger.error(f"파일 정리 실패: {e}")
    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """파일 정보 반환"""
        try:
            if not os.path.exists(filepath):
                return {'exists': False}
            
            stat = os.stat(filepath)
            
            return {
                'exists': True,
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime,
                'is_file': os.path.isfile(filepath),
                'is_directory': os.path.isdir(filepath),
                'basename': os.path.basename(filepath),
                'dirname': os.path.dirname(filepath),
                'extension': os.path.splitext(filepath)[1]
            }
            
        except Exception as e:
            self.logger.error(f"파일 정보 가져오기 실패: {e}")
            return {'exists': False, 'error': str(e)}
    
    def get_directory_size(self, directory: str) -> int:
        """디렉토리 크기 계산"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        pass
            return total_size
            
        except Exception as e:
            self.logger.error(f"디렉토리 크기 계산 실패: {e}")
            return 0
    
    def get_storage_info(self) -> Dict[str, Any]:
        """저장소 정보 반환"""
        try:
            storage_info = {}
            
            for name, path in self.directories.items():
                if os.path.exists(path):
                    # 디렉토리 크기
                    size = self.get_directory_size(path)
                    
                    # 파일 수
                    file_count = sum(len(files) for _, _, files in os.walk(path))
                    
                    storage_info[name] = {
                        'path': path,
                        'size': size,
                        'size_mb': size / (1024 * 1024),
                        'file_count': file_count,
                        'exists': True
                    }
                else:
                    storage_info[name] = {
                        'path': path,
                        'exists': False
                    }
            
            return storage_info
            
        except Exception as e:
            self.logger.error(f"저장소 정보 가져오기 실패: {e}")
            return {}
    
    def _json_serializer(self, obj):
        """JSON 직렬화 헬퍼"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return str(obj)
    
    def export_logs(self, log_directory: str, output_filename: str = None) -> str:
        """로그 파일들을 압축하여 내보내기"""
        try:
            if output_filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"logs_export_{timestamp}.zip"
            
            output_path = os.path.join(self.directories['exports'], output_filename)
            
            import zipfile
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(log_directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, log_directory)
                        zipf.write(file_path, arcname)
            
            self.logger.info(f"로그 내보내기 완료: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"로그 내보내기 실패: {e}")
            raise 