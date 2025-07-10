# -*- coding: utf-8 -*-
"""
설정 관리자 - 애플리케이션 설정을 관리
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from core.interfaces import ConfigInterface
from core.constants import DEFAULT_SCALE, DEFAULT_REFRESH_INTERVAL

class ConfigManager(ConfigInterface):
    """설정 관리자 클래스"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        # 기본 설정
        self.default_config = {
            'display': {
                'scale': DEFAULT_SCALE,
                'border_width': 2,
                'border_color': 128
            },
            'monitoring': {
                'refresh_interval': DEFAULT_REFRESH_INTERVAL,
                'auto_reconnect': True,
                'reconnect_interval': 5.0
            },
            'communication': {
                'baudrate': 921600,  # 기본값을 921600으로 설정
                'timeout': 1.0,
                'auto_detect_port': True
            },
            'logging': {
                'level': 'INFO',
                'max_log_size': 10485760,  # 10MB
                'backup_count': 5
            },
            'performance': {
                'max_samples': 1000,
                'enable_fps_monitoring': True
            }
        }
        
        # 설정 로드
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 기본 설정과 병합
                self.config = self._merge_configs(self.default_config, loaded_config)
                self.logger.info(f"설정 로드 완료: {self.config_file}")
            else:
                # 기본 설정 사용
                self.config = self.default_config.copy()
                self.save_config()  # 기본 설정 파일 생성
                self.logger.info("기본 설정 사용 및 설정 파일 생성")
                
        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
            self.config = self.default_config.copy()
        
        return self.config
    
    def save_config(self, config: Dict[str, Any] = None):
        """설정 저장"""
        try:
            if config is not None:
                self.config = config
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"설정 저장 완료: {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기"""
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            self.logger.error(f"설정 값 가져오기 실패 ({key}): {e}")
            return default
    
    def set(self, key: str, value: Any):
        """설정 값 설정"""
        try:
            keys = key.split('.')
            config = self.config
            
            # 중간 경로 생성
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 값 설정
            config[keys[-1]] = value
            
            # 자동 저장
            self.save_config()
            
        except Exception as e:
            self.logger.error(f"설정 값 설정 실패 ({key}): {e}")
            raise
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정 반환"""
        return self.config.copy()
    
    def reset_to_default(self):
        """기본 설정으로 초기화"""
        self.config = self.default_config.copy()
        self.save_config()
        self.logger.info("설정을 기본값으로 초기화")
    
    def _merge_configs(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """설정 병합"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate_config(self) -> bool:
        """설정 유효성 검증"""
        try:
            # 디스플레이 설정 검증
            scale = self.get('display.scale', DEFAULT_SCALE)
            if not isinstance(scale, int) or scale < 1 or scale > 10:
                self.logger.warning(f"잘못된 스케일 값: {scale}, 기본값으로 설정")
                self.set('display.scale', DEFAULT_SCALE)
            
            # 모니터링 설정 검증
            refresh_interval = self.get('monitoring.refresh_interval', DEFAULT_REFRESH_INTERVAL)
            if not isinstance(refresh_interval, int) or refresh_interval < 50 or refresh_interval > 5000:
                self.logger.warning(f"잘못된 갱신 간격: {refresh_interval}, 기본값으로 설정")
                self.set('monitoring.refresh_interval', DEFAULT_REFRESH_INTERVAL)
            
            # 통신 설정 검증
            baudrate = self.get('communication.baudrate', 115200)
            if not isinstance(baudrate, int) or baudrate <= 0:
                self.logger.warning(f"잘못된 보드레이트: {baudrate}, 기본값으로 설정")
                self.set('communication.baudrate', 115200)
            
            return True
            
        except Exception as e:
            self.logger.error(f"설정 검증 실패: {e}")
            return False
    
    def export_config(self, filename: str = None) -> str:
        """설정을 파일로 내보내기"""
        if filename is None:
            from datetime import datetime
            filename = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"설정 내보내기 완료: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"설정 내보내기 실패: {e}")
            raise
    
    def import_config(self, filename: str) -> bool:
        """설정 파일 가져오기"""
        try:
            if not os.path.exists(filename):
                raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {filename}")
            
            with open(filename, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 기본 설정과 병합
            self.config = self._merge_configs(self.default_config, imported_config)
            
            # 유효성 검증
            if self.validate_config():
                self.save_config()
                self.logger.info(f"설정 가져오기 완료: {filename}")
                return True
            else:
                self.logger.error("가져온 설정이 유효하지 않습니다")
                return False
                
        except Exception as e:
            self.logger.error(f"설정 가져오기 실패: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """설정 정보 반환"""
        try:
            file_info = {}
            if os.path.exists(self.config_file):
                stat = os.stat(self.config_file)
                file_info = {
                    'exists': True,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                }
            else:
                file_info = {'exists': False}
            
            return {
                'config_file': self.config_file,
                'file_info': file_info,
                'config_keys': list(self.config.keys()),
                'total_settings': self._count_settings(self.config)
            }
            
        except Exception as e:
            self.logger.error(f"설정 정보 가져오기 실패: {e}")
            return {}
    
    def _count_settings(self, config: Dict[str, Any]) -> int:
        """설정 항목 수 계산"""
        count = 0
        for value in config.values():
            if isinstance(value, dict):
                count += self._count_settings(value)
            else:
                count += 1
        return count 