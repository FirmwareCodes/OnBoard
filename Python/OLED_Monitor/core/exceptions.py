# -*- coding: utf-8 -*-
"""
OLED Monitor 커스텀 예외 클래스
"""

class OLEDMonitorException(Exception):
    """OLED Monitor 기본 예외 클래스"""
    pass

class ConnectionError(OLEDMonitorException):
    """연결 관련 예외"""
    pass

class ParsingError(OLEDMonitorException):
    """파싱 관련 예외"""
    pass

class TimeoutError(OLEDMonitorException):
    """타임아웃 관련 예외"""
    pass

class ValidationError(OLEDMonitorException):
    """데이터 검증 관련 예외"""
    pass

class ConfigurationError(OLEDMonitorException):
    """설정 관련 예외"""
    pass

class SerialCommunicationError(ConnectionError):
    """시리얼 통신 관련 예외"""
    pass

class ScreenDataError(ParsingError):
    """화면 데이터 관련 예외"""
    pass

class StatusDataError(ParsingError):
    """상태 데이터 관련 예외"""
    pass

class LoggingError(OLEDMonitorException):
    """로깅 관련 예외"""
    pass 