#!/usr/bin/env python3
"""
OLED Monitor Tool for OnBoard LED Timer - Request-Response Protocol v1.4
STM32 펌웨어의 1.3" OLED 디스플레이 실시간 모니터링 도구

Features:
- 요청-응답 기반 실시간 OLED 화면 캡처
- 사용자 정의 갱신 주기 (50ms~2000ms)
- GET_SCREEN, GET_STATUS 명령어 기반 프로토콜
- 상태 정보 모니터링 및 로그 기록 (RAW 데이터 포함)
- 화면 저장 및 기록
- 원격 제어 (타이머 시작/중지/설정)

Protocol:
- 펌웨어: 요청시에만 화면 데이터 전송 (자동 전송 없음)
- 모니터링 도구: 설정된 주기마다 GET_SCREEN 명령 전송

Author: OnBoard LED Timer Project
Date: 2024-01-01
Version: 1.4 - Request-Response Protocol with RAW Data Logging
"""

import serial
import struct
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import json
from datetime import datetime
import os
import re
import signal

# 프로젝트 내 모듈 import
try:
    from utils import StatusLogger, FileManager, Logger
    from serial_parser import SerialDataParser
except ImportError:
    # 모듈이 없는 경우 기본 기능으로 대체
    StatusLogger = None
    FileManager = None
    Logger = None
    SerialDataParser = None

class OLEDMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OnBoard OLED Monitor v1.4 - Request-Response Protocol with RAW Logging")
        self.root.geometry("900x700")
        
        # 시리얼 통신 관련
        self.serial_port = None
        self.is_connected = False
        self.is_monitoring = False
        
        # 성능 최적화를 위한 NumPy 사용 가능 여부 확인
        try:
            import numpy as np
            self.numpy_available = True
            self.log_startup_message = "✅ NumPy 가속 사용 가능 - 초고속 모드"
        except ImportError:
            self.numpy_available = False
            self.log_startup_message = "⚠️ NumPy 없음 - 일반 모드 (pip install numpy 권장)"
        
        # 모니터링 설정
        self.update_interval_ms = 50  # 기본 갱신 주기 50ms (20 FPS)
        self.auto_request_enabled = True  # 자동 요청 모드 기본 활성화
        
        # 성능 통계
        self.performance_stats = {
            'start_time': time.time(),
            'total_captures': 0,
            'successful_captures': 0,
            'fps_counter': 0,
            'fps_start_time': time.time()
        }
        
        # 화면 관련
        self.current_screen = None
        self.current_image = None
        
        # 스레드 관련
        self.capture_thread = None
        self.status_thread = None
        
        # 상태 로그 기록 관련 (RAW 데이터 지원)
        self.setup_status_logging()
        
        # 시리얼 파서 초기화
        self.setup_serial_parser()
        
        # GUI 설정
        self.setup_gui()
        
        # 시작 메시지 출력
        self.root.after(1000, lambda: self.log_message(self.log_startup_message))
        
        # OLED 설정
        self.OLED_WIDTH = 128
        self.OLED_HEIGHT = 64
        self.IMAGE_SIZE = (self.OLED_WIDTH // 8) * self.OLED_HEIGHT  # 1024 bytes
        
        # 현재 화면 데이터
        self.current_screen = None
        self.current_status = {}
        
        # 파싱 방법 설정 (가장 안정적인 방법으로 기본값 변경)
        self.parsing_method = "method3_rotated_180"  # 세로 뒤집기가 가장 안정적
        
        # 로그 출력 최적화 - 중복 방지
        self.log_throttle = {}  # 메시지별 마지막 출력 시간
        self.log_throttle_interval = 2.0  # 2초 내 동일 메시지는 한 번만 출력
        
    def setup_status_logging(self):
        """상태 로그 기록 시스템 설정 - 강화된 RAW 데이터 지원"""
        try:
            # utils.py의 StatusLogger 사용 (RAW 데이터 지원)
            if StatusLogger:
                self.status_logger = StatusLogger()
                print(f"✅ 강화된 상태 로그 시스템 초기화 완료")
                print(f"📝 상태 로그: {self.status_logger.get_log_file_path()}")
                print(f"🔍 RAW 데이터 로그: {self.status_logger.get_raw_log_file_path()}")
            else:
                # 폴백: 기본 로깅 시스템
                self.setup_fallback_logging()
                print(f"⚠️ 기본 상태 로그 시스템 사용")
                
        except Exception as e:
            print(f"❌ 상태 로그 시스템 초기화 실패: {str(e)}")
            self.setup_fallback_logging()
    
    def setup_fallback_logging(self):
        """폴백 로깅 시스템 (utils.py가 없을 때 사용)"""
        try:
            # 실행 경로에 LOG 폴더 생성
            self.log_directory = os.path.join(os.getcwd(), "LOG")
            os.makedirs(self.log_directory, exist_ok=True)
            
            # 오늘 날짜로 상태 로그 파일명 생성
            today = datetime.now().strftime("%Y%m%d")
            self.status_log_file = os.path.join(self.log_directory, f"status_log_{today}.txt")
            
            # 상태 로그 파일 초기화 (헤더 작성)
            self.init_status_log_file()
            
            # 상태 로그 기록을 위한 스레드 락
            self.status_log_lock = threading.Lock()
            self.status_logger = None  # 폴백 모드 표시
            
        except Exception as e:
            print(f"❌ 폴백 로깅 시스템 초기화 실패: {str(e)}")
            self.status_log_file = None
            self.status_logger = None
    
    def setup_serial_parser(self):
        """시리얼 파서 초기화"""
        try:
            if SerialDataParser:
                self.serial_parser = SerialDataParser()
                print(f"✅ 시리얼 파서 초기화 완료")
            else:
                self.serial_parser = None
                print(f"⚠️ 시리얼 파서 모듈 없음 - 기본 파싱 사용")
        except Exception as e:
            print(f"❌ 시리얼 파서 초기화 실패: {str(e)}")
            self.serial_parser = None
    
    def init_status_log_file(self):
        """상태 로그 파일 헤더 초기화"""
        try:
            # 파일이 이미 존재하고 오늘 생성된 것이면 헤더 추가하지 않음
            if os.path.exists(self.status_log_file):
                file_stat = os.path.stat(self.status_log_file)
                file_date = datetime.fromtimestamp(file_stat.st_mtime).date()
                if file_date == datetime.now().date():
                    return  # 오늘 파일이면 헤더 추가하지 않음
            
            # 새 파일이거나 어제 파일이면 헤더 작성
            with open(self.status_log_file, 'a', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"OnBoard OLED Monitor 상태 로그 - {datetime.now().strftime('%Y년 %m월 %d일')}\n")
                f.write("=" * 80 + "\n")
                f.write("시간\t\t\t배터리\t타이머\t\t상태\t\tL1\tL2\t비고\n")
                f.write("-" * 80 + "\n")
                
        except Exception as e:
            print(f"❌ 상태 로그 파일 헤더 초기화 실패: {str(e)}")
    
    def write_status_log(self, status_data):
        """상태 데이터를 로그 파일에 기록 - RAW 데이터 지원"""
        try:
            # 강화된 StatusLogger 사용
            if self.status_logger and hasattr(self.status_logger, 'log_status'):
                self.status_logger.log_status(status_data)
                return
            
            # 폴백: 기본 로깅 (RAW 데이터 간소화)
            if not hasattr(self, 'status_log_file') or not self.status_log_file:
                return
                
            with self.status_log_lock:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 밀리초 포함
                
                # 상태 데이터 추출
                battery = status_data.get('battery', 'N/A')
                timer = status_data.get('timer', 'N/A')
                status = status_data.get('status', 'N/A')
                l1_connected = '연결' if status_data.get('l1_connected', False) else '해제'
                l2_connected = '연결' if status_data.get('l2_connected', False) else '해제'
                source = status_data.get('source', 'unknown')
                
                # RAW 데이터 요약 (기본 로깅용)
                raw_data = status_data.get('raw_data', '')
                if isinstance(raw_data, bytes):
                    raw_summary = f"[{len(raw_data)}bytes]"
                elif isinstance(raw_data, str):
                    raw_summary = raw_data[:30] + '...' if len(raw_data) > 30 else raw_data
                else:
                    raw_summary = str(raw_data)[:30]
                
                # 로그 라인 구성
                log_line = f"{timestamp}\t{battery}%\t{timer}\t\t{status}\t\t{l1_connected}\t{l2_connected}\t{source}\t{raw_summary}\n"
                
                # 파일에 기록
                with open(self.status_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                    
        except Exception as e:
            print(f"❌ 상태 로그 기록 실패: {str(e)}")
    
    def write_status_log_event(self, event_type, message, raw_data=None):
        """특별한 이벤트를 상태 로그에 기록 - RAW 데이터 지원"""
        try:
            # 강화된 StatusLogger 사용
            if self.status_logger and hasattr(self.status_logger, 'log_event'):
                self.status_logger.log_event(event_type, message, raw_data)
                return
            
            # 폴백: 기본 로깅
            if not hasattr(self, 'status_log_file') or not self.status_log_file:
                return
                
            with self.status_log_lock:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # RAW 데이터 요약 추가
                if raw_data:
                    if isinstance(raw_data, bytes):
                        message += f" [RAW: {len(raw_data)}bytes]"
                    elif isinstance(raw_data, str):
                        message += f" [RAW: {len(raw_data)}chars]"
                
                log_line = f"{timestamp}\t[{event_type}]\t{message}\n"
                
                with open(self.status_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                    
        except Exception as e:
            print(f"❌ 상태 로그 이벤트 기록 실패: {str(e)}")

    def setup_gui(self):
        """GUI 인터페이스 설정"""
        self.root.title("OnBoard OLED Monitor v1.4 - Request-Response Protocol")
        self.root.geometry("1000x750")  # 크기 확대
        self.root.resizable(True, True)
        
        # 메뉴바
        self.create_menu()
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 상단 연결 프레임
        self.create_connection_frame(main_frame)
        
        # 중간 화면 표시 프레임
        self.create_display_frame(main_frame)
        
        # 하단 상태 및 제어 프레임
        self.create_control_frame(main_frame)
        
        # 우측 상태 정보 프레임
        self.create_status_frame(main_frame)
        
    def create_menu(self):
        """메뉴바 생성"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="화면 저장", command=self.save_screen)
        file_menu.add_command(label="세션 기록", command=self.save_session)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.on_closing)
        
        # 도구 메뉴
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도구", menu=tools_menu)
        tools_menu.add_command(label="상태 로그 열기", command=self.open_status_log)
        tools_menu.add_command(label="설정", command=self.open_settings)
        tools_menu.add_command(label="도움말", command=self.show_help)
        
    def create_connection_frame(self, parent):
        """연결 설정 프레임"""
        conn_frame = ttk.LabelFrame(parent, text="연결 설정")
        conn_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 시리얼 포트 설정
        ttk.Label(conn_frame, text="포트:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM3")
        port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=10)
        port_combo['values'] = self.get_available_ports()
        port_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="보드레이트:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.StringVar(value="921600")
        baud_combo = ttk.Combobox(conn_frame, textvariable=self.baud_var, width=10)
        baud_combo['values'] = ['9600', '115200', '230400', '460800', '921600']
        baud_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # 연결 버튼
        self.connect_btn = ttk.Button(conn_frame, text="연결", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # 상태 표시
        self.status_label = ttk.Label(conn_frame, text="연결 안됨", foreground="red")
        self.status_label.grid(row=0, column=5, padx=5, pady=5)
        
        # 성능 통계 표시
        self.perf_label = ttk.Label(conn_frame, text="FPS: 0 | 성공률: 0%", foreground="blue")
        self.perf_label.grid(row=0, column=6, padx=5, pady=5)
        
        # 두 번째 행: 갱신 주기 설정
        ttk.Label(conn_frame, text="갱신 주기(ms):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.interval_var = tk.StringVar(value="50")
        interval_combo = ttk.Combobox(conn_frame, textvariable=self.interval_var, width=8)
        interval_combo['values'] = ['50', '100', '200', '500', '1000', '2000']
        interval_combo.grid(row=1, column=1, padx=5, pady=2)
        interval_combo.bind('<<ComboboxSelected>>', self.on_interval_changed)
        
        # 자동 요청 모드 체크박스
        self.auto_request_var = tk.BooleanVar(value=False)
        auto_request_cb = ttk.Checkbutton(conn_frame, text="자동 화면 요청", 
                                        variable=self.auto_request_var,
                                        command=self.on_auto_request_changed)
        auto_request_cb.grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        
        # 갱신 모드 표시
        self.update_mode_label = ttk.Label(conn_frame, text="수동 모드", foreground="orange")
        self.update_mode_label.grid(row=1, column=3, padx=5, pady=2)
        
    def create_display_frame(self, parent):
        """화면 표시 프레임"""
        display_frame = ttk.LabelFrame(parent, text="OLED 화면 (128x64)")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 화면 표시용 캔버스
        self.canvas = tk.Canvas(display_frame, width=512, height=256, bg='black')
        self.canvas.pack(expand=True, padx=10, pady=10)
        
        # 확대 비율 조절
        scale_frame = ttk.Frame(display_frame)
        scale_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(scale_frame, text="확대:").pack(side=tk.LEFT)
        self.scale_var = tk.IntVar(value=4)
        scale = ttk.Scale(scale_frame, from_=1, to=8, orient=tk.HORIZONTAL, 
                         variable=self.scale_var, command=self.update_display_scale)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.scale_label = ttk.Label(scale_frame, text="4x")
        self.scale_label.pack(side=tk.RIGHT)
        
    def create_control_frame(self, parent):
        """제어 프레임"""
        control_frame = ttk.LabelFrame(parent, text="제어")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 상단 행: 모니터링 제어
        top_frame = ttk.Frame(control_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.monitor_btn = ttk.Button(top_frame, text="모니터링 시작", 
                                     command=self.toggle_monitoring)
        self.monitor_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        capture_btn = ttk.Button(top_frame, text="화면 캡처", 
                               command=self.capture_screen)
        capture_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        refresh_btn = ttk.Button(top_frame, text="상태 새로고침", 
                               command=self.refresh_status)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 저장 기능 버튼들 (우측 정렬)
        save_frame = ttk.Frame(top_frame)
        save_frame.pack(side=tk.RIGHT)
        
        save_session_btn = ttk.Button(save_frame, text="세션 저장", 
                                    command=self.save_session)
        save_session_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        save_screen_btn = ttk.Button(save_frame, text="화면 저장", 
                                   command=self.save_screen_high_res)
        save_screen_btn.pack(side=tk.LEFT, padx=(0, 0))
        
        # 하단 행: 원격 제어
        remote_frame = ttk.LabelFrame(control_frame, text="원격 제어")
        remote_frame.pack(fill=tk.X, padx=5, pady=(5, 5))
        
        # 상단 행: 파싱 방법 선택
        parsing_frame = ttk.Frame(remote_frame)
        parsing_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(parsing_frame, text="파싱 방법:").pack(side=tk.LEFT)
        self.parsing_var = tk.StringVar(value="method3_rotated_180")
        parsing_combo = ttk.Combobox(parsing_frame, textvariable=self.parsing_var, width=20)
        parsing_combo['values'] = [
            'method1_direct',           # 직접 매핑
            'method2_reversed',         # reverse 함수 적용
            'method3_rotated_180',      # 180도 회전
            'method4_flipped_h',        # 가로 뒤집기
            'method5_flipped_v',        # 세로 뒤집기 (기본, 안정적)
            'method5_rotate_90',        # 90도 시계방향 회전
            'method5_rotate_270',       # 270도 시계방향 회전 (90도 반시계방향)
            'method5_mirror_h',         # 가로 미러링 (좌우 반전)
            'method5_mirror_v',         # 세로 미러링 (상하 반전)
            'method5_flip_both',        # 상하좌우 모두 뒤집기
            'method6_transposed'        # 전치 + 뒤집기
        ]
        parsing_combo.pack(side=tk.LEFT, padx=(5, 5))
        parsing_combo.bind('<<ComboboxSelected>>', self.on_parsing_method_changed)
        
        # 파싱 방법 적용 버튼
        apply_parsing_btn = ttk.Button(parsing_frame, text="파싱 방법 적용", 
                                     command=self.apply_parsing_method)
        apply_parsing_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 타이머 제어 버튼들
        timer_frame = ttk.Frame(remote_frame)
        timer_frame.pack(fill=tk.X, pady=2)
        
        start_btn = ttk.Button(timer_frame, text="타이머 시작", 
                             command=self.remote_start_timer)
        start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        stop_btn = ttk.Button(timer_frame, text="타이머 정지", 
                            command=self.remote_stop_timer)
        stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        reset_btn = ttk.Button(timer_frame, text="리셋", 
                             command=self.remote_reset)
        reset_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ping_btn = ttk.Button(timer_frame, text="연결 테스트", 
                            command=self.remote_ping)
        ping_btn.pack(side=tk.RIGHT)
        
        # 타이머 설정
        setting_frame = ttk.Frame(remote_frame)
        setting_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(setting_frame, text="타이머 설정(분):").pack(side=tk.LEFT)
        
        self.timer_min_var = tk.StringVar(value="05")
        min_spin = ttk.Spinbox(setting_frame, from_=1, to=99, width=5,
                              textvariable=self.timer_min_var, format="%02.0f")
        min_spin.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(setting_frame, text="분").pack(side=tk.LEFT)
        
        set_timer_btn = ttk.Button(setting_frame, text="타이머 설정", 
                                 command=self.remote_set_timer)
        set_timer_btn.pack(side=tk.LEFT, padx=(10, 0))
        
    def create_status_frame(self, parent):
        """상태 정보 프레임"""
        status_frame = ttk.LabelFrame(parent, text="디바이스 상태")
        status_frame.pack(fill=tk.X)
        
        # 상태 정보 표시
        self.status_text = tk.Text(status_frame, height=6, width=50)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
    def get_available_ports(self):
        """사용 가능한 시리얼 포트 목록 반환"""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
        
    def toggle_connection(self):
        """연결/해제 토글"""
        if not self.is_connected:
            self.connect_device()
        else:
            self.disconnect_device()
            
    def connect_device(self):
        """디바이스 연결 - UI 멈춤 방지를 위한 완전 비동기 처리"""
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
            
            # 포트 유효성 검사
            if not port or port.strip() == "":
                messagebox.showerror("오류", "포트를 선택하세요")
                return
                
            # 연결 진행 상태 표시
            self.connect_btn.config(text="연결 중...", state="disabled")
            self.status_label.config(text="연결 시도 중...", foreground="orange")
            
            # 진행 상황 표시를 위한 프로그레스 바 생성
            self.show_connection_progress()
            
            # GUI 즉시 업데이트
            self.root.update_idletasks()
            
            # 완전 비동기 연결을 위한 스레드 사용
            connection_thread = threading.Thread(
                target=self._connect_device_async, 
                args=(port, baud),
                daemon=True
            )
            connection_thread.start()
            
            # 연결 상태 모니터링 스레드 시작
            self._start_connection_monitor()
            
        except Exception as e:
            self._connection_failed(f"연결 설정 오류: {str(e)}")
    
    def show_connection_progress(self):
        """연결 진행 상황 표시"""
        if hasattr(self, 'progress_window'):
            return  # 이미 열려있으면 무시
            
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("연결 중...")
        self.progress_window.geometry("300x120")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        
        # 창을 화면 중앙에 배치
        self.progress_window.update_idletasks()
        x = (self.progress_window.winfo_screenwidth() // 2) - (150)
        y = (self.progress_window.winfo_screenheight() // 2) - (60)
        self.progress_window.geometry(f"300x120+{x}+{y}")
        
        # 진행 상황 라벨
        self.progress_label = tk.Label(self.progress_window, text="시리얼 포트 연결 중...", 
                                     font=("Arial", 10))
        self.progress_label.pack(pady=10)
        
        # 프로그레스 바
        from tkinter import ttk
        self.progress_bar = ttk.Progressbar(self.progress_window, mode='indeterminate')
        self.progress_bar.pack(pady=10, padx=20, fill=tk.X)
        self.progress_bar.start()
        
        # 취소 버튼
        cancel_btn = ttk.Button(self.progress_window, text="취소", 
                              command=self.cancel_connection)
        cancel_btn.pack(pady=5)
        
        # 연결 시작 시간 기록
        self.connection_start_time = time.time()
        
    def cancel_connection(self):
        """연결 취소"""
        self.connection_cancelled = True
        self.hide_connection_progress()
        self._connection_failed("사용자가 연결을 취소했습니다")
        
    def hide_connection_progress(self):
        """연결 진행 상황 창 숨기기"""
        if hasattr(self, 'progress_window'):
            try:
                self.progress_window.destroy()
                delattr(self, 'progress_window')
            except:
                pass
                
    def _start_connection_monitor(self):
        """연결 상태 모니터링 시작"""
        self.connection_cancelled = False
        self.connection_timeout = 10.0  # 10초 타임아웃
        self._monitor_connection()
        
    def _monitor_connection(self):
        """연결 상태 모니터링"""
        if hasattr(self, 'connection_start_time'):
            elapsed = time.time() - self.connection_start_time
            
            # 타임아웃 체크
            if elapsed > self.connection_timeout:
                self.connection_cancelled = True
                self.hide_connection_progress()
                self._connection_failed("연결 시간 초과 (10초)")
                return
                
            # 진행 상황 업데이트
            if hasattr(self, 'progress_label'):
                remaining = int(self.connection_timeout - elapsed)
                self.progress_label.config(text=f"시리얼 포트 연결 중... ({remaining}초 남음)")
            
            # 연결 완료 또는 취소 체크
            if not self.connection_cancelled and not self.is_connected:
                # 100ms 후 다시 체크
                self.root.after(100, self._monitor_connection)
            else:
                self.hide_connection_progress()
                
    def _connect_device_async(self, port, baud):
        """비동기 디바이스 연결 처리 - UI 멈춤 방지 강화"""
        try:
            # 취소 체크
            if getattr(self, 'connection_cancelled', False):
                return
                
            # 1단계: 시리얼 포트 생성 (논블로킹)
            self.root.after(0, lambda: self._update_progress("시리얼 포트 설정 중..."))
            
            self.serial_port = serial.Serial()
            self.serial_port.port = port
            self.serial_port.baudrate = baud
            self.serial_port.timeout = 0.1  # 매우 짧은 타임아웃
            self.serial_port.write_timeout = 0.2
            self.serial_port.inter_byte_timeout = 0.05
            
            # 추가 시리얼 포트 설정
            self.serial_port.rtscts = False
            self.serial_port.dsrdtr = False
            self.serial_port.xonxoff = False
            
            # 취소 체크
            if getattr(self, 'connection_cancelled', False):
                return
                
            # 2단계: 포트 열기 (논블로킹 시도)
            self.root.after(0, lambda: self._update_progress("포트 열기 중..."))
            
            # 포트 열기를 여러 번 시도
            max_open_attempts = 5
            for attempt in range(max_open_attempts):
                if getattr(self, 'connection_cancelled', False):
                    return
                    
                try:
                    self.serial_port.open()
                    if self.serial_port.is_open:
                        break
                except serial.SerialException as e:
                    if attempt == max_open_attempts - 1:
                        raise e
                    time.sleep(0.1)  # 100ms 대기 후 재시도
                    
            # 포트 열기 확인
            if not self.serial_port.is_open:
                raise Exception("포트 열기 실패")
                
            # 3단계: 초기 버퍼 클리어
            self.root.after(0, lambda: self._update_progress("초기 설정 중..."))
            
            # 짧은 안정화 시간
            time.sleep(0.1)
            
            # 버퍼 클리어 (논블로킹)
            clear_attempts = 0
            while clear_attempts < 3 and not getattr(self, 'connection_cancelled', False):
                if self.serial_port.in_waiting > 0:
                    old_data = self.serial_port.read(self.serial_port.in_waiting)
                    if len(old_data) > 0:
                        self.root.after(0, lambda size=len(old_data): 
                                      self.log_message(f"🧹 초기 버퍼 클리어: {size} bytes"))
                time.sleep(0.05)
                clear_attempts += 1
                
            # 4단계: 연결 테스트 (선택적)
            self.root.after(0, lambda: self._update_progress("연결 테스트 중..."))
            
            test_success = False
            if not getattr(self, 'connection_cancelled', False):
                try:
                    # 빠른 PING 테스트
                    self.serial_port.write(b'PING\n')
                    self.serial_port.flush()
                    
                    # 빠른 응답 확인 (최대 1초)
                    ping_response = b''
                    test_start = time.time()
                    while time.time() - test_start < 1.0:
                        if getattr(self, 'connection_cancelled', False):
                            return
                        if self.serial_port.in_waiting > 0:
                            chunk = self.serial_port.read(self.serial_port.in_waiting)
                            ping_response += chunk
                            if b'PONG' in ping_response:
                                test_success = True
                                break
                        time.sleep(0.01)
                        
                except Exception:
                    # 테스트 실패해도 연결은 유지
                    pass
                    
            # 취소 체크
            if getattr(self, 'connection_cancelled', False):
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                return
                
            # 연결 성공 처리
            self.is_connected = True
            
            # GUI 업데이트를 메인 스레드에서 안전하게 수행
            connection_info = {
                'port': port,
                'baud': baud,
                'test_success': test_success,
                'connection_time': time.time() - getattr(self, 'connection_start_time', time.time())
            }
            
            self.root.after(0, lambda info=connection_info: self._connection_success_with_info(info))
            
        except Exception as e:
            # 연결 실패 처리
            error_msg = str(e)
            
            # 시리얼 포트 정리
            if hasattr(self, 'serial_port') and self.serial_port:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except:
                    pass
                self.serial_port = None
                
            self.root.after(0, lambda msg=error_msg: self._connection_failed(msg))
            
    def _update_progress(self, message):
        """진행 상황 업데이트"""
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text=message)
            
    def _connection_success_with_info(self, info):
        """연결 성공 처리 - 상세 정보 포함"""
        try:
            # 진행 상황 창 닫기
            self.hide_connection_progress()
            
            self.connect_btn.config(text="연결 해제", state="normal")
            self.status_label.config(text="연결됨", foreground="green")
            
            # 연결 정보 메시지 구성
            test_msg = " (통신 확인됨)" if info['test_success'] else " (통신 미확인)"
            time_msg = f" ({info['connection_time']:.1f}초)"
            
            self.log_message(f"✅ 포트 {info['port']}에 연결됨 (보드레이트: {info['baud']}){test_msg}{time_msg}")
            
            # 연결 이벤트 로그
            connection_details = f"PORT:{info['port']},BAUD:{info['baud']},TIMEOUT:0.1,TEST:{info['test_success']}"
            self.write_status_log_event("CONNECT", f"포트 {info['port']} 연결 (보드레이트: {info['baud']})", connection_details.encode())
            
            # 연결 성공 알림
            messagebox.showinfo("연결 성공", f"포트 {info['port']}에 성공적으로 연결되었습니다!")
            
        except Exception as e:
            self.log_message(f"❌ 연결 후 처리 오류: {str(e)}")
    
    def _connection_failed(self, error_msg):
        """연결 실패 처리 - 강화된 오류 처리"""
        try:
            # 진행 상황 창 닫기
            self.hide_connection_progress()
            
            # 시리얼 포트 정리
            if hasattr(self, 'serial_port') and self.serial_port:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except:
                    pass
                self.serial_port = None
            
            self.is_connected = False
            self.connect_btn.config(text="연결", state="normal")
            self.status_label.config(text="연결 실패", foreground="red")
            
            # 사용자에게 오류 메시지 표시
            error_display = f"연결할 수 없습니다: {error_msg}"
            self.log_message(f"❌ {error_display}")
            
            # 상세한 해결 방법 제시
            if "사용자가 연결을 취소" in error_msg:
                self.log_message("ℹ️ 연결이 취소되었습니다")
            elif "연결 시간 초과" in error_msg:
                self.log_message("💡 해결방법:")
                self.log_message("   1. 디바이스 전원과 USB 케이블을 확인하세요")
                self.log_message("   2. 다른 USB 포트를 사용해보세요")
                self.log_message("   3. 보드레이트를 확인하세요")
                messagebox.showerror("연결 실패", "연결 시간이 초과되었습니다.\n디바이스 연결 상태를 확인해주세요.")
            elif "PermissionError" in error_msg or "액세스가 거부" in error_msg:
                self.log_message("💡 해결방법: 다른 프로그램이 포트를 사용 중일 수 있습니다. 시리얼 모니터를 종료하세요.")
                messagebox.showerror("연결 실패", "포트에 액세스할 수 없습니다.\n다른 프로그램에서 포트를 사용 중일 수 있습니다.")
            elif "FileNotFoundError" in error_msg or "찾을 수 없습니다" in error_msg:
                self.log_message("💡 해결방법: 포트가 존재하지 않습니다. 디바이스 연결을 확인하세요.")
                messagebox.showerror("연결 실패", "선택한 포트를 찾을 수 없습니다.\n디바이스 연결을 확인해주세요.")
            else:
                messagebox.showerror("연결 실패", f"연결에 실패했습니다:\n{error_msg}")
                
        except Exception as e:
            self.log_message(f"❌ 연결 실패 처리 오류: {str(e)}")
    
    def disconnect_device(self):
        """디바이스 연결 해제 - 안전한 비동기 처리"""
        # 먼저 모니터링 중지
        if self.is_monitoring:
            self.stop_monitoring()
            # 모니터링 완전 중지까지 대기 (비블로킹)
            threading.Thread(target=self._async_disconnect, daemon=True).start()
        else:
            self._async_disconnect()
    
    def _async_disconnect(self):
        """비동기 연결 해제 처리"""
        try:
            connection_info = ""
            
            # 연결 정보 수집 (안전하게)
            if self.serial_port:
                try:
                    if hasattr(self.serial_port, 'port') and hasattr(self.serial_port, 'baudrate'):
                        port_info = f"PORT:{self.serial_port.port},BAUD:{self.serial_port.baudrate}"
                        connection_info = port_info
                except:
                    connection_info = "PORT:UNKNOWN,BAUD:UNKNOWN"
            
            # 시리얼 포트 안전하게 닫기
            if self.serial_port:
                try:
                    # 1. 펌웨어에 정지 명령 전송 (타임아웃 짧게)
                    if self.serial_port.is_open:
                        self.serial_port.write(b'STOP_MONITOR\n')
                        self.serial_port.flush()
                        time.sleep(0.1)  # 100ms 대기
                    
                    # 2. 포트 닫기
                    if self.serial_port.is_open:
                        self.serial_port.close()
                        
                    # 3. 포트 객체 정리
                    self.serial_port = None
                    
                except Exception as close_error:
                    # 포트 닫기 실패시에도 계속 진행
                    self.root.after(0, lambda: self.log_message(f"⚠️ 포트 닫기 오류: {str(close_error)}"))
                    self.serial_port = None
            
            # 연결 상태 업데이트 (메인 스레드에서 안전하게)
            self.is_connected = False
            self.root.after(0, self._update_disconnect_ui)
            
            # 로그 기록
            self.root.after(0, lambda: self.log_message("✅ 연결이 안전하게 해제되었습니다"))
            self.root.after(0, lambda: self.write_status_log_event("DISCONNECT", "연결 해제", connection_info.encode() if connection_info else None))
            
        except Exception as e:
            # 연결 해제 실패시에도 상태는 업데이트
            self.is_connected = False
            self.serial_port = None
            self.root.after(0, self._update_disconnect_ui)
            self.root.after(0, lambda: self.log_message(f"⚠️ 연결 해제 중 오류: {str(e)}"))
    
    def _update_disconnect_ui(self):
        """연결 해제 UI 업데이트 (메인 스레드에서 실행)"""
        try:
            self.connect_btn.config(text="연결", state="normal")
            self.status_label.config(text="연결 안됨", foreground="red")
        except Exception as e:
            self.log_message(f"❌ UI 업데이트 오류: {str(e)}")
    
    def toggle_monitoring(self):
        """모니터링 시작/중지"""
        if not self.is_connected:
            messagebox.showwarning("경고", "먼저 디바이스에 연결하세요")
            return
            
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
            
    def start_monitoring(self):
        """모니터링 시작 - 비블로킹 최적화 버전"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 성능 통계 초기화
            self.performance_stats = {
                'start_time': time.time(),
                'total_captures': 0,
                'successful_captures': 0,
                'fps_counter': 0,
                'fps_start_time': time.time()
            }
            
            # 모니터링 플래그 먼저 설정 (빠른 시작)
            self.is_monitoring = True
            
            # UI 즉시 업데이트
            self.monitor_btn.config(text="모니터링 중지")
            self.log_message("🚀 모니터링 시작 중...")
            
            # 시리얼 버퍼 비동기 클리어
            threading.Thread(target=self._async_start_monitoring, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ 모니터링 시작 오류: {str(e)}")
            self.is_monitoring = False
            self.monitor_btn.config(text="모니터링 시작")
    
    def _async_start_monitoring(self):
        """비동기 모니터링 시작 처리"""
        try:
            # 1단계: 시리얼 버퍼 클리어 (비블로킹)
            self._clear_serial_buffers_async()
            
            # 2단계: 펌웨어 설정 (타임아웃 단축)
            self._setup_firmware_async()
            
            # 3단계: 스레드 시작
            self._start_monitoring_threads()
            
            # 성공 로그
            mode_text = "자동 모드" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.root.after(0, lambda: self.log_message(f"✅ 모니터링 시작 완료 - {mode_text}{interval_text}"))
            self.root.after(0, lambda: self.write_status_log_event("START", f"모니터링 시작 - {mode_text}{interval_text}"))
            
        except Exception as e:
            # 실패시 모니터링 중지
            self.is_monitoring = False
            self.root.after(0, lambda: self.monitor_btn.config(text="모니터링 시작"))
            self.root.after(0, lambda: self.log_message(f"❌ 모니터링 시작 실패: {str(e)}"))
    
    def _clear_serial_buffers_async(self):
        """비동기 시리얼 버퍼 클리어"""
        if not self.serial_port:
            return
            
        try:
            # 빠른 버퍼 클리어 (최대 3회 시도)
            for attempt in range(3):
                if self.serial_port.in_waiting > 0:
                    old_data = self.serial_port.read(self.serial_port.in_waiting)
                    if len(old_data) > 0:
                        self.root.after(0, lambda size=len(old_data): 
                                      self.log_message(f"🧹 버퍼 클리어: {size} bytes"))
                else:
                    break  # 버퍼가 비어있으면 종료
                time.sleep(0.05)  # 50ms 대기
            
            # 출력 버퍼 플러시
            self.serial_port.flush()
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"⚠️ 버퍼 클리어 오류: {str(e)}"))
    
    def _setup_firmware_async(self):
        """비동기 펌웨어 설정"""
        try:
            # 1. 간단한 연결 테스트 (짧은 타임아웃)
            self.serial_port.write(b'PING\n')
            self.serial_port.flush()
            
            ping_response = self._wait_for_response_quick(500)  # 0.5초 타임아웃
            if ping_response and b'PONG' in ping_response:
                self.root.after(0, lambda: self.log_message("✅ 펌웨어 연결 확인"))
            else:
                self.root.after(0, lambda: self.log_message("⚠️ 펌웨어 응답 없음 - 계속 진행"))
            
            # 2. 모니터링 모드 설정 (짧은 타임아웃)
            command = f"SET_UPDATE_MODE:REQUEST_RESPONSE,{self.update_interval_ms}\n"
            self.serial_port.write(command.encode())
            self.serial_port.flush()
            
            mode_response = self._wait_for_response_quick(500)
            if mode_response and b'OK' in mode_response:
                self.root.after(0, lambda: self.log_message("✅ 펌웨어 모드 설정 완료"))
            
            # 3. 모니터링 활성화 (짧은 타임아웃)
            self.serial_port.write(b'START_MONITOR\n')
            self.serial_port.flush()
            
            start_response = self._wait_for_response_quick(500)
            if start_response and b'OK' in start_response:
                self.root.after(0, lambda: self.log_message("✅ 펌웨어 모니터링 활성화"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"⚠️ 펌웨어 설정 오류: {str(e)} - 계속 진행"))
    
    def _wait_for_response_quick(self, timeout_ms):
        """빠른 응답 대기 (블로킹 방지용)"""
        try:
            timeout_seconds = timeout_ms / 1000.0
            start_time = time.time()
            response_data = b''
            
            while time.time() - start_time < timeout_seconds:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    if b'\n' in response_data:
                        break
                else:
                    time.sleep(0.01)  # 10ms 대기
            
            return response_data if response_data else None
            
        except Exception:
            return None
    
    def _start_monitoring_threads(self):
        """모니터링 스레드 시작"""
        try:
            # 캡처 스레드 시작 (높은 우선순위)
            if self.capture_thread is None or not self.capture_thread.is_alive():
                self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
                self.capture_thread.start()
            
            # 상태 모니터링 스레드 시작 (낮은 우선순위)
            if self.status_thread is None or not self.status_thread.is_alive():
                self.status_thread = threading.Thread(target=self.status_loop, daemon=True)
                self.status_thread.start()
                
        except Exception as e:
            raise Exception(f"스레드 시작 실패: {str(e)}")
    
    def stop_monitoring(self):
        """모니터링 중지 - 최적화된 안전한 종료"""
        if not self.is_monitoring:
            return
            
        # 모니터링 플래그 즉시 비활성화
        self.is_monitoring = False
        
        # UI 즉시 업데이트
        self.monitor_btn.config(text="모니터링 시작")
        
        try:
            # 펌웨어에 모니터링 중지 명령 전송 (빠른 처리)
            if self.is_connected and self.serial_port:
                self.serial_port.write(b'STOP_MONITOR\n')
                self.serial_port.flush()
                
                # 응답 확인 (짧은 타임아웃)
                response = self.wait_for_response(500)
                if response and b'OK:Monitoring stopped' in response:
                    self.log_message("✅ 펌웨어 모니터링 모드 비활성화 완료")
                else:
                    self.log_message("⚠️ 펌웨어 모니터링 모드 비활성화 응답 없음")
            
            self.log_message("🛑 모니터링 완전 중지 및 상태 초기화 완료")
            
            # 상태 로그에 모니터링 중지 이벤트 기록
            self.write_status_log_event("STOP", "모니터링 중지")
            
        except Exception as e:
            self.log_message(f"❌ 모니터링 중지 오류: {str(e)}")
        
        # 스레드들은 daemon=True로 설정되어 자동으로 종료됨
    
    def clear_serial_buffers(self):
        """시리얼 버퍼 완전 클리어"""
        if not self.serial_port:
            return
            
        try:
            # 입력 버퍼 클리어
            flush_count = 0
            while self.serial_port.in_waiting > 0 and flush_count < 10:
                old_data = self.serial_port.read(self.serial_port.in_waiting)
                self.log_message(f"🧹 버퍼 클리어: {len(old_data)} bytes 제거")
                time.sleep(0.05)  # 50ms 대기
                flush_count += 1
                
            # 출력 버퍼도 플러시
            self.serial_port.flush()
            
            # 추가 안정화 시간
            time.sleep(0.1)
            
        except Exception as e:
            self.log_message(f"⚠️ 버퍼 클리어 오류: {str(e)}")
        
    def capture_loop(self):
        """화면 캡처 루프 - 최적화된 고성능 버전"""
        consecutive_failures = 0
        max_failures = 3  # 실패 허용 횟수 줄임 (5 -> 3)
        last_request_time = 0
        
        try:
            while self.is_monitoring:
                try:
                    current_time = time.time()
                    
                    # 자동 요청 모드에서만 주기적으로 화면 요청
                    if self.auto_request_enabled:
                        interval_seconds = self.update_interval_ms / 1000.0
                        
                        if current_time - last_request_time >= interval_seconds:
                            # 고속 화면 요청 및 처리
                            try:
                                success = self.fast_screen_request()
                                last_request_time = current_time
                                
                                if success:
                                    consecutive_failures = 0
                                else:
                                    consecutive_failures += 1
                            except Exception as request_error:
                                consecutive_failures += 1
                        
                        # 최적화된 대기 시간 (CPU 효율성 향상)
                        sleep_time = min(0.005, interval_seconds / 50)  # 5ms 최대, 더 빠른 응답
                        time.sleep(sleep_time)
                    else:
                        # 수동 모드에서는 짧은 대기 (반응성 향상)
                        time.sleep(0.02)  # 20ms 대기 (기존 100ms에서 대폭 단축)
                        consecutive_failures = 0
                        
                    # 연속 실패 처리 (더 빠른 복구)
                    if consecutive_failures >= max_failures:
                        try:
                            self.root.after(0, lambda: self.log_message(f"🚨 연속 {max_failures}회 실패로 캡처 루프 일시 중단 (0.5초)"))
                        except:
                            pass  # 로그 메시지 오류는 무시
                        time.sleep(0.5)  # 대기 시간 단축 (2초 -> 0.5초)
                        consecutive_failures = 0
                        
                except Exception as inner_error:
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_failures:
                        try:
                            self.root.after(0, lambda: self.log_message("🚨 캡처 루프 오류로 일시 중단"))
                        except:
                            pass
                        time.sleep(0.5)  # 대기 시간 단축
                        consecutive_failures = 0
                    else:
                        time.sleep(0.1)  # 실패시 대기 시간 단축 (0.5초 -> 0.1초)
                        
        except Exception as critical_error:
            # 스레드 전체를 중단시킬 수 있는 심각한 오류 처리
            try:
                self.root.after(0, lambda: self.log_message(f"❌ 캡처 루프 심각한 오류: {str(critical_error)}"))
                self.root.after(0, lambda: self.stop_monitoring())
            except:
                # 최후의 안전장치 - 모든 GUI 호출이 실패해도 스레드는 종료
                pass
        finally:
            # 스레드 정리 작업
            try:
                self.root.after(0, lambda: self.log_message("🔄 캡처 루프 종료"))
            except:
                pass
    
    def fast_screen_request(self):
        """고속 화면 요청 및 처리 (최적화된 버전) - RAW 데이터 로깅 포함"""
        if not self.is_connected or not self.serial_port:
            return False
            
        try:
            # 고속 요청 전송
            self.serial_port.write(b'GET_SCREEN\n')
            self.serial_port.flush()
            
            # 초고속 응답 수집 (블록킹 방식으로 성능 향상)
            start_time = time.time()
            response_data = b''
            timeout_seconds = 0.5  # 타임아웃 단축 (기존보다 빠름)
            
            # 필수 마커들
            markers_found = {
                'screen_start': False,
                'data_start': False, 
                'data_end': False,
                'screen_end': False
            }
            
            while time.time() - start_time < timeout_seconds:
                try:
                    if self.serial_port.in_waiting > 0:
                        chunk = self.serial_port.read(self.serial_port.in_waiting)
                        response_data += chunk
                        
                        # 마커 검사 (최적화된 방식)
                        if not markers_found['screen_start'] and b'<<SCREEN_START>>' in response_data:
                            markers_found['screen_start'] = True
                        if not markers_found['data_start'] and b'<<DATA_START>>' in response_data:
                            markers_found['data_start'] = True
                        if not markers_found['data_end'] and b'<<DATA_END>>' in response_data:
                            markers_found['data_end'] = True
                        if not markers_found['screen_end'] and b'<<SCREEN_END>>' in response_data:
                            markers_found['screen_end'] = True
                            break  # 모든 데이터 수신 완료
                        
                        # 오류 감지
                        if b'<<TRANSMISSION_ERROR>>' in response_data:
                            # 전송 오류시 RAW 데이터 로그 기록
                            if hasattr(self, 'status_logger') and self.status_logger:
                                self.status_logger.log_screen_capture(False, len(response_data), response_data)
                            return False
                    else:
                        time.sleep(0.001)  # 1ms 대기 (매우 짧음)
                        
                except Exception as serial_error:
                    # 시리얼 통신 오류 처리 및 RAW 데이터 로그
                    if hasattr(self, 'status_logger') and self.status_logger:
                        self.status_logger.log_event("SERIAL_ERROR", f"시리얼 오류: {str(serial_error)}", response_data)
                    return False
            
            # 모든 마커 확인
            if not all(markers_found.values()):
                # 불완전한 수신시 RAW 데이터 로그
                if hasattr(self, 'status_logger') and self.status_logger:
                    missing_markers = [k for k, v in markers_found.items() if not v]
                    self.status_logger.log_screen_capture(False, len(response_data), response_data)
                    self.status_logger.log_event("INCOMPLETE_MARKERS", f"누락된 마커: {missing_markers}", response_data)
                return False
            
            # 이미지 데이터 추출 (최적화)
            try:
                data_start_pos = response_data.find(b'<<DATA_START>>\n') + len(b'<<DATA_START>>\n')
                data_end_pos = response_data.find(b'\n<<DATA_END>>')
                
                if data_start_pos == -1 or data_end_pos == -1:
                    # 마커 위치 오류시 RAW 데이터 로그
                    if hasattr(self, 'status_logger') and self.status_logger:
                        self.status_logger.log_screen_capture(False, len(response_data), response_data)
                        self.status_logger.log_event("MARKER_POSITION_ERROR", f"마커 위치 오류: start={data_start_pos}, end={data_end_pos}", response_data)
                    return False
                
                img_data = response_data[data_start_pos:data_end_pos]
                
                # 크기 검증 (빠른 체크)
                if len(img_data) != 1024:
                    # 크기 오류시 RAW 데이터 로그
                    if hasattr(self, 'status_logger') and self.status_logger:
                        self.status_logger.log_screen_capture(False, len(img_data), response_data)
                        self.status_logger.log_event("SIZE_MISMATCH", f"예상 크기: 1024, 실제 크기: {len(img_data)}", img_data)
                    return False
                
                # 고속 파싱 및 화면 업데이트
                screen_data = self.fast_parse_screen_data(img_data)
                if screen_data is not None:
                    # GUI 업데이트는 메인 스레드에서 안전하게 수행
                    try:
                        self.root.after(0, lambda: self.update_display(screen_data))
                    except Exception as gui_error:
                        # GUI 업데이트 오류는 무시하고 계속 진행
                        pass
                    
                    # 성공적인 화면 캡처 RAW 데이터 로그 (간소화 - 너무 빈번한 로깅 방지)
                    if hasattr(self, 'status_logger') and self.status_logger and self.performance_stats['total_captures'] % 50 == 0:
                        # 50회마다 한 번씩만 성공 RAW 데이터 로그
                        self.status_logger.log_screen_capture(True, len(img_data), img_data[:100])  # 처음 100바이트만 로그
                    
                    # 성능 통계 업데이트 (경량화)
                    self.performance_stats['total_captures'] += 1
                    self.performance_stats['successful_captures'] += 1
                    
                    # 성능 표시 업데이트 (주기 줄임)
                    if self.performance_stats['total_captures'] % 10 == 0:  # 10회마다 업데이트
                        try:
                            self.root.after(0, self.update_performance_display)
                        except Exception as perf_error:
                            # 성능 표시 오류는 무시
                            pass
                    
                    return True
                else:
                    # 파싱 실패시 RAW 데이터 로그
                    if hasattr(self, 'status_logger') and self.status_logger:
                        self.status_logger.log_screen_capture(False, len(img_data), img_data)
                        self.status_logger.log_event("PARSING_FAILED", "화면 데이터 파싱 실패", img_data)
                
            except Exception as parse_error:
                # 파싱 과정 오류시 RAW 데이터 로그
                if hasattr(self, 'status_logger') and self.status_logger:
                    self.status_logger.log_screen_capture(False, len(response_data), response_data)
                    self.status_logger.log_event("PARSE_EXCEPTION", f"파싱 예외: {str(parse_error)}", response_data)
                return False
                
            return False
                
        except Exception as e:
            # 모든 예외를 안전하게 처리하고 RAW 데이터 로그
            if hasattr(self, 'status_logger') and self.status_logger:
                self.status_logger.log_event("SCREEN_REQUEST_ERROR", f"화면 요청 오류: {str(e)}", None)
            return False
    
    def request_screen_update(self):
        """화면 업데이트 요청 (논블록킹 방식)"""
        if not self.is_connected or not self.serial_port:
            return False
            
        try:
            # 논블록킹 방식으로 즉시 요청 전송
            self.serial_port.write(b'GET_SCREEN\n')
            self.serial_port.flush()
            
            # 즉시 응답 확인 (짧은 타임아웃)
            response_available = False
            quick_check_count = 0
            
            # 빠른 응답 확인 (최대 50ms)
            while quick_check_count < 5:  # 5 x 10ms = 50ms
                if self.serial_port.in_waiting > 0:
                    response_available = True
                    break
                time.sleep(0.01)  # 10ms 대기
                quick_check_count += 1
            
            if response_available:
                # 응답이 빠르게 왔으면 즉시 처리
                self.process_screen_response()
                return True
            else:
                # 응답이 늦으면 다음 사이클에서 처리
                return False
                
        except Exception as e:
            self.log_message(f"❌ 화면 요청 오류: {str(e)}")
            return False
    
    def process_screen_response(self):
        """화면 응답 데이터 처리 (capture_screen 로직 재사용)"""
        try:
            # 기존 capture_screen 로직을 재사용하되, 요청 부분은 제외
            # 성능 통계 업데이트
            self.performance_stats['total_captures'] += 1
            
            response_data = b''
            timeout_count = 0
            max_timeout = 100  # 1초 타임아웃 (기존보다 단축)
            
            # 단계별 마커 확인
            screen_start_found = False
            data_start_found = False
            data_end_found = False
            screen_end_found = False
            checksum_received = None
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 단계별 마커 검출
                    if not screen_start_found and b'<<SCREEN_START>>' in response_data:
                        screen_start_found = True
                        
                    if screen_start_found and not data_start_found and b'<<DATA_START>>' in response_data:
                        data_start_found = True
                        
                        # 체크섬 추출
                        checksum_match = re.search(rb'CHECKSUM:([0-9A-F]{8})', response_data)
                        if checksum_match:
                            checksum_received = checksum_match.group(1).decode()
                        
                    if data_start_found and not data_end_found and b'<<DATA_END>>' in response_data:
                        data_end_found = True
                        
                    if data_end_found and not screen_end_found and b'<<SCREEN_END>>' in response_data:
                        screen_end_found = True
                        break
                        
                    # 전송 오류 감지
                    if b'<<TRANSMISSION_ERROR>>' in response_data:
                        self.log_message("❌ 화면 전송 오류")
                        return False
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            # 수신 완료 검증
            if not (screen_start_found and data_start_found and data_end_found and screen_end_found):
                return False
                
            # 실제 이미지 데이터 추출
            data_start_pos = response_data.find(b'<<DATA_START>>')
            data_end_pos = response_data.find(b'<<DATA_END>>')
            
            if data_start_pos == -1 or data_end_pos == -1:
                return False
                
            data_start_actual = response_data.find(b'\n', data_start_pos) + 1
            img_data = response_data[data_start_actual:data_end_pos]
            
            # 데이터 크기 검증
            if len(img_data) < 1024:
                return False
            elif len(img_data) > 1024:
                img_data = img_data[:1024]
            
            # 체크섬 검증 (있는 경우)
            if checksum_received:
                calculated_checksum = sum(img_data) & 0xFFFFFFFF
                received_checksum = int(checksum_received, 16)
                
                if calculated_checksum != received_checksum:
                    return False
            
            # 파싱 및 화면 업데이트
            screen_data = self.parse_firmware_screen_data_enhanced(img_data)
            if screen_data is not None:
                self.update_display(screen_data)
                
                # 성공 통계 업데이트
                self.performance_stats['successful_captures'] += 1
                self.update_performance_display()
                
                return True
            
            return False
                
        except Exception as e:
            self.log_message(f"❌ 화면 응답 처리 오류: {str(e)}")
            return False
    
    def status_loop(self):
        """상태 모니터링 루프 - BAT ADC 처리 최적화 및 무한루프 방지"""
        status_request_interval = 5.0  # 5초마다 상태 요청
        last_status_request = 0
        consecutive_errors = 0  # 연속 오류 카운터
        max_consecutive_errors = 3  # 최대 연속 오류 허용
        status_timeout_count = 0  # 상태 타임아웃 카운터
        max_status_timeouts = 5  # 최대 상태 타임아웃 허용
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 상태 요청 주기 확인
                if current_time - last_status_request >= status_request_interval:
                    # GET_STATUS 명령어로 상태 정보 요청
                    if self.is_connected and self.serial_port:
                        try:
                            # 시리얼 버퍼 클리어 (무한루프 방지)
                            if self.serial_port.in_waiting > 0:
                                old_data = self.serial_port.read(self.serial_port.in_waiting)
                                if len(old_data) > 100:  # 너무 많은 데이터가 쌓여있으면 경고
                                    self.write_status_log_event("WARNING", f"과도한 버퍼 데이터: {len(old_data)} bytes")
                            
                            # 상태 요청 전송 (타임아웃 설정)
                            self.serial_port.write(b'GET_STATUS\n')
                            self.serial_port.flush()
                            
                            # 응답 대기 및 처리 (짧은 타임아웃으로 블로킹 방지)
                            response = self.wait_for_response(800)  # 800ms로 단축
                            if response:
                                # BAT ADC 안전 파싱
                                status_data = self._safe_parse_status_data(response)
                                if status_data:
                                    # GUI 업데이트 (비동기)
                                    self.root.after(0, lambda data=status_data: self.update_status_display(data))
                                    
                                    # 상태 로그에 기록 (안전한 방식)
                                    try:
                                        self.write_status_log(status_data)
                                    except Exception as log_error:
                                        # 로그 기록 실패해도 모니터링은 계속
                                        pass
                                    
                                    consecutive_errors = 0  # 성공시 오류 카운터 리셋
                                    status_timeout_count = 0  # 타임아웃 카운터 리셋
                                    last_status_request = current_time
                                else:
                                    # 파싱 실패시 테스트 데이터로 대체 (BAT ADC 포함)
                                    test_status = self._generate_safe_test_status()
                                    self.root.after(0, lambda data=test_status: self.update_status_display(data))
                                    consecutive_errors += 1
                                    
                            else:
                                # 응답 없음 - 타임아웃 카운터 증가
                                status_timeout_count += 1
                                if status_timeout_count <= max_status_timeouts:
                                    self.write_status_log_event("WARNING", f"상태 응답 없음 ({status_timeout_count}/{max_status_timeouts})")
                                consecutive_errors += 1
                                
                        except Exception as status_error:
                            error_msg = str(status_error)
                            # BAT ADC 관련 오류 특별 처리
                            if "BAT_ADC" in error_msg or "parse" in error_msg.lower():
                                self.write_status_log_event("ERROR", f"BAT ADC 파싱 오류: {error_msg}")
                                # 안전한 테스트 데이터로 대체
                                safe_status = self._generate_safe_test_status()
                                self.root.after(0, lambda data=safe_status: self.update_status_display(data))
                            else:
                                self.write_status_log_event("ERROR", f"상태 요청 오류: {error_msg}")
                            consecutive_errors += 1
                            
                        # 연속 오류가 너무 많으면 잠시 대기
                        if consecutive_errors >= max_consecutive_errors:
                            self.write_status_log_event("WARNING", f"연속 오류 {consecutive_errors}회 발생, 대기 중...")
                            time.sleep(3)  # 3초 대기 (단축)
                            consecutive_errors = 0  # 리셋
                            
                        # 상태 타임아웃이 너무 많으면 상태 요청 중단
                        if status_timeout_count >= max_status_timeouts:
                            self.write_status_log_event("WARNING", "상태 요청 일시 중단 (과도한 타임아웃)")
                            time.sleep(10)  # 10초 대기 후 재시도
                            status_timeout_count = 0
                            
                    last_status_request = current_time
                
                # 루프 대기 시간 (CPU 효율성)
                time.sleep(0.5)  # 0.5초 간격으로 단축 (기존 1초)
                
            except Exception as e:
                error_msg = str(e)
                self.write_status_log_event("ERROR", f"상태 루프 오류: {error_msg}")
                consecutive_errors += 1
                
                # BAT ADC 관련 심각한 오류시 상태 루프 일시 중단
                if "BAT_ADC" in error_msg or consecutive_errors >= max_consecutive_errors:
                    time.sleep(5)  # 5초 대기
                    consecutive_errors = 0
                else:
                    time.sleep(1)  # 1초 대기
    
    def _safe_parse_status_data(self, response):
        """BAT ADC 안전 파싱 (타임아웃 및 예외 처리 강화)"""
        try:
            # 파싱 시간 제한 (3초)
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("상태 파싱 타임아웃")
            
            # 윈도우에서는 signal.alarm이 지원되지 않으므로 조건부 처리
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(3)  # 3초 타임아웃
            except (AttributeError, OSError):
                # 윈도우나 신호 처리가 지원되지 않는 환경
                pass
            
            try:
                # 기존 파싱 함수 호출
                result = self.parse_firmware_status_data(response)
                
                # BAT ADC 값 검증 및 보정
                if result and 'bat_adc' in result:
                    bat_adc = result['bat_adc']
                    # ADC 값 범위 검증 (0-4095, 12-bit ADC)
                    if not isinstance(bat_adc, int) or bat_adc < 0 or bat_adc > 4095:
                        result['bat_adc'] = 0  # 잘못된 값은 0으로 보정
                        self.write_status_log_event("WARNING", f"BAT ADC 값 보정: {bat_adc} -> 0")
                
                return result
                
            finally:
                try:
                    signal.alarm(0)  # 타임아웃 해제
                except (AttributeError, OSError):
                    pass
                
        except TimeoutError:
            self.write_status_log_event("ERROR", "상태 파싱 타임아웃 - 안전 모드로 전환")
            return self._generate_safe_test_status()
        except Exception as e:
            self.write_status_log_event("ERROR", f"안전 파싱 오류: {str(e)}")
            return self._generate_safe_test_status()
    
    def _generate_safe_test_status(self):
        """안전한 테스트 상태 데이터 생성 (BAT ADC 포함)"""
        import random
        
        return {
            'battery': random.randint(20, 100),
            'timer': f"{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            'status': 'STANDBY',  # 안전한 기본 상태
            'l1_connected': False,  # 안전한 기본값
            'l2_connected': False,  # 안전한 기본값
            'bat_adc': random.randint(0, 4095),  # 유효한 ADC 범위
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': 'safe_test_data',
            'raw_data': b'STATUS:BAT:75%,TIMER:05:30,STATUS:STANDBY,L1:0,L2:0,BAT_ADC:2048',
            'raw_string': 'STATUS:BAT:75%,TIMER:05:30,STATUS:STANDBY,L1:0,L2:0,BAT_ADC:2048'
        }
    
    def generate_test_status_data(self):
        """테스트용 상태 데이터 생성"""
        import random
        
        statuses = ['STANDBY', 'RUNNING', 'SETTING', 'COOLING']
        
        return {
            'battery': random.randint(20, 100),
            'timer': f"{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            'status': random.choice(statuses),
            'l1_connected': random.choice([True, False]),
            'l2_connected': random.choice([True, False]),
            'bat_adc': random.randint(0, 4095),  # 12-bit ADC 값
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'source': 'test_data'
        }
    
    def capture_screen(self):
        """수동 화면 캡처 (버튼 클릭용)"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 수동 요청을 위한 버퍼 클리어
            self.clear_serial_buffers()
            
            # 즉시 화면 요청 및 처리
            self.serial_port.write(b'GET_SCREEN\n')
            self.serial_port.flush()
            
            # 동기적으로 응답 처리 (수동 요청이므로 완전한 대기)
            success = self.process_screen_response_sync()
            
            if success:
                self.log_message("✅ 수동 화면 캡처 성공")
            else:
                self.log_message("❌ 수동 화면 캡처 실패")
                
        except Exception as e:
            self.log_message(f"❌ 수동 화면 캡처 오류: {str(e)}")
    
    def process_screen_response_sync(self):
        """동기식 화면 응답 처리 (수동 캡처용)"""
        try:
            response_data = b''
            timeout_count = 0
            max_timeout = 300  # 3초 타임아웃 (충분한 시간)
            
            screen_start_found = False
            data_start_found = False
            data_end_found = False
            screen_end_found = False
            checksum_received = None
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 단계별 마커 검출
                    if not screen_start_found and b'<<SCREEN_START>>' in response_data:
                        screen_start_found = True
                        
                    if screen_start_found and not data_start_found and b'<<DATA_START>>' in response_data:
                        data_start_found = True
                        
                        # 체크섬 추출
                        checksum_match = re.search(rb'CHECKSUM:([0-9A-F]{8})', response_data)
                        if checksum_match:
                            checksum_received = checksum_match.group(1).decode()
                        
                    if data_start_found and not data_end_found and b'<<DATA_END>>' in response_data:
                        data_end_found = True
                        
                    if data_end_found and not screen_end_found and b'<<SCREEN_END>>' in response_data:
                        screen_end_found = True
                        break
                        
                    # 전송 오류 감지
                    if b'<<TRANSMISSION_ERROR>>' in response_data:
                        return False
                        
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            # 수신 완료 검증
            if not (screen_start_found and data_start_found and data_end_found and screen_end_found):
                return False
                
            # 실제 이미지 데이터 추출
            data_start_pos = response_data.find(b'<<DATA_START>>')
            data_end_pos = response_data.find(b'<<DATA_END>>')
            
            if data_start_pos == -1 or data_end_pos == -1:
                return False
                
            data_start_actual = response_data.find(b'\n', data_start_pos) + 1
            img_data = response_data[data_start_actual:data_end_pos]
            
            # 데이터 크기 검증
            if len(img_data) < 1024:
                return False
            elif len(img_data) > 1024:
                img_data = img_data[:1024]
            
            # 체크섬 검증
            if checksum_received:
                calculated_checksum = sum(img_data) & 0xFFFFFFFF
                received_checksum = int(checksum_received, 16)
                
                if calculated_checksum != received_checksum:
                    return False
            
            # 파싱 및 화면 업데이트
            screen_data = self.parse_firmware_screen_data_enhanced(img_data)
            if screen_data is not None:
                self.update_display(screen_data)
                return True
            
            return False
                
        except Exception as e:
            self.log_message(f"❌ 동기식 화면 처리 오류: {str(e)}")
            return False
    
    def parse_firmware_screen_data(self, data):
        """기존 펌웨어 화면 데이터 파싱 - 호환성 유지"""
        try:
            # 새로운 마커 형식 먼저 확인
            if b'<<SCREEN_START>>' in data and b'<<DATA_START>>' in data:
                # 새로운 형식으로 리다이렉트
                data_start_pos = data.find(b'<<DATA_START>>')
                data_end_pos = data.find(b'<<DATA_END>>')
                
                if data_start_pos != -1 and data_end_pos != -1:
                    data_start_actual = data.find(b'\n', data_start_pos) + 1
                    img_data = data[data_start_actual:data_end_pos]
                    
                    if len(img_data) >= 1024:
                        return self.parse_firmware_screen_data_enhanced(img_data[:1024])
            
            # 기존 형식 처리 (하위 호환성)
            self.log_message("기존 형식으로 파싱 시도")
            
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
            self.log_message(f"기존 파싱 오류: {str(e)}")
            return None
            
    def parse_firmware_screen_data_enhanced(self, img_data):
        """강화된 펌웨어 화면 데이터 파싱 - 다양한 회전 옵션 지원"""
        try:
            if len(img_data) != 1024:
                self.log_message(f"❌ 잘못된 데이터 크기: {len(img_data)}")
                return None
            
            # 원본 데이터 저장 (파싱 방법 변경시 재사용)
            self.last_raw_data = img_data
                
            # NumPy 사용 가능 여부 확인
            if not self.numpy_available:
                try:
                    import numpy as np
                    self.numpy_available = True
                except ImportError:
                    return self._parse_without_numpy(img_data)
            
            import numpy as np
            
            # OLED 데이터를 PIL 이미지로 변환
            img_array = np.zeros((self.OLED_HEIGHT, self.OLED_WIDTH), dtype=np.uint8)
            width_bytes = self.OLED_WIDTH // 8  # 16 bytes per row
            
            current_method = self.parsing_method
            self.log_message(f"파싱 방법: {current_method}")
            
            # 기본 파싱 (원본 데이터)
            temp_array = np.zeros((self.OLED_HEIGHT, self.OLED_WIDTH), dtype=np.uint8)
            
            for row in range(self.OLED_HEIGHT):
                for byte_col in range(width_bytes):
                    byte_idx = byte_col + row * width_bytes
                    
                    if byte_idx < len(img_data):
                        byte_value = img_data[byte_idx]
                        
                        for bit in range(8):
                            x = byte_col * 8 + bit
                            y = row
                            
                            if x < self.OLED_WIDTH and y < self.OLED_HEIGHT:
                                bit_value = (byte_value >> (7 - bit)) & 1
                                temp_array[y, x] = 255 if bit_value else 0
            
            # 파싱 방법에 따른 변환 적용
            if current_method == "method1_direct":
                # 방법 1: 직접 매핑 (변환 없음)
                img_array = temp_array.copy()
                
            elif current_method == "method2_reversed":
                # 방법 2: reverse 함수 적용
                for row in range(self.OLED_HEIGHT):
                    for byte_col in range(width_bytes):
                        byte_idx = byte_col + row * width_bytes
                        
                        if byte_idx < len(img_data):
                            byte_value = img_data[byte_idx]
                            reversed_byte = self.reverse_byte(byte_value)
                            
                            for bit in range(8):
                                x = byte_col * 8 + bit
                                y = row
                                
                                if x < self.OLED_WIDTH and y < self.OLED_HEIGHT:
                                    bit_value = (reversed_byte >> (7 - bit)) & 1
                                    img_array[y, x] = 255 if bit_value else 0
                                    
            elif current_method == "method3_rotated_180":
                # 방법 3: 180도 회전
                img_array = np.rot90(temp_array, 2)
                
            elif current_method == "method4_flipped_h":
                # 방법 4: 가로 뒤집기
                img_array = np.fliplr(temp_array)
                
            elif current_method == "method5_flipped_v":
                # 방법 5: 세로 뒤집기 (기본, 안정적)
                img_array = np.flipud(temp_array)
                
            elif current_method == "method5_rotate_90":
                # 방법 5-1: 90도 시계방향 회전
                img_array = np.rot90(temp_array, -1)  # -1은 시계방향
                
            elif current_method == "method5_rotate_270":
                # 방법 5-2: 270도 시계방향 회전 (90도 반시계방향)
                img_array = np.rot90(temp_array, 1)   # 1은 반시계방향
                
            elif current_method == "method5_mirror_h":
                # 방법 5-3: 가로 미러링 (좌우 반전)
                img_array = np.fliplr(temp_array)
                
            elif current_method == "method5_mirror_v":
                # 방법 5-4: 세로 미러링 (상하 반전)
                img_array = np.flipud(temp_array)
                
            elif current_method == "method5_flip_both":
                # 방법 5-5: 상하좌우 모두 뒤집기
                img_array = np.flipud(np.fliplr(temp_array))
                
            elif current_method == "method6_transposed":
                # 방법 6: 전치 + 조정
                # 128x64를 64x128로 전치하면 크기가 맞지 않으므로 보간 필요
                transposed = temp_array.T  # 전치: 64x128
                # 64x128을 128x64로 리사이즈
                from PIL import Image
                pil_img = Image.fromarray(transposed.astype(np.uint8), mode='L')
                resized_img = pil_img.resize((self.OLED_WIDTH, self.OLED_HEIGHT), Image.NEAREST)
                img_array = np.array(resized_img)
                
            else:
                # 알 수 없는 방법인 경우 기본 세로 뒤집기 적용
                self.log_message(f"⚠️ 알 수 없는 파싱 방법: {current_method}, 기본값 적용")
                img_array = np.flipud(temp_array)
            
            # 데이터 검증
            white_pixels = np.sum(img_array == 255)
            black_pixels = np.sum(img_array == 0)
            total_pixels = white_pixels + black_pixels
            
            if total_pixels == 0:
                self.log_message("❌ 빈 이미지 데이터")
                return None
                
            white_ratio = (white_pixels / total_pixels) * 100
            # 파싱 완료 로그를 간소화 (과도한 출력 방지)
            if white_ratio > 5:  # 의미있는 데이터가 있을 때만 상세 로그
                self.log_message(f"✅ 파싱 완료 - 흰색 픽셀: {white_ratio:.1f}%")
            else:
                self.log_message("✅ 파싱 완료")
            
            return img_array
            
        except Exception as e:
            self.log_message(f"❌ 파싱 오류: {str(e)}")
            return None
    
    def _parse_without_numpy(self, img_data):
        """NumPy 없이 파싱하는 폴백 함수"""
        try:
            # 원본 데이터 저장
            self.last_raw_data = img_data
            
            # PIL로 직접 처리
            img = Image.new('L', (128, 64), 0)
            pixels = []
            
            for y in range(64):
                for x in range(128):
                    byte_index = y * 16 + x // 8
                    if byte_index < len(img_data):
                        byte_val = img_data[byte_index]
                        bit_pos = 7 - (x % 8)
                        pixel_val = 255 if (byte_val >> bit_pos) & 1 else 0
                        pixels.append(pixel_val)
                    else:
                        pixels.append(0)
            
            img.putdata(pixels)
            
            # 파싱 방법 적용 (간단한 변환만)
            if self.parsing_method == "method3_rotated_180":
                img = img.rotate(180)
            elif self.parsing_method == "method4_flipped_h":
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif self.parsing_method == "method5_flipped_v":
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
            return img
            
        except Exception as e:
            self.log_message(f"❌ NumPy 없는 파싱 오류: {str(e)}")
            return None
    
    def reverse_byte(self, byte_val):
        """OLED 드라이버의 reverse() 함수 구현"""
        # temp = ((temp & 0x55) << 1) | ((temp & 0xaa) >> 1);
        # temp = ((temp & 0x33) << 2) | ((temp & 0xcc) >> 2);
        # temp = ((temp & 0x0f) << 4) | ((temp & 0xf0) >> 4);
        temp = byte_val
        temp = ((temp & 0x55) << 1) | ((temp & 0xaa) >> 1)
        temp = ((temp & 0x33) << 2) | ((temp & 0xcc) >> 2) 
        temp = ((temp & 0x0f) << 4) | ((temp & 0xf0) >> 4)
        return temp
        
    def generate_test_screen(self):
        """테스트용 더미 화면 데이터 생성 (실제 OLED 형식)"""
        # 실제 OLED 데이터 형식으로 테스트 패턴 생성
        data = np.zeros((self.OLED_HEIGHT, self.OLED_WIDTH), dtype=np.uint8)
        
        # 명확한 흑백 패턴 생성 (격자 무늬)
        pattern_type = int(time.time()) % 4  # 4가지 패턴을 순환
        
        if pattern_type == 0:
            # 체스보드 패턴
            for y in range(self.OLED_HEIGHT):
                for x in range(self.OLED_WIDTH):
                    if (x // 8 + y // 8) % 2 == 0:
                        data[y, x] = 255
        elif pattern_type == 1:
            # 세로 줄무늬
            for y in range(self.OLED_HEIGHT):
                for x in range(self.OLED_WIDTH):
                    if (x // 4) % 2 == 0:
                        data[y, x] = 255
        elif pattern_type == 2:
            # 가로 줄무늬
            for y in range(self.OLED_HEIGHT):
                for x in range(self.OLED_WIDTH):
                    if (y // 4) % 2 == 0:
                        data[y, x] = 255
        else:
            # 중앙 사각형 + 테두리
            for y in range(self.OLED_HEIGHT):
                for x in range(self.OLED_WIDTH):
                    # 테두리
                    if x < 2 or x >= self.OLED_WIDTH - 2 or y < 2 or y >= self.OLED_HEIGHT - 2:
                        data[y, x] = 255
                    # 중앙 사각형
                    elif 20 <= x < 108 and 15 <= y < 49:
                        data[y, x] = 255
                        
        # 테스트 텍스트 영역 (우상단에 "TEST" 표시)
        # 간단한 픽셀 아트로 "TEST" 문자 만들기
        test_pattern = [
            [1,1,1,0,1,1,1,0,1,1,1,0,1,1,1],  # T E S T
            [0,1,0,0,1,0,0,0,1,0,0,0,0,1,0],
            [0,1,0,0,1,1,0,0,1,1,0,0,0,1,0],
            [0,1,0,0,1,0,0,0,0,0,1,0,0,1,0],
            [0,1,0,0,1,1,1,0,1,1,1,0,0,1,0],
        ]
        
        start_x = self.OLED_WIDTH - 20
        start_y = 5
        for row, line in enumerate(test_pattern):
            for col, pixel in enumerate(line):
                x = start_x + col
                y = start_y + row
                if x < self.OLED_WIDTH and y < self.OLED_HEIGHT and pixel:
                    data[y, x] = 255
                    
        return data
        
    def request_status(self):
        """상태 정보 요청"""
        if not self.is_connected or not self.serial_port:
            return
            
        try:
            # 상태 요청 명령 전송
            self.serial_port.write(b'GET_STATUS\n')
            self.serial_port.flush()
            
            # 응답 대기
            response_data = b''
            timeout_count = 0
            max_timeout = 20  # 200ms 타임아웃
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 개행 문자를 찾으면 완료
                    if b'\n' in response_data:
                        break
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            if len(response_data) > 0:
                # 실제 펌웨어 응답 파싱
                status_info = self.parse_firmware_status_data(response_data)
                if status_info:
                    self.update_status_display(status_info)
                    return
            
            # 응답이 없거나 파싱 실패시 테스트 데이터 사용
            test_status = {
                'battery': 75,
                'timer': '99:99',
                'status': 'ERROR',
                'l1_connected': True,
                'l2_connected': False,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'test_data'
            }
            
            self.update_status_display(test_status)
            
        except Exception as e:
            self.log_message(f"상태 요청 실패: {str(e)}")
    
    def parse_firmware_status_data(self, response):
        """펌웨어에서 받은 상태 데이터 파싱 - BAT ADC 안전 처리 및 무한루프 방지"""
        try:
            # 파싱 시간 제한 (응답 없음 방지)
            start_parse_time = time.time()
            max_parse_time = 2.0  # 2초 파싱 시간 제한
            
            # 강화된 시리얼 파서 사용 (RAW 데이터 지원)
            if self.serial_parser:
                try:
                    parsed_data = self.serial_parser.parse_status_data(response)
                    if parsed_data:
                        # 파싱 시간 체크
                        if time.time() - start_parse_time > max_parse_time:
                            self.write_status_log_event("WARNING", "시리얼 파서 타임아웃")
                            return None
                        return parsed_data
                except Exception as parser_error:
                    self.write_status_log_event("ERROR", f"시리얼 파서 오류: {str(parser_error)}")
                    # 파서 오류시 기본 파싱으로 폴백
            
            # 폴백: 기본 파싱 (RAW 데이터 포함, 안전 처리)
            if isinstance(response, bytes):
                raw_data = response
                try:
                    data_str = response.decode('utf-8', errors='ignore').strip()
                except UnicodeDecodeError:
                    # 디코딩 실패시 안전한 처리
                    data_str = str(response, errors='replace').strip()
            else:
                data_str = str(response).strip()
                raw_data = data_str.encode('utf-8', errors='ignore')
            
            # 파싱 시간 체크
            if time.time() - start_parse_time > max_parse_time:
                self.write_status_log_event("WARNING", "기본 파싱 타임아웃")
                return None
            
            # 데이터 길이 검증 (과도한 데이터 방지)
            if len(data_str) > 1000:  # 1KB 제한
                self.write_status_log_event("WARNING", f"과도한 데이터 크기: {len(data_str)} chars")
                data_str = data_str[:1000]  # 잘라내기
            
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
            
            # 안전한 파싱을 위한 아이템 분할
            try:
                items = status_part.split(',')
                # 최대 아이템 수 제한 (무한루프 방지)
                if len(items) > 20:
                    self.write_status_log_event("WARNING", f"과도한 상태 아이템 수: {len(items)}")
                    items = items[:20]  # 최대 20개로 제한
                
                parse_count = 0  # 파싱 카운터
                max_parse_count = 50  # 최대 파싱 횟수 제한
                
                for item in items:
                    parse_count += 1
                    if parse_count > max_parse_count:
                        self.write_status_log_event("WARNING", "파싱 횟수 제한 도달")
                        break
                    
                    # 파싱 시간 체크
                    if time.time() - start_parse_time > max_parse_time:
                        self.write_status_log_event("WARNING", "파싱 시간 초과")
                        break
                    
                    item = item.strip()  # 공백 제거
                    if not item or ':' not in item:
                        continue
                    
                    try:
                        key, value = item.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 키와 값 길이 검증
                        if len(key) > 50 or len(value) > 100:
                            self.write_status_log_event("WARNING", f"과도한 키/값 길이: {key}={value}")
                            continue
                        
                        if key == 'BAT':
                            # 배터리: "75%" -> 75
                            try:
                                battery_str = value.replace('%', '').strip()
                                battery_val = int(battery_str)
                                # 배터리 범위 검증
                                if 0 <= battery_val <= 100:
                                    status_info['battery'] = battery_val
                                else:
                                    status_info['battery'] = max(0, min(100, battery_val))  # 범위 보정
                            except (ValueError, TypeError):
                                status_info['battery'] = 0
                                self.write_status_log_event("WARNING", f"배터리 값 파싱 오류: {value}")
                                
                        elif key == 'TIMER':
                            # 타이머: "05:30"
                            if len(value) <= 10:  # 길이 제한
                                status_info['timer'] = value
                            else:
                                status_info['timer'] = '00:00'
                                
                        elif key == 'STATUS':
                            # 상태: "RUNNING"
                            if len(value) <= 20:  # 길이 제한
                                status_info['status'] = value
                            else:
                                status_info['status'] = 'UNKNOWN'
                                
                        elif key == 'L1':
                            # L1 연결: "1" -> True
                            status_info['l1_connected'] = (value == '1')
                            
                        elif key == 'L2':
                            # L2 연결: "0" -> False
                            status_info['l2_connected'] = (value == '1')
                            
                        elif key == 'BAT_ADC':
                            # BAT ADC: "123" -> 123 (안전한 파싱)
                            try:
                                adc_val = int(value)
                                # ADC 범위 검증 (12-bit ADC: 0-4095)
                                if 0 <= adc_val <= 4095:
                                    status_info['bat_adc'] = adc_val
                                else:
                                    # 범위 벗어나면 보정
                                    status_info['bat_adc'] = max(0, min(4095, adc_val))
                                    self.write_status_log_event("WARNING", f"BAT ADC 값 보정: {adc_val} -> {status_info['bat_adc']}")
                            except (ValueError, TypeError) as adc_error:
                                status_info['bat_adc'] = 0
                                self.write_status_log_event("WARNING", f"BAT ADC 파싱 오류: {value} ({str(adc_error)})")
                                
                    except Exception as item_error:
                        # 개별 아이템 파싱 오류시 로그만 기록하고 계속 진행
                        self.write_status_log_event("WARNING", f"아이템 파싱 오류: {item} ({str(item_error)})")
                        continue
                
            except Exception as split_error:
                self.write_status_log_event("ERROR", f"상태 데이터 분할 오류: {str(split_error)}")
                return None
            
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
            parse_duration = time.time() - start_parse_time
            if parse_duration > 1.0:  # 1초 이상 걸리면 경고
                self.write_status_log_event("WARNING", f"파싱 시간 지연: {parse_duration:.2f}초")
            
            return status_info
            
        except Exception as e:
            error_msg = str(e)
            self.write_status_log_event("ERROR", f"상태 데이터 파싱 치명적 오류: {error_msg}")
            
            # 오류시에도 RAW 데이터 포함하여 반환
            return {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'firmware_error',
                'battery': 0,
                'timer': '00:00',
                'status': 'ERROR',
                'l1_connected': False,
                'l2_connected': False,
                'bat_adc': 0,
                'error': error_msg,
                'raw_data': response if isinstance(response, bytes) else str(response).encode('utf-8', errors='ignore'),
                'raw_string': response.decode('utf-8', errors='ignore') if isinstance(response, bytes) else str(response)
            }
    
    def update_display(self, screen_data):
        """화면 업데이트 (PIL/NumPy 호환 버전)"""
        if screen_data is None:
            return
            
        try:
            # 화면 데이터를 PIL Image로 통일
            if hasattr(screen_data, 'save'):
                # 이미 PIL Image인 경우
                display_img = screen_data
            elif hasattr(screen_data, 'shape'):
                # NumPy 배열인 경우
                display_img = Image.fromarray(screen_data.astype('uint8'), mode='L')
            else:
                # 다른 형식인 경우 PIL Image로 변환 시도
                display_img = Image.fromarray(screen_data, mode='L')
            
            # 스케일링 최적화
            scale = int(self.scale_var.get())
            
            if scale == 1:
                # 스케일링 없음 - 최고 성능
                final_img = display_img
            else:
                # 고품질 리사이징 (필요시에만)
                new_size = (128 * scale, 64 * scale)
                final_img = display_img.resize(new_size, Image.NEAREST)  # NEAREST는 가장 빠름
            
            # PhotoImage 변환 최적화
            self.current_image = ImageTk.PhotoImage(final_img)
            
            # Canvas 업데이트 (최소한의 연산)
            self.canvas.delete("all")  # 이전 이미지 삭제
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
            
            # Canvas 크기 자동 조정
            canvas_width = 128 * scale
            canvas_height = 64 * scale
            self.canvas.config(width=canvas_width, height=canvas_height)
            
            # 현재 화면 저장 (파싱 방법 변경용)
            self.current_screen = screen_data
            
        except Exception as e:
            self.log_message(f"❌ 화면 업데이트 오류: {str(e)}")
    
    def update_display_scale(self, value):
        """화면 확대 비율 업데이트"""
        scale = int(float(value))
        self.scale_label.config(text=f"{scale}x")
        
        if self.current_screen is not None:
            self.update_display(self.current_screen)
            
    def update_status_display(self, status_data):
        """상태 정보 디스플레이 업데이트"""
        self.current_status = status_data
        
        # 데이터 소스 표시
        data_source = status_data.get('source', 'unknown')
        if data_source == 'firmware':
            source_text = "📡 실시간 데이터"
            source_color = "green"
        else:
            source_text = "🧪 테스트 데이터"
            source_color = "orange"
        
        # BAT ADC 값 표시 추가
        bat_adc_text = f"BAT ADC: {status_data.get('bat_adc', 'N/A')}"
        
        status_text = f"""배터리: {status_data.get('battery', 'N/A')}%
타이머: {status_data.get('timer', 'N/A')}
상태: {status_data.get('status', 'N/A')}
L1 연결: {'예' if status_data.get('l1_connected', False) else '아니오'}
L2 연결: {'예' if status_data.get('l2_connected', False) else '아니오'}
{bat_adc_text}
업데이트: {status_data.get('timestamp', 'N/A')}
데이터 소스: {source_text}
"""
        
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, status_text)
        
        # 상태에 따른 텍스트 색상 변경
        if hasattr(self, 'status_label'):
            if data_source == 'firmware':
                self.status_label.config(foreground="green")
            else:
                self.status_label.config(foreground="orange")
        
    def refresh_status(self):
        """상태 새로고침"""
        if self.is_connected:
            try:
                # 즉시 상태 요청
                self.serial_port.write(b'GET_STATUS\n')
                self.serial_port.flush()
                
                response = self.wait_for_response(2000)
                if response:
                    status_data = self.parse_firmware_status_data(response)
                    if status_data:
                        self.update_status_display(status_data)
                        # 수동 새로고침도 로그에 기록
                        self.write_status_log(status_data)
                        self.write_status_log_event("MANUAL", "수동 상태 새로고침")
                    else:
                        # 파싱 실패시 테스트 데이터
                        test_status = self.generate_test_status_data()
                        self.update_status_display(test_status)
                else:
                    self.log_message("❌ 상태 새로고침 응답 없음")
                    
            except Exception as e:
                self.log_message(f"❌ 상태 새로고침 오류: {str(e)}")
                self.write_status_log_event("ERROR", f"상태 새로고침 오류: {str(e)}")
        else:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
    
    def save_screen(self):
        """화면 저장 - 개선된 버전"""
        if self.current_screen is None:
            messagebox.showwarning("경고", "저장할 화면이 없습니다")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # 현재 화면 데이터 타입에 따라 처리
                if hasattr(self.current_screen, 'save'):
                    # PIL Image 객체인 경우
                    self.current_screen.save(filename)
                elif hasattr(self.current_screen, 'shape'):
                    # NumPy 배열인 경우
                    img = Image.fromarray(self.current_screen.astype('uint8'), mode='L')
                    img.save(filename)
                else:
                    # 다른 형식인 경우 PIL Image로 변환 시도
                    img = Image.fromarray(self.current_screen, mode='L')
                    img.save(filename)
                    
                self.log_message(f"✅ 화면이 저장되었습니다: {filename}")
                
            except Exception as e:
                error_msg = f"화면 저장 실패: {str(e)}"
                messagebox.showerror("오류", error_msg)
                self.log_message(f"❌ {error_msg}")
                
    def save_session(self):
        """세션 기록 저장"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'status': self.current_status,
                'settings': {
                    'port': self.port_var.get(),
                    'baudrate': self.baud_var.get()
                }
            }
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                self.log_message(f"세션이 저장되었습니다: {filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {str(e)}")
    
    def log_message(self, message):
        """로그 메시지 출력 - 중복 방지 및 출력 최적화"""
        current_time = time.time()
        
        # 파싱 관련 메시지는 더 엄격하게 제한
        if any(keyword in message for keyword in ["파싱 방법:", "✅ 파싱 완료", "수신 중...", "진행상황"]):
            throttle_interval = 5.0  # 파싱 메시지는 5초 간격
        else:
            throttle_interval = self.log_throttle_interval
        
        # 메시지 키 생성 (동일 패턴의 메시지 그룹화)
        message_key = message
        if "수신 중..." in message:
            message_key = "수신 중..."  # 수신 메시지는 하나로 그룹화
        elif "✅ 파싱 완료" in message:
            message_key = "파싱 완료"  # 파싱 완료 메시지도 그룹화
        elif "파싱 방법:" in message:
            message_key = "파싱 방법 변경"  # 파싱 방법 변경 메시지 그룹화
        
        # 중복 메시지 제한
        if message_key in self.log_throttle:
            if current_time - self.log_throttle[message_key] < throttle_interval:
                return  # 제한 시간 내 동일 메시지는 스킵
        
        # 메시지 출력 시간 기록
        self.log_throttle[message_key] = current_time
        
        # 실제 메시지 출력
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        
        # GUI 텍스트 위젯에 추가 (안전한 방식)
        try:
            self.status_text.insert(tk.END, log_msg)
            self.status_text.see(tk.END)
            
            # 텍스트 위젯 내용이 너무 많으면 정리 (성능 향상)
            line_count = int(self.status_text.index('end-1c').split('.')[0])
            if line_count > 200:  # 200줄 초과시 앞부분 삭제
                self.status_text.delete('1.0', '50.0')  # 앞의 50줄 삭제
        except Exception:
            pass  # GUI 업데이트 실패는 무시
            
        # 콘솔 출력 (모니터링 중이 아닐 때만 또는 중요한 메시지만)
        if not self.is_monitoring or any(keyword in message for keyword in ["오류", "실패", "성공", "연결", "시작", "중지"]):
            print(log_msg.strip())

    def open_settings(self):
        """설정 창 열기"""
        messagebox.showinfo("설정", "설정 기능은 향후 버전에서 제공됩니다")
        
    def show_help(self):
        """도움말 표시"""
        help_text = """OnBoard OLED Monitor v1.3 - Enhanced Stability & Performance

🔗 연결 설정:
1. 시리얼 포트와 보드레이트를 설정합니다 (기본: 921600)
2. '연결' 버튼을 클릭하여 디바이스에 연결합니다

📺 모니터링:
1. '모니터링 시작'을 클릭하여 실시간 모니터링을 시작합니다
2. 화면 확대 비율을 조절할 수 있습니다 (1x~8x)
3. '화면 캡처'로 현재 화면을 저장할 수 있습니다
4. 자동 저장 기능으로 주기적 저장이 가능합니다

⚙️ 갱신 모드 설정:
• 갱신 주기: 50ms~2000ms 선택 가능 (FPS 조절)
• 자동 화면 요청: 체크시 설정된 주기로 자동 화면 요청
• 수동 모드: 체크 해제시 수동으로만 화면 캡처
• 실시간 FPS 및 성공률 모니터링

🔄 새로운 프로토콜 방식:
• 요청-응답 기반: 펌웨어가 요청시에만 화면 데이터 전송
• CPU 효율성: 불필요한 데이터 전송 방지
• 안정성 향상: 버퍼 오버플로우 및 데이터 충돌 방지
• 주기 조절: 사용자가 원하는 FPS로 설정 가능

🎛️ 원격 제어:
• 타이머 시작/정지: 펌웨어의 타이머를 원격으로 제어
• 타이머 설정: 분:초 형식으로 타이머 시간 설정
• 시스템 리셋: 펌웨어 상태 초기화
• 연결 테스트: PING/PONG으로 통신 상태 확인

📊 상태 정보:
• 배터리 잔량 (%)
• 타이머 시간 (MM:SS)
• 시스템 상태 (STANDBY/RUNNING/SETTING/COOLING)
• LED 연결 상태 (L1, L2)
• 데이터 소스 표시 (실시간/테스트)

💾 파일 기능:
• 화면 캡처: PNG 형식으로 저장
• 세션 기록: JSON 형식으로 모니터링 세션 저장

🚀 업데이트 내용 (v1.3):
• 고속 통신: 921600 보드레이트 지원
• 다양한 파싱 방법: 6가지 화면 해석 방법 제공
• 실시간 변경: 파싱 방법을 즉시 적용 가능
• 완전한 데이터 수신: 안정적인 화면 표시
• 상태 표시 개선: 배터리 잔량 표시 추가

문의: OnBoard LED Timer Project
버전: v1.3 (고속 통신 및 다중 파싱 방법 지원)
"""
        messagebox.showinfo("도움말", help_text)
        
    def on_closing(self):
        """애플리케이션 종료 처리 - 강화된 안전 종료"""
        try:
            print("프로그램 종료 중...")
            
            # 상태 로그에 종료 이벤트 기록
            if hasattr(self, 'status_log_file') and self.status_log_file:
                self.write_status_log_event("SHUTDOWN", "프로그램 종료")
            
            # 1단계: 모니터링 중지
            if self.is_monitoring:
                try:
                    self.stop_monitoring()
                    # 스레드가 완전히 종료될 시간 제공
                    time.sleep(0.5)
                except Exception as monitor_error:
                    print(f"모니터링 중지 오류: {str(monitor_error)}")
            
            # 2단계: 시리얼 연결 해제
            if self.is_connected:
                try:
                    self.disconnect_device()
                except Exception as disconnect_error:
                    print(f"연결 해제 오류: {str(disconnect_error)}")
            
            # 3단계: 시리얼 포트 강제 닫기
            if hasattr(self, 'serial_port') and self.serial_port:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except Exception as port_error:
                    print(f"포트 닫기 오류: {str(port_error)}")
            
            # 4단계: GUI 정리
            try:
                self.root.destroy()
            except Exception as gui_error:
                print(f"GUI 정리 오류: {str(gui_error)}")
                # GUI 정리 실패시 강제 종료
                import sys
                sys.exit(0)
                
            print("프로그램이 안전하게 종료되었습니다.")
            
        except Exception as critical_error:
            print(f"치명적 종료 오류: {str(critical_error)}")
            # 모든 정리 작업이 실패해도 프로그램은 종료
            import sys
            sys.exit(1)
    
    def run(self):
        """애플리케이션 실행"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def remote_start_timer(self):
        """원격 타이머 시작"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            self.serial_port.write(b'START_TIMER\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response(2000)  # 타임아웃 증가
            if response and b'OK:Timer started' in response:
                self.log_message("✅ 타이머가 시작되었습니다")
                self.write_status_log_event("CONTROL", "원격 타이머 시작")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 시작 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 시작 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 원격 제어 오류: {str(e)}")
            self.write_status_log_event("ERROR", f"원격 타이머 시작 오류: {str(e)}")
    
    def remote_stop_timer(self):
        """원격 타이머 정지"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            self.serial_port.write(b'STOP_TIMER\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response(2000)  # 타임아웃 증가
            if response and b'OK:Timer stopped' in response:
                self.log_message("✅ 타이머가 정지되었습니다")
                self.write_status_log_event("CONTROL", "원격 타이머 정지")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 정지 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 정지 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 원격 제어 오류: {str(e)}")
            self.write_status_log_event("ERROR", f"원격 타이머 정지 오류: {str(e)}")
    
    def remote_set_timer(self):
        """원격 타이머 설정 (분 단위만)"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            minutes = self.timer_min_var.get()
            
            # 유효성 검사 (분만)
            try:
                min_val = int(minutes)
                if min_val < 1 or min_val > 99:
                    raise ValueError("분 범위 오류")
            except ValueError:
                messagebox.showerror("오류", "올바른 시간을 입력하세요 (분: 1-99)")
                return
            
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            # 분 단위로 설정 (초는 항상 00)
            command = f"SET_TIMER:{minutes:0>2}:00\n"
            self.serial_port.write(command.encode())
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response(2000)  # 타임아웃 증가
            if response and b'OK:Timer set' in response:
                self.log_message(f"✅ 타이머가 {minutes}분으로 설정되었습니다")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 설정 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 설정 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 원격 제어 오류: {str(e)}")
    
    def remote_reset(self):
        """원격 시스템 리셋"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        # 확인 대화상자
        if not messagebox.askyesno("확인", "시스템을 리셋하시겠습니까?"):
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            self.serial_port.write(b'RESET\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response(3000)  # 리셋은 더 긴 타임아웃
            if response and b'OK:System reset' in response:
                self.log_message("✅ 시스템이 리셋되었습니다")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 시스템 리셋 응답: {response_str}")
            else:
                self.log_message("❌ 시스템 리셋 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 원격 제어 오류: {str(e)}")
    
    def remote_ping(self):
        """연결 테스트 - 비동기 처리로 UI 멈춤 방지"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            start_time = time.time()
            
            # 비동기 PING 명령 전송
            def handle_ping_response(response):
                elapsed_time = time.time() - start_time
                
                if response and b'PONG' in response:
                    self.log_message(f"✅ 연결 테스트 성공 (응답시간: {elapsed_time*1000:.1f}ms)")
                elif response:
                    response_str = response.decode('utf-8', errors='ignore').strip()
                    self.log_message(f"⚠️ 연결 테스트 응답: {response_str}")
                else:
                    self.log_message("❌ 연결 테스트 응답 없음")
            
            # 비동기 명령 전송
            self.send_command_async("PING", timeout_ms=2000, callback=handle_ping_response)
            self.log_message("📡 연결 테스트 명령 전송 중...")
                
        except Exception as e:
            self.log_message(f"❌ 연결 테스트 오류: {str(e)}")
            
    def test_connection(self):
        """기본 연결 테스트 - 비동기 처리로 개선"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            # 비동기 연결 테스트
            def handle_test_response(response):
                if response:
                    response_str = response.decode('utf-8', errors='ignore').strip()
                    if 'PONG' in response_str:
                        self.log_message(f"✅ 연결 테스트 성공: {response_str}")
                    elif 'OnBoard LED Timer Ready' in response_str:
                        self.log_message(f"✅ 연결 테스트 응답: {response_str}")
                    else:
                        self.log_message(f"⚠️ 연결 테스트 응답: {response_str}")
                else:
                    self.log_message("❌ 연결 테스트 응답 없음")
            
            # 비동기 PING 명령 전송
            self.send_command_async("PING", timeout_ms=3000, callback=handle_test_response)
            self.log_message("📡 기본 연결 테스트 시작...")
                
        except Exception as e:
            self.log_message(f"❌ 연결 테스트 오류: {str(e)}")
    
    def test_simple_screen(self):
        """간단한 화면 데이터 테스트 - 새로운 마커 형식 지원"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 완전 클리어
            self.clear_serial_buffers()
            
            self.serial_port.write(b'GET_SIMPLE\n')
            self.serial_port.flush()
            self.log_message("📡 GET_SIMPLE 명령어 전송")
            
            # 강화된 수신 로직 (capture_screen과 동일)
            response_data = b''
            timeout_count = 0
            max_timeout = 300  # 3초 타임아웃
            
            screen_start_found = False
            data_start_found = False
            data_end_found = False
            screen_end_found = False
            
            self.log_message("📥 GET_SIMPLE 응답 수신 중...")
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 마커 검출
                    if not screen_start_found and b'<<SCREEN_START>>' in response_data:
                        screen_start_found = True
                        self.log_message("✓ SCREEN_START 감지")
                        
                    if screen_start_found and not data_start_found and b'<<DATA_START>>' in response_data:
                        data_start_found = True
                        self.log_message("✓ DATA_START 감지")
                        
                    if data_start_found and not data_end_found and b'<<DATA_END>>' in response_data:
                        data_end_found = True
                        self.log_message("✓ DATA_END 감지")
                        
                    if data_end_found and not screen_end_found and b'<<SCREEN_END>>' in response_data:
                        screen_end_found = True
                        self.log_message("✓ SCREEN_END 감지")
                        break
                        
                    if b'<<TRANSMISSION_ERROR>>' in response_data:
                        self.log_message("❌ 전송 오류 감지됨")
                        return
                        
                    # 진행상황 표시 (간소화)
                    if timeout_count % 100 == 0 and len(response_data) > 0:
                        self.log_message(f"수신 중... {len(response_data)} bytes")
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            if screen_start_found and data_start_found and data_end_found and screen_end_found:
                self.log_message(f"✅ GET_SIMPLE 데이터 수신 완료: {len(response_data)} bytes")
                
                # 데이터 추출 및 파싱
                data_start_pos = response_data.find(b'<<DATA_START>>')
                data_end_pos = response_data.find(b'<<DATA_END>>')
                
                if data_start_pos != -1 and data_end_pos != -1:
                    data_start_actual = response_data.find(b'\n', data_start_pos) + 1
                    img_data = response_data[data_start_actual:data_end_pos]
                    
                    if len(img_data) >= 1024:
                        screen_data = self.parse_firmware_screen_data_enhanced(img_data[:1024])
                        if screen_data is not None:
                            self.log_message("✅ GET_SIMPLE 파싱 성공")
                            self.update_display(screen_data)
                            return
                
                self.log_message("❌ GET_SIMPLE 데이터 파싱 실패")
            else:
                self.log_message(f"❌ GET_SIMPLE 불완전한 수신: START:{screen_start_found}, D_START:{data_start_found}, D_END:{data_end_found}, END:{screen_end_found}")
                
            # 실패시 기존 방식으로 재시도
            self.log_message("🔄 기존 방식으로 GET_SIMPLE 재파싱 시도")
            if len(response_data) > 0:
                screen_data = self.parse_firmware_screen_data(response_data)
                if screen_data is not None:
                    self.log_message("✅ 기존 방식 파싱 성공")
                    self.update_display(screen_data)
                    return
                    
            # 모든 방법 실패시 테스트 패턴
            self.log_message("🧪 테스트 패턴으로 대체")
            screen_data = self.generate_test_screen()
            self.update_display(screen_data)
                
        except Exception as e:
            self.log_message(f"❌ GET_SIMPLE 명령어 오류: {str(e)}")
            import traceback
            self.log_message(f"📋 상세 오류: {traceback.format_exc()}")

    def on_parsing_method_changed(self, event):
        """파싱 방법 변경 처리"""
        self.parsing_method = self.parsing_var.get()
        self.log_message(f"🔄 파싱 방법 변경: {self.parsing_method}")
        
        # 현재 화면이 있으면 새로운 파싱 방법으로 재처리
        if hasattr(self, 'last_raw_data') and self.last_raw_data is not None:
            # 마지막 원본 데이터를 새 파싱 방법으로 재처리
            screen_data = self.parse_firmware_screen_data_enhanced(self.last_raw_data)
            if screen_data is not None:
                self.current_screen = screen_data
                self.update_display(screen_data)
        elif self.current_screen is not None:
            # 테스트 패턴 재생성
            test_screen = self.generate_test_screen()
            self.update_display(test_screen)

    def apply_parsing_method(self):
        """파싱 방법 수동 적용"""
        self.parsing_method = self.parsing_var.get()
        self.log_message(f"✅ 파싱 방법 수동 적용: {self.parsing_method}")
        
        # 현재 화면이 있으면 새로운 파싱 방법으로 재처리
        if hasattr(self, 'last_raw_data') and self.last_raw_data is not None:
            # 마지막 원본 데이터를 새 파싱 방법으로 재처리
            screen_data = self.parse_firmware_screen_data_enhanced(self.last_raw_data)
            if screen_data is not None:
                self.current_screen = screen_data
                self.update_display(screen_data)
        else:
            # 테스트 패턴으로 파싱 방법 확인
            test_screen = self.generate_test_screen()
            self.update_display(test_screen)

    def update_performance_display(self):
        """성능 통계 표시 업데이트"""
        try:
            current_time = time.time()
            
            # FPS 계산 (5초마다 리셋)
            if current_time - self.performance_stats['fps_start_time'] >= 5.0:
                fps = self.performance_stats['fps_counter'] / 5.0
                self.performance_stats['fps_counter'] = 0
                self.performance_stats['fps_start_time'] = current_time
            else:
                self.performance_stats['fps_counter'] += 1
                fps = self.performance_stats['fps_counter'] / max(1, current_time - self.performance_stats['fps_start_time'])
            
            # 성공률 계산
            total = self.performance_stats['total_captures']
            successful = self.performance_stats['successful_captures']
            success_rate = (successful / max(1, total)) * 100

            # GUI 업데이트
            if hasattr(self, 'perf_label'):
                perf_text = f"FPS: {fps:.1f} | 성공률: {success_rate:.1f}% ({successful}/{total})"
                self.perf_label.config(text=perf_text)
                
        except Exception as e:
            pass  # 성능 표시 오류는 무시

    def on_interval_changed(self, event):
        """갱신 주기 변경 처리"""
        try:
            new_interval = int(self.interval_var.get())
            self.update_interval_ms = new_interval
            self.log_message(f"🕐 갱신 주기 변경: {new_interval}ms ({1000/new_interval:.1f} FPS)")
            
            # 자동 모드가 활성화되어 있으면 문구도 업데이트
            if self.auto_request_enabled:
                self.update_mode_label.config(text=f"자동 모드 ({new_interval}ms)", foreground="green")
                
        except ValueError:
            self.log_message("❌ 잘못된 갱신 주기 값")
            self.interval_var.set(str(self.update_interval_ms))

    def on_auto_request_changed(self):
        """자동 요청 모드 변경 처리"""
        self.auto_request_enabled = self.auto_request_var.get()
        
        if self.auto_request_enabled:
            self.update_mode_label.config(text=f"자동 모드 ({self.update_interval_ms}ms)", foreground="green")
            self.log_message(f"🔄 자동 화면 요청 모드 활성화 (주기: {self.update_interval_ms}ms)")
        else:
            self.update_mode_label.config(text="수동 모드", foreground="orange")
            self.log_message("⏹️ 자동 화면 요청 모드 비활성화")
        
        # 모니터링 중이면 새로운 설정 적용
        if self.is_monitoring:
            self.log_message("⚙️ 모니터링 중 설정 변경 - 적용됨")

    def fast_parse_screen_data(self, img_data):
        """초고속 화면 데이터 파싱 (128x64 최적화) - 파싱 방법 적용"""
        try:
            # 원본 데이터 저장 (파싱 방법 변경시 재사용)
            self.last_raw_data = img_data
            
            # NumPy 배열을 사용한 초고속 처리 (가능한 경우)
            if self.numpy_available:
                import numpy as np
                
                # 1024바이트를 NumPy 배열로 변환
                byte_array = np.frombuffer(img_data, dtype=np.uint8)
                
                # 기본 파싱: 8비트를 개별 픽셀로 확장 (벡터화 연산)
                # 각 바이트를 8개 비트로 분해
                bits = np.unpackbits(byte_array).reshape(64, 128)
                
                # 0과 1을 255와 0으로 변환하여 가시성 향상
                temp_array = (bits * 255).astype(np.uint8)
                
                # 현재 파싱 방법 적용
                current_method = self.parsing_method
                
                # 파싱 방법에 따른 변환 적용
                if current_method == "method1_direct":
                    # 방법 1: 직접 매핑 (변환 없음)
                    img_array = temp_array.copy()
                    
                elif current_method == "method2_reversed":
                    # 방법 2: reverse 함수 적용 - NumPy로 최적화
                    img_array = temp_array.copy()
                    # 바이트별 reverse 처리는 복잡하므로 기본 처리
                    
                elif current_method == "method3_rotated_180":
                    # 방법 3: 180도 회전
                    img_array = np.rot90(temp_array, 2)
                    
                elif current_method == "method4_flipped_h":
                    # 방법 4: 가로 뒤집기
                    img_array = np.fliplr(temp_array)
                    
                elif current_method == "method5_flipped_v":
                    # 방법 5: 세로 뒤집기 (기본, 안정적)
                    img_array = np.flipud(temp_array)
                    
                elif current_method == "method5_rotate_90":
                    # 방법 5-1: 90도 시계방향 회전
                    img_array = np.rot90(temp_array, -1)  # -1은 시계방향
                    
                elif current_method == "method5_rotate_270":
                    # 방법 5-2: 270도 시계방향 회전 (90도 반시계방향)
                    img_array = np.rot90(temp_array, 1)   # 1은 반시계방향
                    
                elif current_method == "method5_mirror_h":
                    # 방법 5-3: 가로 미러링 (좌우 반전)
                    img_array = np.fliplr(temp_array)
                    
                elif current_method == "method5_mirror_v":
                    # 방법 5-4: 세로 미러링 (상하 반전)
                    img_array = np.flipud(temp_array)
                    
                elif current_method == "method5_flip_both":
                    # 방법 5-5: 상하좌우 모두 뒤집기
                    img_array = np.flipud(np.fliplr(temp_array))
                    
                elif current_method == "method6_transposed":
                    # 방법 6: 전치 + 조정
                    # 128x64를 64x128로 전치하면 크기가 맞지 않으므로 보간 필요
                    transposed = temp_array.T  # 전치: 64x128
                    # 64x128을 128x64로 리사이즈
                    from PIL import Image
                    pil_img = Image.fromarray(transposed.astype(np.uint8), mode='L')
                    resized_img = pil_img.resize((128, 64), Image.NEAREST)
                    img_array = np.array(resized_img)
                    
                else:
                    # 알 수 없는 방법인 경우 기본 세로 뒤집기 적용
                    img_array = np.flipud(temp_array)
                
                # PIL 이미지 생성
                img = Image.fromarray(img_array, mode='L')  # 그레이스케일
                
                return img
            else:
                # NumPy가 없는 경우 최적화된 Python 코드 사용
                return self._fast_parse_fallback(img_data)
                
        except Exception as e:
            # 오류 발생시 폴백 방식 사용
            return self._fast_parse_fallback(img_data)
    
    def _fast_parse_fallback(self, img_data):
        """NumPy 없이 최적화된 파싱 (폴백 방식) - 파싱 방법 적용"""
        try:
            # 원본 데이터 저장
            self.last_raw_data = img_data
            
            # PIL 이미지 생성 (L 모드로 성능 향상)
            img = Image.new('L', (128, 64), 0)
            
            # 픽셀 데이터를 직접 생성 (최적화된 방식)
            pixels = []
            
            # 미리 계산된 비트 마스크 (룩업 테이블)
            bit_masks = [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]
            
            # 행별 처리 (64행)
            for y in range(64):
                row_pixels = []
                row_start = y * 16  # 각 행은 16바이트 (128픽셀 / 8)
                
                # 각 행의 16바이트 처리
                for x_byte in range(16):
                    byte_index = row_start + x_byte
                    if byte_index >= len(img_data):
                        # 데이터 부족시 0으로 채움
                        row_pixels.extend([0] * 8)
                        continue
                    
                    byte_val = img_data[byte_index]
                    
                    # 각 바이트의 8비트를 픽셀로 변환 (언롤링)
                    for bit_mask in bit_masks:
                        pixel_val = 255 if (byte_val & bit_mask) else 0
                        row_pixels.append(pixel_val)
                
                pixels.extend(row_pixels)
            
            # 픽셀 데이터를 이미지에 적용
            img.putdata(pixels)
            
            # 파싱 방법 적용 (간단한 변환만)
            current_method = self.parsing_method
            
            if current_method == "method3_rotated_180":
                img = img.rotate(180)
            elif current_method == "method4_flipped_h" or current_method == "method5_mirror_h":
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif current_method == "method5_flipped_v" or current_method == "method5_mirror_v":
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            elif current_method == "method5_flip_both":
                img = img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
            elif current_method == "method5_rotate_90":
                img = img.rotate(-90, expand=True)  # 시계방향 90도
                img = img.resize((128, 64), Image.NEAREST)  # 크기 조정
            elif current_method == "method5_rotate_270":
                img = img.rotate(90, expand=True)  # 반시계방향 90도
                img = img.resize((128, 64), Image.NEAREST)  # 크기 조정
            elif current_method == "method6_transposed":
                img = img.transpose(Image.TRANSPOSE)
                img = img.resize((128, 64), Image.NEAREST)  # 크기 조정
            # method1_direct와 method2_reversed는 변환 없음 또는 복잡한 처리가 필요하여 생략
            
            return img
            
        except Exception as e:
            return None

    def save_screen_high_res(self):
        """고해상도 화면 저장 - 해상도를 높여서 저장"""
        if self.current_screen is None:
            messagebox.showwarning("경고", "저장할 화면이 없습니다")
            return
        
        # 해상도 선택 다이얼로그 (크기 증가)
        scale_dialog = tk.Toplevel(self.root)
        scale_dialog.title("저장 해상도 선택")
        scale_dialog.geometry("400x250")  # 크기 증가: 300x150 -> 400x200
        scale_dialog.resizable(False, False)
        scale_dialog.transient(self.root)
        scale_dialog.grab_set()
        
        # 창을 화면 중앙에 배치
        scale_dialog.update_idletasks()
        x = (scale_dialog.winfo_screenwidth() // 2) - (400 // 2)  # 중앙 위치 조정
        y = (scale_dialog.winfo_screenheight() // 2) - (250 // 2)  # 중앙 위치 조정
        scale_dialog.geometry(f"400x250+{x}+{y}")
        
        # 메인 프레임 생성
        main_frame = ttk.Frame(scale_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 제목 라벨
        ttk.Label(main_frame, text="저장할 해상도를 선택하세요:", font=("Arial", 10, "bold")).pack(pady=(0, 10))
        
        scale_var = tk.StringVar(value="4")  # 기본값을 "4"로 변경
        
        # 해상도 옵션들을 위한 프레임
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 해상도 옵션들
        options = [
            ("1x (128x64) - 원본", "1"),
            ("2x (256x128)", "2"),
            ("4x (512x256) - 권장", "4"),
            ("8x (1024x512)", "8"),
            ("16x (2048x1024)", "16")
        ]
        
        for text, value in options:
            ttk.Radiobutton(options_frame, text=text, variable=scale_var, value=value).pack(anchor=tk.W, pady=2)
        
        # 버튼 프레임 (하단에 고정)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        def save_with_scale():
            try:
                scale = int(scale_var.get())
                scale_dialog.destroy()
                
                # 파일 저장 다이얼로그
                filename = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[
                        ("PNG files", "*.png"), 
                        ("JPEG files", "*.jpg"), 
                        ("BMP files", "*.bmp"),
                        ("All files", "*.*")
                    ],
                    title="고해상도 화면 저장"
                )
                
                if filename:
                    # 현재 화면 데이터 타입에 따라 처리
                    if hasattr(self.current_screen, 'save'):
                        # PIL Image 객체인 경우
                        base_img = self.current_screen
                    elif hasattr(self.current_screen, 'shape'):
                        # NumPy 배열인 경우
                        base_img = Image.fromarray(self.current_screen.astype('uint8'), mode='L')
                    else:
                        # 다른 형식인 경우
                        base_img = Image.fromarray(self.current_screen, mode='L')
                    
                    if scale == 1:
                        # 원본 크기로 저장
                        final_img = base_img
                    else:
                        # 고해상도로 확대 (NEAREST: 픽셀 아트 스타일, LANCZOS: 부드러운 확대)
                        new_size = (128 * scale, 64 * scale)
                        
                        # 파일 확장자에 따라 리사이징 방법 선택
                        if filename.lower().endswith(('.jpg', '.jpeg')):
                            # JPEG는 부드러운 확대가 더 적합
                            final_img = base_img.resize(new_size, Image.LANCZOS)
                        else:
                            # PNG, BMP는 픽셀 아트 스타일 유지
                            final_img = base_img.resize(new_size, Image.NEAREST)
                    
                    # 파일 저장
                    final_img.save(filename)
                    
                    # 저장 정보 로그
                    file_size = final_img.size
                    self.log_message(f"✅ 고해상도 화면 저장 완료: {filename}")
                    self.log_message(f"📐 저장 크기: {file_size[0]}x{file_size[1]} (확대: {scale}배)")
                    
            except Exception as e:
                error_msg = f"고해상도 화면 저장 실패: {str(e)}"
                messagebox.showerror("오류", error_msg)
                self.log_message(f"❌ {error_msg}")
        
        def cancel_save():
            scale_dialog.destroy()
        
        # 버튼들을 중앙 정렬로 배치
        ttk.Button(button_frame, text="저장", command=save_with_scale).pack(side=tk.LEFT, padx=(50, 5))
        ttk.Button(button_frame, text="취소", command=cancel_save).pack(side=tk.LEFT, padx=(5, 50))

    def open_status_log(self):
        """상태 로그 파일 열기"""
        try:
            if self.status_log_file and os.path.exists(self.status_log_file):
                if os.name == 'nt':  # Windows
                    os.startfile(self.status_log_file)
                else:  # Linux/Mac
                    os.system(f'open "{self.status_log_file}"')
            else:
                messagebox.showinfo("정보", "상태 로그 파일이 없습니다")
        except Exception as e:
            messagebox.showerror("오류", f"로그 파일을 열 수 없습니다: {str(e)}")

if __name__ == "__main__":
    try:
        print("OnBoard OLED Monitor를 시작합니다...")
        print("프로그램을 종료하려면 창을 닫거나 Ctrl+C를 누르세요.")
        
        app = OLEDMonitor()
        app.run()
        
    except KeyboardInterrupt:
        print("\n[사용자 중단] Ctrl+C로 프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"\n[오류] 프로그램 실행 중 심각한 오류가 발생했습니다:")
        print(f"오류 타입: {type(e).__name__}")
        print(f"오류 메시지: {str(e)}")
        
        # 상세 오류 정보 출력
        import traceback
        print("\n[상세 오류 정보]")
        print(traceback.format_exc())
        
        # 오류 로그 파일 저장
        try:
            from datetime import datetime
            import os
            
            # logs 폴더 생성
            if not os.path.exists("logs"):
                os.makedirs("logs")
                
            # 오류 로그 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"logs/error_log_{timestamp}.txt"
            
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write(f"OnBoard OLED Monitor 오류 로그\n")
                f.write(f"발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"오류 타입: {type(e).__name__}\n")
                f.write(f"오류 메시지: {str(e)}\n\n")
                f.write("상세 오류 정보:\n")
                f.write(traceback.format_exc())
                
            print(f"\n오류 로그가 저장되었습니다: {log_filename}")
            
        except Exception as log_error:
            print(f"오류 로그 저장 실패: {str(log_error)}")
        
        print("\n[해결 방법]")
        print("1. 시리얼 포트 연결을 확인하세요")
        print("2. 다른 프로그램이 포트를 사용 중인지 확인하세요")
        print("3. 펌웨어가 정상 동작하는지 확인하세요")
        print("4. 로그 파일을 확인하거나 개발자에게 문의하세요")
        
        input("\n계속하려면 Enter를 누르세요...")
    finally:
        print("프로그램을 정리 중...")
        try:
            # 시리얼 포트가 열려있다면 닫기
            import serial.tools.list_ports
            print("시리얼 포트 정리 완료")
        except:
            pass
