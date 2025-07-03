"""
OnBoard OLED Monitor Package
STM32 펌웨어의 OLED 디스플레이 모니터링 도구

Author: OnBoard LED Timer Project
Date: 2024-01-01
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "OnBoard LED Timer Project"
__email__ = "support@onboard-timer.com"
__description__ = "STM32 OLED Display Monitoring Tool"

# 주요 클래스들을 패키지 레벨에서 import 가능하게 함
from .oled_monitor import OLEDMonitor
from .serial_parser import SerialDataParser, ProtocolManager
from .utils import (
    FileManager,
    Logger,
    SerialPortManager,
    ImageProcessor,
    ConfigManager,
    PerformanceMonitor,
    DataBuffer
)

# 패키지의 주요 구성요소들
__all__ = [
    "OLEDMonitor",
    "SerialDataParser", 
    "ProtocolManager",
    "FileManager",
    "Logger",
    "SerialPortManager",
    "ImageProcessor",
    "ConfigManager",
    "PerformanceMonitor",
    "DataBuffer"
] 