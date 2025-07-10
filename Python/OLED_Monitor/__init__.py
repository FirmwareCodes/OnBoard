# -*- coding: utf-8 -*-
"""
OLED Monitor Package
STM32 기반 OLED 모니터링 시스템
"""

__version__ = "2.0.0"
__author__ = "OnBoard Team"
__description__ = "STM32 OLED 모니터링 시스템"

# 핵심 모듈들
from . import core
from . import parsers
from . import utils_enhanced

# 메인 클래스
from .oled_monitor_optimized import OptimizedOLEDMonitor

__all__ = [
    'OptimizedOLEDMonitor',
    'core',
    'parsers', 
    'utils_enhanced'
] 