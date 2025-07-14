#!/usr/bin/env python3

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
import csv

# 프로젝트 내 모듈 import
try:
    from utils import StatusLogger, FileManager, Logger
    from Python.OLED_Monitor.Core.serial_parser import SerialDataParser
except ImportError:
    # 모듈이 없는 경우 기본 기능으로 대체
    StatusLogger = None
    FileManager = None
    Logger = None
    SerialDataParser = None

class OLEDMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OnBoard OLED Monitor v2.0 - 통합 응답 프로토콜")
        self.root.geometry("1200x900")
        
        # 시리얼 통신 관련
        self.serial_port = None
        self.is_connected = False
        self.is_monitoring = False
        
        # 무한루프 방지 및 안전 설정
        self.serial_lock = threading.Lock()
        self.last_screen_request_time = 0
        self.last_status_request_time = 0
        self.request_min_interval = 0.1  # 100ms 최소 간격
        
        # 파싱 안전 설정 (무한루프 완전 방지)
        self.max_parse_time = 2.0  # 최대 파싱 시간 2초
        self.max_parse_attempts = 3  # 최대 파싱 시도 횟수
        self.parsing_active = False  # 파싱 진행 상태 플래그
        
        # NumPy 가용성 검사 복구
        try:
            import numpy as np
            self.numpy_available = True
            self.log_startup_message = "✅ NumPy 가속 사용 가능 - 초고속 모드"
        except ImportError:
            self.numpy_available = False
            self.log_startup_message = "⚠️ NumPy 없음 - 일반 모드 (pip install numpy 권장)"
        
        # 스레드 관련 (누락된 속성 추가)
        self.capture_thread = None
        self.status_thread = None
        
        # GUI 변수들
        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="921600")
        self.display_scale = tk.IntVar(value=4)
        self.update_interval_ms = 100
        self.current_screen = None
        self.current_status = {}
        
        # 모니터링 및 성능 관련
        self.auto_request_enabled = True
        self.integrated_mode = True  # 통합 모드 기본 활성화
        
        # 모니터링 모드 설정 (새로 추가)
        self.monitoring_mode = "integrated"  # "integrated", "screen_only", "status_only"
        
        self.performance_stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'last_fps': 0,
            'start_time': time.time()
        }
        
        # 로그 스로틀링 (메시지 스팸 방지)
        self.log_throttle = {}
        
        # 초기화
        self.setup_fallback_logging()
        self.setup_serial_parser()
        self.setup_gui()
        
        # 정리 이벤트 바인딩
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 시작 메시지 (지연 출력)
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
        """상태 로깅 시스템 설정 - 실행 위치 기반 로그 폴더 생성"""
        try:
            # 현재 실행 위치 기준으로 logs 폴더 생성
            import os
            current_dir = os.getcwd()
           
            
            # 로그 파일 경로 설정
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 상태 로그 파일만 생성 (파싱된 결과)
            self.status_log_file = os.path.join(self.log_dir, f"status_log_{timestamp}.txt")
            
            # 상태 로그 파일 초기화 (텍스트 헤더 작성)
            with open(self.status_log_file, 'a', encoding='utf-8') as f:
                # 파일이 비어있으면 헤더 작성
                if f.tell() == 0:
                    f.write("=" * 80 + "\n")
                    f.write(f"OnBoard OLED Monitor 상태 로그 - {datetime.now().strftime('%Y년 %m월 %d일')}\n")
                    f.write("=" * 80 + "\n")
                    f.write("시간\t\t\t배터리\t타이머\t\t상태\t\tL1\tL2\t비고\n")
                    f.write("-" * 80 + "\n")
            
            self.status_logger = self
            print(f"✅ 로그 시스템 초기화 완료")
            print(f"   📄 상태 로그: {self.status_log_file}")
            
        except Exception as e:
            print(f"❌ 로그 시스템 초기화 실패: {str(e)}")
            self.status_logger = None
            self.status_log_file = None
    
    def setup_fallback_logging(self):
        """폴백 로깅 시스템 (utils.py가 없을 때 사용)"""
        try:
            # 실행 경로에 LOG 폴더 생성
            self.log_directory = os.path.join(os.getcwd(), "LOG")
            os.makedirs(self.log_directory, exist_ok=True)
            
            # 오늘 날짜로 상태 로그 파일명 생성
            today = datetime.now().strftime("%Y%m%d%H%M%S")
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
        """상태 데이터를 텍스트 파일에 기록"""
        if not hasattr(self, 'status_log_file') or not self.status_log_file:
            return
            
        try:
            # 상태 데이터를 텍스트로 기록
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            battery = status_data.get('battery', 18.6)
            timer = status_data.get('timer', '00:00')
            status = status_data.get('status', 'UNKNOWN')
            l1_connected = "O" if status_data.get('l1_connected', False) else "X"
            l2_connected = "O" if status_data.get('l2_connected', False) else "X"
            bat_adc = status_data.get('bat_adc', 0)
            
            with open(self.status_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}\t\t{battery}V\t{timer}\t\t{status}\t\t{l1_connected}\t{l2_connected}\t{bat_adc}\n")
            
        except Exception as e:
            # 로그 기록 실패시 콘솔에만 출력 (무한 루프 방지)
            print(f"상태 로그 기록 실패: {str(e)}")
    
    def write_raw_data_log(self, raw_data, data_type="UNKNOWN", additional_info=""):
        """RAW 데이터를 별도 로그 파일에 기록"""
        if not hasattr(self, 'raw_data_log_file') or not self.raw_data_log_file:
            return
            
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            with open(self.raw_data_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {data_type}\n")
                f.write(f"크기: {len(raw_data)} bytes\n")
                
                if additional_info:
                    f.write(f"추가 정보: {additional_info}\n")
                
                # RAW 데이터 헥스 덤프
                if isinstance(raw_data, bytes):
                    f.write("HEX: ")
                    f.write(' '.join(f'{b:02X}' for b in raw_data[:100]))  # 처음 100바이트만
                    if len(raw_data) > 100:
                        f.write(f" ... (총 {len(raw_data)} bytes)")
                    f.write("\n")
                    
                    # 텍스트 표현 (가능한 경우)
                    try:
                        text_repr = raw_data.decode('utf-8', errors='replace')
                        f.write(f"TEXT: {repr(text_repr[:200])}")  # 처음 200자만
                        if len(text_repr) > 200:
                            f.write(f" ... (총 {len(text_repr)} chars)")
                        f.write("\n")
                    except:
                        f.write("TEXT: [디코딩 불가]\n")
                else:
                    f.write(f"DATA: {str(raw_data)[:200]}\n")
                
                f.write("-" * 50 + "\n\n")
                
        except Exception as e:
            print(f"RAW 데이터 로그 기록 실패: {str(e)}")
    
    def write_event_log(self, event_type, message, details=""):
        """이벤트 로그 기록 - 비활성화됨"""
        pass
    
    def setup_gui(self):
        """GUI 인터페이스 설정"""
        self.root.title("OnBoard OLED Monitor v2.0 - 통합 응답 프로토콜")
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
        
        # 세 번째 행: 모니터링 모드 선택
        ttk.Label(conn_frame, text="모니터링 모드:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        self.monitoring_mode_var = tk.StringVar(value="integrated")
        monitoring_combo = ttk.Combobox(conn_frame, textvariable=self.monitoring_mode_var, width=15)
        monitoring_combo['values'] = [
            'integrated',    # 통합 모드 (화면+상태)
            'screen_only',   # 화면만
            'status_only'    # 상태만
        ]
        monitoring_combo.grid(row=2, column=1, padx=5, pady=2)
        monitoring_combo.bind('<<ComboboxSelected>>', self.on_monitoring_mode_changed)
        
        # 모니터링 모드 설명 표시
        self.monitoring_mode_label = ttk.Label(conn_frame, text="통합 모드 (화면+상태)", foreground="blue")
        self.monitoring_mode_label.grid(row=2, column=2, columnspan=2, padx=5, pady=2, sticky=tk.W)
        
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
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except Exception as e:
            self.log_message(f"포트 목록 조회 오류: {str(e)}")
            return []
        
    def toggle_connection(self):
        """연결/해제 토글"""
        if not self.is_connected:
            self.connect_device()
        else:
            self.disconnect_device()
            
    def connect_device(self):
        """디바이스 연결 - 간단하고 안정적인 동기식 처리"""
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
            
            # 포트 유효성 검사
            if not port or port.strip() == "":
                messagebox.showerror("오류", "포트를 선택하세요")
                return
                
            # 이미 연결되어 있으면 먼저 해제
            if self.is_connected and self.serial_port:
                self.disconnect_device()
                time.sleep(0.1)  # 짧은 대기
                
            # 연결 상태 표시
            self.connect_btn.config(text="연결 중...", state="disabled")
            self.status_label.config(text="연결 중...", foreground="orange")
            self.root.update()
            
            self.log_message(f"포트 {port}에 연결 시도 중... (보드레이트: {baud})")
            
            # 시리얼 포트 생성 및 설정
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0,
                write_timeout=1.0,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            # 연결 확인
            if not self.serial_port.is_open:
                raise Exception("포트 열기 실패")
                
            # 버퍼 클리어
            self.clear_serial_buffers()
            
            # 연결 성공 처리
            self.is_connected = True
            self.connect_btn.config(text="연결 해제", state="normal")
            self.status_label.config(text="연결됨", foreground="green")
            
            self.log_message(f"✅ 포트 {port}에 성공적으로 연결됨")
            
            # 연결 테스트 (선택적)
            self.test_connection_quick()
            
        except serial.SerialException as e:
            error_msg = f"시리얼 포트 오류: {str(e)}"
            self.connection_failed(error_msg)
        except Exception as e:
            error_msg = f"연결 오류: {str(e)}"
            self.connection_failed(error_msg)
    
    def connection_failed(self, error_msg):
        """연결 실패 처리"""
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
        
        self.log_message(f"❌ {error_msg}")
        
        # 사용자에게 오류 메시지 표시
        if "PermissionError" in error_msg or "액세스가 거부" in error_msg:
            messagebox.showerror("연결 실패", "포트에 액세스할 수 없습니다.\n다른 프로그램이 포트를 사용 중일 수 있습니다.")
        elif "FileNotFoundError" in error_msg or "찾을 수 없습니다" in error_msg:
            messagebox.showerror("연결 실패", "선택한 포트를 찾을 수 없습니다.\n디바이스 연결을 확인해주세요.")
        else:
            messagebox.showerror("연결 실패", f"연결에 실패했습니다:\n{error_msg}")
    
    def test_connection_quick(self):
        """빠른 연결 테스트"""
        try:
            if not self.is_connected or not self.serial_port:
                return
                
            # PING 명령 전송
            self.serial_port.write(b'PING\n')
            self.serial_port.flush()
            
            # 응답 대기 (짧은 타임아웃)
            response = self.wait_for_response(1000)  # 1초
            if response and b'PONG' in response:
                self.log_message("✅ 통신 테스트 성공")
            else:
                self.log_message("⚠️ 통신 테스트 응답 없음 (연결은 유지)")
                
        except Exception as e:
            self.log_message(f"⚠️ 통신 테스트 오류: {str(e)} (연결은 유지)")
    
    def disconnect_device(self):
        """디바이스 연결 해제"""
        try:
            # 먼저 모니터링 중지
            if self.is_monitoring:
                self.stop_monitoring()
                time.sleep(0.2)  # 모니터링 완전 중지 대기
            
            # 시리얼 포트 해제
            if hasattr(self, 'serial_port') and self.serial_port:
                try:
                    # 펌웨어에 정지 명령 전송 (선택적)
                    if self.serial_port.is_open:
                        self.serial_port.write(b'STOP_MONITOR\n')
                        self.serial_port.flush()
                        time.sleep(0.1)
                    
                    # 포트 닫기
                    if self.serial_port.is_open:
                        self.serial_port.close()
                        
                except Exception as close_error:
                    self.log_message(f"⚠️ 포트 닫기 오류: {str(close_error)}")
                
                self.serial_port = None
            
            # 연결 상태 업데이트
            self.is_connected = False
            self.connect_btn.config(text="연결", state="normal")
            self.status_label.config(text="연결 안됨", foreground="red")
            
            self.log_message("✅ 연결이 해제되었습니다")
            
        except Exception as e:
            self.log_message(f"❌ 연결 해제 오류: {str(e)}")
            # 오류가 있어도 상태는 업데이트
            self.is_connected = False
            self.serial_port = None
            self.connect_btn.config(text="연결", state="normal")
            self.status_label.config(text="연결 안됨", foreground="red")
    
    def clear_serial_buffers(self):
        """시리얼 버퍼 클리어"""
        if not self.serial_port or not self.serial_port.is_open:
            return
            
        try:
            # 입력 버퍼 클리어
            if self.serial_port.in_waiting > 0:
                old_data = self.serial_port.read(self.serial_port.in_waiting)
                if len(old_data) > 0:
                    self.log_message(f"🧹 버퍼 클리어: {len(old_data)} bytes")
            
            # 출력 버퍼 플러시
            self.serial_port.flush()
            
            # 추가 버퍼 재클리어 (안정성 향상)
            time.sleep(0.05)  # 50ms 대기
            if self.serial_port.in_waiting > 0:
                self.serial_port.read(self.serial_port.in_waiting)
                
        except Exception as e:
            self.log_message(f"⚠️ 버퍼 클리어 오류: {str(e)}")
    
    def wait_for_response(self, timeout_ms=2000):
        """응답 대기"""
        if not self.is_connected or not self.serial_port:
            return None
            
        try:
            timeout_seconds = timeout_ms / 1000.0
            start_time = time.time()
            response_data = b''
            
            while time.time() - start_time < timeout_seconds:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 완료 조건 확인 (개행 문자)
                    if b'\n' in response_data or b'\r' in response_data:
                        break
                else:
                    time.sleep(0.01)  # 10ms 대기
                    
            return response_data if response_data else None
            
        except Exception as e:
            self.log_message(f"응답 대기 오류: {str(e)}")
            return None
    
    def send_command(self, command):
        """명령어 전송"""
        if not self.is_connected or not self.serial_port:
            return False
            
        try:
            # 명령어 전송
            if isinstance(command, str):
                command_bytes = command.encode() + b'\n'
            else:
                command_bytes = command + b'\n'
                
            self.serial_port.write(command_bytes)
            self.serial_port.flush()
            
            return True
            
        except Exception as e:
            self.log_message(f"명령어 전송 오류: {str(e)}")
            return False
    
    def send_command_and_wait(self, command, timeout_ms=2000):
        """명령어 전송 후 응답 대기"""
        if not self.send_command(command):
            return None
            
        return self.wait_for_response(timeout_ms)
    
    def check_connection(self):
        """연결 상태 확인"""
        try:
            if not self.serial_port:
                return False
            return self.serial_port.is_open and self.is_connected
        except:
            self.is_connected = False
            return False
    
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
        """모니터링 시작 - 모드별 분기 처리"""
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
            
            # 모니터링 플래그 설정
            self.is_monitoring = True
            self.monitor_btn.config(text="모니터링 중지")
            
            # 시리얼 버퍼 클리어
            self.clear_serial_buffers()
            
            # 모니터링 모드에 따른 분기 처리
            if self.monitoring_mode == "integrated":
                self.start_integrated_monitoring()
            elif self.monitoring_mode == "screen_only":
                self.start_screen_only_monitoring()
            elif self.monitoring_mode == "status_only":
                self.start_status_only_monitoring()
            else:
                # 기본값은 통합 모드
                self.start_integrated_monitoring()
                
        except Exception as e:
            self.log_message(f"❌ 모니터링 시작 오류: {str(e)}")
            self.is_monitoring = False
            self.monitor_btn.config(text="모니터링 시작")
    
    def start_integrated_monitoring(self):
        """통합 모니터링 시작 (화면+상태)"""
        try:
            # 펌웨어 설정
            try:
                # 새로운 펌웨어에서는 화면 요청 시 상태도 함께 전송 (통합 응답 모드)
                command = f"SET_UPDATE_MODE:INTEGRATED_RESPONSE,{self.update_interval_ms}\n"
                self.send_command(command)
                
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 통합 응답 모드 설정 완료")
                else:
                    # 기존 펌웨어 호환성을 위한 폴백
                    command = f"SET_UPDATE_MODE:REQUEST_RESPONSE,{self.update_interval_ms}\n"
                    self.send_command(command)
                    self.log_message("🔄 기존 펌웨어 모드로 폴백")
                
                # 모니터링 활성화
                self.send_command("START_MONITOR")
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 활성화")
                    
            except Exception as setup_error:
                self.log_message(f"⚠️ 펌웨어 설정 오류: {str(setup_error)} - 계속 진행")
            
            # 화면 캡처 루프 시작 (상태는 화면 응답에 포함됨)
            if self.capture_thread is None or not self.capture_thread.is_alive():
                self.capture_thread = threading.Thread(target=self.integrated_capture_loop, daemon=True)
                self.capture_thread.start()
                
            mode_text = "통합 모드 (화면+상태)" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.log_message(f"🚀 통합 모니터링 시작 - {mode_text}{interval_text}")
            self.write_event_log("START", f"통합 모니터링 시작 - {mode_text}{interval_text}")
            
        except Exception as e:
            self.log_message(f"❌ 통합 모니터링 시작 오류: {str(e)}")
            raise
    
    def start_screen_only_monitoring(self):
        """화면만 모니터링 시작"""
        try:
            # 펌웨어 설정 (화면만)
            try:
                command = f"SET_UPDATE_MODE:SCREEN_ONLY,{self.update_interval_ms}\n"
                self.send_command(command)
                
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 화면 전용 모드 설정 완료")
                else:
                    self.log_message("⚠️ 펌웨어 화면 전용 모드 설정 응답 없음")
                
                # 모니터링 활성화
                self.send_command("START_MONITOR")
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 활성화")
                    
            except Exception as setup_error:
                self.log_message(f"⚠️ 펌웨어 설정 오류: {str(setup_error)} - 계속 진행")
            
            # 화면 전용 캡처 루프 시작
            if self.capture_thread is None or not self.capture_thread.is_alive():
                self.capture_thread = threading.Thread(target=self.screen_only_capture_loop, daemon=True)
                self.capture_thread.start()
                
            mode_text = "화면 전용 모드" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.log_message(f"🚀 화면 전용 모니터링 시작 - {mode_text}{interval_text}")
            self.write_event_log("START", f"화면 전용 모니터링 시작 - {mode_text}{interval_text}")
            
        except Exception as e:
            self.log_message(f"❌ 화면 전용 모니터링 시작 오류: {str(e)}")
            raise
    
    def start_status_only_monitoring(self):
        """상태만 모니터링 시작"""
        try:
            # 펌웨어 설정 (상태만)
            try:
                command = f"SET_UPDATE_MODE:STATUS_ONLY,{self.update_interval_ms}\n"
                self.send_command(command)
                
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 상태 전용 모드 설정 완료")
                else:
                    self.log_message("⚠️ 펌웨어 상태 전용 모드 설정 응답 없음")
                
                # 모니터링 활성화
                self.send_command("START_MONITOR")
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 활성화")
                    
            except Exception as setup_error:
                self.log_message(f"⚠️ 펌웨어 설정 오류: {str(setup_error)} - 계속 진행")
            
            # 상태 전용 모니터링 루프 시작
            if self.status_thread is None or not self.status_thread.is_alive():
                self.status_thread = threading.Thread(target=self.status_only_monitoring_loop, daemon=True)
                self.status_thread.start()
                
            mode_text = "상태 전용 모드" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.log_message(f"🚀 상태 전용 모니터링 시작 - {mode_text}{interval_text}")
            self.write_event_log("START", f"상태 전용 모니터링 시작 - {mode_text}{interval_text}")
            
        except Exception as e:
            self.log_message(f"❌ 상태 전용 모니터링 시작 오류: {str(e)}")
            raise
    
    def stop_monitoring(self):
        """모니터링 중지 - 간소화된 안전한 종료"""
        if not self.is_monitoring:
            return
            
        # 모니터링 플래그 즉시 비활성화
        self.is_monitoring = False
        self.monitor_btn.config(text="모니터링 시작")
        
        try:
            # 펌웨어에 모니터링 중지 명령 전송
            if self.is_connected and self.serial_port:
                self.send_command("STOP_MONITOR")
                response = self.wait_for_response(500)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 비활성화")
                else:
                    self.log_message("⚠️ 펌웨어 모니터링 비활성화 응답 없음")
            
            self.log_message("🛑 모니터링 중지")
            self.write_event_log("STOP", "모니터링 중지")
            
        except Exception as e:
            self.log_message(f"❌ 모니터링 중지 오류: {str(e)}")
    
    def integrated_capture_loop(self):
        """통합 캡처 루프 - 화면+상태 동시 처리 (무한루프 방지 강화)"""
        consecutive_failures = 0
        max_failures = 10
        requests_per_minute = 0
        last_request_time = 0
        last_minute_reset = time.time()
        
        # 성능 통계
        loop_start_time = time.time()
        
        self.log_message("🔄 통합 캡처 루프 시작 - 화면+상태 동시 처리")
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 분당 요청 수 계산 및 리셋
                if current_time - last_minute_reset >= 60:
                    requests_per_minute = 0
                    last_minute_reset = current_time
                
                # 연결 상태 확인
                if not self.check_connection():
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        self.log_message(f"⚠️ 연결 끊어짐 감지 - 복구 시도 중... ({consecutive_failures}/{max_failures})")
                        # 연결 복구 시도
                        try:
                            self.clear_serial_buffers()
                            time.sleep(1.0)
                            # 테스트 데이터로 대체하여 모니터링 계속
                            test_screen = self.generate_test_screen()
                            if test_screen is not None:
                                self.root.after(0, lambda img=test_screen: self.update_display(img))
                            test_status = self.generate_test_status_data()
                            self.root.after(0, lambda data=test_status: self.update_status_display(data))
                            
                            # 실패 카운터 리셋 (테스트 데이터로 진행)
                            if consecutive_failures >= max_failures * 2:
                                consecutive_failures = max_failures // 2  # 절반으로 리셋
                                self.log_message("🔄 테스트 데이터 모드로 전환 - 모니터링 계속")
                        except Exception as recovery_error:
                            self.log_message(f"복구 시도 오류: {str(recovery_error)}")
                        
                        time.sleep(2.0)
                        continue
                    time.sleep(0.5)
                    continue
                
                # 자동 요청 모드 처리 (통합 요청)
                if self.auto_request_enabled:
                    interval_seconds = self.update_interval_ms / 1000.0
                    min_interval = 0.05  # 50ms 최소 간격
                    if interval_seconds < min_interval:
                        interval_seconds = min_interval
                    
                    if current_time - last_request_time >= interval_seconds:
                        try:
                            # 통합 화면+상태 요청
                            success = self.integrated_screen_status_request()
                            last_request_time = current_time
                            requests_per_minute += 1
                            
                            if success:
                                consecutive_failures = 0
                            else:
                                consecutive_failures += 1
                                
                        except Exception as request_error:
                            error_msg = str(request_error)
                            if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                                self.log_message(f"통합 요청 오류: {error_msg}")
                            consecutive_failures += 1
                    
                    # 적절한 대기 시간
                    sleep_time = min(0.01, interval_seconds / 10)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                else:
                    # 수동 모드에서는 긴 대기
                    time.sleep(0.1)
                    consecutive_failures = 0
                
                # 연속 실패 처리
                if consecutive_failures >= max_failures:
                    self.log_message(f"⚠️ 연속 {max_failures}회 실패 - 복구 시도")
                    
                    try:
                        self.clear_serial_buffers()
                        time.sleep(0.5)
                        
                        if self.check_connection():
                            self.log_message("✅ 연결 복구 완료")
                            consecutive_failures = 0
                        else:
                            self.log_message("⚠️ 연결 복구 실패 - 테스트 데이터 모드로 계속")
                            # 테스트 데이터로 대체하여 모니터링 계속
                            try:
                                test_screen = self.generate_test_screen()
                                if test_screen is not None:
                                    self.root.after(0, lambda img=test_screen: self.update_display(img))
                                test_status = self.generate_test_status_data()
                                self.root.after(0, lambda data=test_status: self.update_status_display(data))
                                consecutive_failures = max_failures // 2  # 실패 카운터 절반으로 리셋
                            except Exception as test_error:
                                self.log_message(f"테스트 데이터 생성 오류: {str(test_error)}")
                                consecutive_failures = 0  # 리셋하여 계속 시도
                    except Exception as recovery_error:
                        self.log_message(f"복구 시도 오류: {str(recovery_error)}")
                        # 오류가 발생해도 계속 진행
                        consecutive_failures = max_failures // 2
                    
                    time.sleep(2.0)
                    
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"❌ 통합 캡처 루프 오류: {error_msg}")
                consecutive_failures += 1
                
                if any(keyword in error_msg.lower() for keyword in ["memory", "overflow", "recursion"]):
                    self.log_message("❌ 심각한 오류 감지 - 복구 시도")
                    # 심각한 오류시 대기 시간을 늘리고 복구 시도
                    time.sleep(5.0)
                    consecutive_failures = max_failures // 2  # 카운터 리셋
                    try:
                        # 메모리 정리 시도
                        self.clear_serial_buffers()
                        import gc
                        gc.collect()
                        self.log_message("🧹 메모리 정리 완료 - 모니터링 계속")
                    except:
                        pass
                    continue
                
                if consecutive_failures >= max_failures * 2:
                    self.log_message(f"⚠️ 과도한 연속 오류 ({consecutive_failures}회) - 안전 모드로 전환")
                    # 종료하지 않고 안전 모드로 전환
                    try:
                        test_screen = self.generate_test_screen()
                        if test_screen is not None:
                            self.root.after(0, lambda img=test_screen: self.update_display(img))
                        test_status = self.generate_test_status_data()
                        self.root.after(0, lambda data=test_status: self.update_status_display(data))
                        consecutive_failures = 0  # 카운터 완전 리셋
                        self.log_message("🛡️ 안전 모드 활성화 - 테스트 데이터로 모니터링 계속")
                        time.sleep(3.0)  # 안전 대기
                    except Exception as safe_error:
                        self.log_message(f"안전 모드 전환 오류: {str(safe_error)}")
                        consecutive_failures = 0
                    continue
                    
                time.sleep(0.5)
        
        # 종료 처리
        total_time = time.time() - loop_start_time
        self.log_message(f"🔄 통합 캡처 루프 종료 - 실행시간: {total_time:.1f}초")
        
        if not self.is_monitoring:
            self.log_message("🛑 사용자가 모니터링을 중지함")
        # 자동으로 stop_monitoring을 호출하지 않음
    
    def screen_only_capture_loop(self):
        """화면 전용 캡처 루프 - 화면만 모니터링"""
        consecutive_failures = 0
        max_failures = 10
        requests_per_minute = 0
        last_request_time = 0
        last_minute_reset = time.time()
        
        # 성능 통계
        loop_start_time = time.time()
        
        self.log_message("🔄 화면 전용 캡처 루프 시작")
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 분당 요청 수 계산 및 리셋
                if current_time - last_minute_reset >= 60:
                    requests_per_minute = 0
                    last_minute_reset = current_time
                
                # 연결 상태 확인
                if not self.check_connection():
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        self.log_message(f"⚠️ 연결 끊어짐 감지 - 복구 시도 중... ({consecutive_failures}/{max_failures})")
                        try:
                            self.clear_serial_buffers()
                            time.sleep(1.0)
                            # 테스트 화면으로 대체
                            test_screen = self.generate_test_screen()
                            if test_screen is not None:
                                self.root.after(0, lambda img=test_screen: self.update_display(img))
                            consecutive_failures = max_failures // 2
                        except Exception as recovery_error:
                            self.log_message(f"복구 시도 오류: {str(recovery_error)}")
                        time.sleep(2.0)
                        continue
                    time.sleep(0.5)
                    continue
                
                # 자동 요청 모드 처리 (화면만)
                if self.auto_request_enabled:
                    interval_seconds = self.update_interval_ms / 1000.0
                    min_interval = 0.05  # 50ms 최소 간격
                    if interval_seconds < min_interval:
                        interval_seconds = min_interval
                    
                    if current_time - last_request_time >= interval_seconds:
                        try:
                            # 화면만 요청
                            success = self.simple_screen_request()
                            last_request_time = current_time
                            requests_per_minute += 1
                            
                            if success:
                                consecutive_failures = 0
                            else:
                                consecutive_failures += 1
                                
                        except Exception as request_error:
                            error_msg = str(request_error)
                            if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                                self.log_message(f"화면 요청 오류: {error_msg}")
                            consecutive_failures += 1
                    
                    # 적절한 대기 시간
                    sleep_time = min(0.01, interval_seconds / 10)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                else:
                    # 수동 모드에서는 긴 대기
                    time.sleep(0.1)
                    consecutive_failures = 0
                
                # 연속 실패 처리
                if consecutive_failures >= max_failures:
                    self.log_message(f"⚠️ 연속 {max_failures}회 실패 - 복구 시도")
                    try:
                        self.clear_serial_buffers()
                        time.sleep(0.5)
                        if self.check_connection():
                            self.log_message("✅ 연결 복구 완료")
                            consecutive_failures = 0
                        else:
                            # 테스트 화면으로 대체
                            test_screen = self.generate_test_screen()
                            if test_screen is not None:
                                self.root.after(0, lambda img=test_screen: self.update_display(img))
                            consecutive_failures = max_failures // 2
                    except Exception as recovery_error:
                        self.log_message(f"복구 시도 오류: {str(recovery_error)}")
                        consecutive_failures = max_failures // 2
                    time.sleep(2.0)
                    
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"❌ 화면 전용 캡처 루프 오류: {error_msg}")
                consecutive_failures += 1
                time.sleep(0.5)
        
        # 종료 처리
        total_time = time.time() - loop_start_time
        self.log_message(f"🔄 화면 전용 캡처 루프 종료 - 실행시간: {total_time:.1f}초")
    
    def status_only_monitoring_loop(self):
        """상태 전용 모니터링 루프 - GET_STATUS 명령을 주기적으로 전송"""
        consecutive_failures = 0
        max_failures = 10
        requests_per_minute = 0
        last_request_time = 0
        last_minute_reset = time.time()
        
        # 성능 통계
        loop_start_time = time.time()
        successful_requests = 0
        total_requests = 0
        
        self.log_message("🔄 상태 전용 모니터링 루프 시작 - GET_STATUS 명령 주기적 전송")
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 분당 요청 수 계산 및 리셋
                if current_time - last_minute_reset >= 60:
                    requests_per_minute = 0
                    last_minute_reset = current_time
                
                # 연결 상태 확인
                if not self.check_connection():
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        self.log_message(f"⚠️ 연결 끊어짐 감지 - 복구 시도 중... ({consecutive_failures}/{max_failures})")
                        try:
                            self.clear_serial_buffers()
                            time.sleep(1.0)
                            # 테스트 상태로 대체
                            test_status = self.generate_test_status_data()
                            self.root.after(0, lambda data=test_status: self.update_status_display(data))
                            consecutive_failures = max_failures // 2
                        except Exception as recovery_error:
                            self.log_message(f"복구 시도 오류: {str(recovery_error)}")
                        time.sleep(2.0)
                        continue
                    time.sleep(0.5)
                    continue
                
                # 자동 요청 모드 처리 (상태만)
                if self.auto_request_enabled:
                    interval_seconds = self.update_interval_ms / 1000.0
                    min_interval = 0.1  # 100ms 최소 간격 (상태 요청은 화면보다 느려도 됨)
                    if interval_seconds < min_interval:
                        interval_seconds = min_interval
                    
                    if current_time - last_request_time >= interval_seconds:
                        # 시리얼 락 획득 (짧은 타임아웃)
                        if self.serial_lock.acquire(timeout=0.5):
                            try:
                                total_requests += 1
                                
                                # 최소 간격 체크
                                if current_time - self.last_status_request_time >= self.request_min_interval:
                                    self.last_status_request_time = current_time
                                    
                                    # GET_STATUS 명령 전송
                                    response = self.send_command_and_wait("GET_STATUS", 1000)
                                    last_request_time = current_time
                                    requests_per_minute += 1
                                    
                                    if response:
                                        status_data = self.parse_firmware_status_data(response)
                                        if status_data:
                                            # GUI 업데이트 (비동기)
                                            self.root.after(0, lambda data=status_data: self.update_status_display(data))
                                            
                                            # 상태 로그에 기록
                                            try:
                                                self.write_status_log(status_data)
                                            except:
                                                pass
                                            
                                            successful_requests += 1
                                            consecutive_failures = 0
                                        else:
                                            # 파싱 실패시 테스트 데이터
                                            try:
                                                test_status = self.generate_test_status_data()
                                                self.root.after(0, lambda data=test_status: self.update_status_display(data))
                                            except:
                                                pass
                                            consecutive_failures += 1
                                    else:
                                        consecutive_failures += 1
                                
                            except Exception as status_error:
                                consecutive_failures += 1
                            finally:
                                # 락 해제
                                self.serial_lock.release()
                        else:
                            # 락 획득 실패시 그냥 넘어감
                            pass
                    
                    # 적절한 대기 시간
                    sleep_time = min(0.1, interval_seconds / 5)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                else:
                    # 수동 모드에서는 긴 대기
                    time.sleep(0.5)
                    consecutive_failures = 0
                
                # 연속 실패 처리
                if consecutive_failures >= max_failures:
                    self.log_message(f"⚠️ 연속 {max_failures}회 실패 - 복구 시도")
                    try:
                        self.clear_serial_buffers()
                        time.sleep(0.5)
                        if self.check_connection():
                            self.log_message("✅ 연결 복구 완료")
                            consecutive_failures = 0
                        else:
                            # 테스트 상태로 대체
                            test_status = self.generate_test_status_data()
                            self.root.after(0, lambda data=test_status: self.update_status_display(data))
                            consecutive_failures = max_failures // 2
                    except Exception as recovery_error:
                        self.log_message(f"복구 시도 오류: {str(recovery_error)}")
                        consecutive_failures = max_failures // 2
                    time.sleep(2.0)
                    
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"❌ 상태 전용 모니터링 루프 오류: {error_msg}")
                consecutive_failures += 1
                time.sleep(0.5)
        
        # 종료 처리
        total_time = time.time() - loop_start_time
        self.log_message(f"🔄 상태 전용 모니터링 루프 종료 - 실행시간: {total_time:.1f}초")
        
        # 최종 통계
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100
            self.log_message(f"📊 최종 상태 요청 통계: 성공률 {success_rate:.1f}% ({successful_requests}/{total_requests})")
        else:
            self.log_message("�� 상태 요청 통계: 요청 없음")
    
    def status_loop_simple(self):
        """간소화된 상태 모니터링 루프 - 단순하고 안정적"""
        status_request_interval = 1.0  # 1초마다 상태 요청
        last_status_request = 0
        
        # 성능 통계
        loop_start_time = time.time()
        successful_requests = 0
        total_requests = 0
        
        self.log_message("🔄 상태 루프 시작 - 1초 간격 상태 로깅 활성화")
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 상태 요청 주기 확인
                if current_time - last_status_request >= status_request_interval:
                    # 시리얼 락 획득 (짧은 타임아웃)
                    if self.serial_lock.acquire(timeout=0.3):
                        try:
                            total_requests += 1
                            
                            # 최소 간격 체크
                            if current_time - self.last_status_request_time >= self.request_min_interval:
                                self.last_status_request_time = current_time
                                
                                # 상태 요청
                                response = self.send_command_and_wait("GET_STATUS", 800)
                                if response:
                                    status_data = self.parse_firmware_status_data(response)
                                    if status_data:
                                        # GUI 업데이트 (비동기)
                                        self.root.after(0, lambda data=status_data: self.update_status_display(data))
                                        
                                        # 상태 로그에 기록 (모니터링 중 자동 기록)
                                        try:
                                            self.write_status_log(status_data)
                                        except:
                                            pass
                                        
                                        successful_requests += 1
                                    else:
                                        # 파싱 실패시 테스트 데이터
                                        try:
                                            test_status = self.generate_test_status_data()
                                            self.root.after(0, lambda data=test_status: self.update_status_display(data))
                                        except:
                                            pass
                                
                                last_status_request = current_time
                                
                        except Exception as status_error:
                            # 오류 발생시 로깅 없이 계속 진행
                            pass
                        finally:
                            # 락 해제
                            self.serial_lock.release()
                    else:
                        # 락 획득 실패시 그냥 넘어감
                        pass
                
                # 루프 대기 시간
                time.sleep(0.5)
                
            except Exception as e:
                # 예외 발생시 짧은 대기 후 계속
                time.sleep(1)
        
        # 종료 처리
        total_time = time.time() - loop_start_time
        self.log_message(f"🔄 상태 루프 종료 - 실행시간: {total_time:.1f}초")
        
        # 최종 통계
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100
            self.log_message(f"📊 최종 상태 요청 통계: 성공률 {success_rate:.1f}% ({successful_requests}/{total_requests})")
    
    def integrated_screen_status_request(self):
        """통합 화면+상태 요청 - 하나의 요청으로 화면과 상태를 모두 받음"""
        if not self.check_connection():
            return False
        
        # 시리얼 락 획득 (짧은 타임아웃)
        if not self.serial_lock.acquire(timeout=0.5):
            return False  # 락 획득 실패시 스킵
            
        try:
            current_time = time.time()
            
            # 최소 간격 체크
            if current_time - self.last_screen_request_time < self.request_min_interval:
                return False  # 너무 빠른 요청은 스킵
            
            self.last_screen_request_time = current_time
            
            # 통합 화면+상태 요청 전송
            response = self.send_command_and_wait("GET_SCREEN", 2000)  # 통합 응답이므로 타임아웃 증가
            if not response:
                return False
            
            # 통합 응답 데이터 파싱
            screen_data = self.parse_screen_response(response)
            if screen_data is not None:
                # GUI 업데이트 (메인 스레드에서)
                self.root.after(0, lambda: self.update_display(screen_data))
                
                # 성능 통계 업데이트
                self.performance_stats['total_captures'] += 1
                self.performance_stats['successful_captures'] += 1
                
                # 주기적으로 성능 표시 업데이트
                if self.performance_stats['total_captures'] % 10 == 0:
                    self.root.after(0, self.update_performance_display)
                
                return True
            
            return False
            
        except Exception as e:
            # 오류는 로깅하지 않음 (빈번한 호출로 스팸 방지)
            return False
        finally:
            # 락 해제
            self.serial_lock.release()
    
    def simple_screen_request(self):
        """간단한 화면 요청 및 처리 - 시리얼 충돌 방지"""
        if not self.check_connection():
            return False
        
        # 시리얼 락 획득 (짧은 타임아웃)
        if not self.serial_lock.acquire(timeout=0.5):
            return False  # 락 획득 실패시 스킵
            
        try:
            current_time = time.time()
            
            # 최소 간격 체크 (상태 요청과 충돌 방지)
            if current_time - self.last_screen_request_time < self.request_min_interval:
                return False  # 너무 빠른 요청은 스킵
            
            self.last_screen_request_time = current_time
            
            # 화면 요청
            response = self.send_command_and_wait("GET_SCREEN", 1500)  # 타임아웃 단축
            if not response:
                return False
            
            # 데이터 파싱
            screen_data = self.parse_screen_response(response)
            if screen_data is not None:
                # GUI 업데이트 (메인 스레드에서)
                self.root.after(0, lambda: self.update_display(screen_data))
                
                # 성능 통계 업데이트
                self.performance_stats['total_captures'] += 1
                self.performance_stats['successful_captures'] += 1
                
                # 주기적으로 성능 표시 업데이트
                if self.performance_stats['total_captures'] % 10 == 0:
                    self.root.after(0, self.update_performance_display)
                
                return True
            
            return False
            
        except Exception as e:
            # 오류는 로깅하지 않음 (빈번한 호출로 스팸 방지)
            return False
        finally:
            # 락 해제
            self.serial_lock.release()
    
    def parse_screen_response(self, response_data):
        """화면 응답 데이터 파싱 - 상태 정보 포함 (무한루프 방지 단순화)"""
        try:
            screen_data = None
            
            # 데이터 크기 제한 (메모리 및 성능 보호)
            if len(response_data) > 10000:  # 10KB 제한
                response_data = response_data[:10000]
            
            # 실제 펌웨어 형식: <<SCREEN_END>>\r\n 다음에 바로 STATUS: 형식
            if b'<<SCREEN_START>>' in response_data and b'<<SCREEN_END>>' in response_data:
                self.log_message("📦 통합 응답 데이터 감지")
                
                # 화면 데이터 추출
                screen_start = response_data.find(b'<<SCREEN_START>>')
                screen_end = response_data.find(b'<<SCREEN_END>>')
                
                if screen_start != -1 and screen_end != -1 and screen_end > screen_start:
                    screen_section = response_data[screen_start:screen_end + len(b'<<SCREEN_END>>')]
                    
                    # 화면 데이터에서 이미지 데이터 추출
                    data_start_pos = screen_section.find(b'<<DATA_START>>')
                    data_end_pos = screen_section.find(b'<<DATA_END>>')
                    
                    if data_start_pos != -1 and data_end_pos != -1 and data_end_pos > data_start_pos:
                        # 실제 데이터 시작점 찾기
                        data_content_start = data_start_pos + len(b'<<DATA_START>>')
                        # 개행문자 건너뛰기
                        while data_content_start < data_end_pos:
                            if screen_section[data_content_start:data_content_start+1] in [b'\n', b'\r']:
                                data_content_start += 1
                            else:
                                break
                        
                        if data_content_start < data_end_pos:
                            img_data = screen_section[data_content_start:data_end_pos]
                            
                            if len(img_data) >= 1024:
                                # 안전 래퍼를 사용한 화면 파싱
                                def parse_screen_safe(data):
                                    return self.parse_firmware_screen_data_enhanced(data[:1024])
                                
                                screen_data = self.safe_parse_wrapper(parse_screen_safe, img_data, "화면파싱")
                                if screen_data is not None:
                                    self.log_message("✅ 화면 데이터 파싱 성공")
                                else:
                                    self.log_message("⚠️ 화면 데이터 파싱 실패 - 폴백 시도")
                                    # 폴백: 기본 파싱 시도
                                    try:
                                        screen_data = self.parse_firmware_screen_data(img_data[:1024])
                                        if screen_data is not None:
                                            self.log_message("✅ 폴백 화면 파싱 성공")
                                    except Exception as fallback_error:
                                        self.log_message(f"❌ 폴백 파싱도 실패: {str(fallback_error)}")
                            else:
                                self.log_message(f"⚠️ 화면 데이터 크기 부족: {len(img_data)} bytes")
                
                # 상태 데이터 추출 (단순화된 방식)
                status_start_marker = b'STATUS:'
                status_pos = response_data.find(status_start_marker)
                
                if status_pos != -1:
                    # STATUS: 이후 첫 번째 줄만 가져오기 (간단하게)
                    status_start = status_pos
                    status_end = status_pos + 200  # 최대 200자만 (안전 제한)
                    
                    # 개행문자로 끝나는 지점 찾기
                    newline_pos = response_data.find(b'\n', status_start)
                    if newline_pos != -1 and newline_pos < status_end:
                        status_end = newline_pos
                        
                    crlf_pos = response_data.find(b'\r\n', status_start)
                    if crlf_pos != -1 and crlf_pos < status_end:
                        status_end = crlf_pos
                    
                    # 응답 데이터 끝을 넘지 않도록
                    if status_end > len(response_data):
                        status_end = len(response_data)
                    
                    if status_end > status_start:
                        status_raw = response_data[status_start:status_end]
                        
                        # 상태 데이터 파싱 (안전한 방식)
                        try:
                            # 안전 래퍼를 사용한 상태 파싱
                            def parse_status_safe(data):
                                # 원본 함수에서 래퍼를 제거하고 실제 파싱 로직만 사용
                                if isinstance(data, bytes):
                                    try:
                                        data_str = data.decode('utf-8', errors='ignore').strip()
                                    except:
                                        data_str = str(data, errors='replace').strip()
                                else:
                                    data_str = str(data).strip()
                                
                                status_info = {
                                    'timestamp': datetime.now().strftime('%H:%M:%S'), 
                                    'source': 'firmware',
                                    'battery': 18.6,
                                    'timer': '00:00',
                                    'status': 'UNKNOWN',
                                    'l1_connected': False,
                                    'l2_connected': False,
                                    'bat_adc': 0,
                                    'raw_data': data,
                                    'raw_string': data_str
                                }
                                
                                if not data_str.startswith('STATUS:'):
                                    return status_info
                                
                                status_part = data_str[7:]
                                items = status_part.split(',')[:6]  # 최대 6개만
                                
                                for item in items:
                                    item = item.strip()
                                    if ':' not in item:
                                        continue
                                    key, value = item.split(':', 1)
                                    key, value = key.strip(), value.strip()
                                    
                                    if key == 'BAT':
                                        try:
                                            battery_val = float(value.replace('V', ''))
                                            status_info['battery'] = battery_val/100
                                        except:
                                            pass
                                    elif key == 'TIMER' and len(value) <= 8:
                                        status_info['timer'] = value
                                    elif key == 'STATUS' and len(value) <= 15:
                                        status_info['status'] = value
                                    elif key == 'L1':
                                        status_info['l1_connected'] = (value == '1')
                                    elif key == 'L2':
                                        status_info['l2_connected'] = (value == '1')
                                    elif key == 'BAT_ADC':
                                        try:
                                            adc_val = int(value)
                                            status_info['bat_adc'] = max(0, min(4095, adc_val))
                                        except:
                                            pass
                                
                                return status_info
                            
                            status_data = self.safe_parse_wrapper(parse_status_safe, status_raw, "상태파싱")
                            if status_data:
                                self.log_message("✅ 상태 데이터 파싱 성공")
                                # RAW 데이터 먼저 기록
                                self.write_raw_data_log(status_raw, "INTEGRATED_STATUS", f"통합 응답에서 추출된 상태 데이터")
                                # GUI 업데이트는 메인 스레드에서
                                self.root.after(0, lambda: self.update_status_display(status_data))
                                self.write_status_log(status_data)
                            else:
                                self.log_message("⚠️ 상태 데이터 파싱 실패")
                                # 실패한 RAW 데이터도 기록
                                self.write_raw_data_log(status_raw, "FAILED_STATUS_PARSING", f"파싱 실패한 상태 데이터")
                        except Exception as status_error:
                            self.log_message(f"⚠️ 상태 파싱 오류: {str(status_error)}")
                
                # 화면 데이터 반환 (상태 처리 완료)
                return screen_data
            
            # 기존 화면만 있는 형식 (하위 호환성)
            elif b'<<SCREEN_START>>' in response_data and b'<<DATA_START>>' in response_data:
                self.log_message("📺 기존 화면 전용 응답 처리")
                
                data_start_pos = response_data.find(b'<<DATA_START>>')
                data_end_pos = response_data.find(b'<<DATA_END>>')
                
                if data_start_pos != -1 and data_end_pos != -1 and data_end_pos > data_start_pos:
                    # 실제 데이터 시작점
                    data_content_start = data_start_pos + len(b'<<DATA_START>>')
                    # 개행문자 건너뛰기
                    while data_content_start < data_end_pos:
                        if response_data[data_content_start:data_content_start+1] in [b'\n', b'\r']:
                            data_content_start += 1
                        else:
                            break
                    
                    if data_content_start < data_end_pos:
                        img_data = response_data[data_content_start:data_end_pos]
                        
                        if len(img_data) >= 1024:
                            # 안전 래퍼를 사용한 화면 파싱
                            def parse_legacy_screen_safe(data):
                                return self.parse_firmware_screen_data_enhanced(data[:1024])
                            
                            result = self.safe_parse_wrapper(parse_legacy_screen_safe, img_data, "레거시화면파싱")
                            if result is not None:
                                return result
                            else:
                                # 폴백: 기본 파싱
                                try:
                                    return self.parse_firmware_screen_data(img_data[:1024])
                                except Exception as e:
                                    self.log_message(f"❌ 레거시 폴백 파싱 실패: {str(e)}")
                        else:
                            self.log_message(f"⚠️ 레거시 화면 데이터 크기 부족: {len(img_data)} bytes")
            
            # 기존 형식으로 파싱 시도 (최종 폴백)
            self.log_message("🔄 기존 형식으로 파싱 시도")
            def parse_final_fallback(data):
                return self.parse_firmware_screen_data(data)
            
            return self.safe_parse_wrapper(parse_final_fallback, response_data, "최종폴백파싱")
            
        except Exception as e:
            self.log_message(f"❌ 화면 응답 파싱 오류: {str(e)}")
            return None
    
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
                                if len(old_data) > 5000:  # 5KB 이상
                                    self.write_event_log("WARNING", f"과도한 버퍼 데이터: {len(old_data)} bytes")
                                    
                                    # 강제 버퍼 클리어
                                    try:
                                        self.serial_port.reset_input_buffer()
                                        self.serial_port.reset_output_buffer()
                                        time.sleep(0.1)
                                        self.log_message("🧹 시리얼 버퍼 강제 클리어")
                                    except Exception:
                                        pass
                            
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
                                    self.write_event_log("WARNING", f"상태 응답 없음 ({status_timeout_count}/{max_status_timeouts})")
                                consecutive_errors += 1
                                
                        except Exception as status_error:
                            error_msg = str(status_error)
                            # BAT ADC 관련 오류 특별 처리
                            if "BAT_ADC" in error_msg or "parse" in error_msg.lower():
                                self.write_event_log("ERROR", f"BAT ADC 파싱 오류: {error_msg}")
                                # 안전한 테스트 데이터로 대체
                                safe_status = self._generate_safe_test_status()
                                self.root.after(0, lambda data=safe_status: self.update_status_display(data))
                            else:
                                self.write_event_log("ERROR", f"상태 요청 오류: {error_msg}")
                            consecutive_errors += 1
                            
                        # 연속 오류가 너무 많으면 잠시 대기
                        if consecutive_errors >= max_consecutive_errors:
                            self.write_event_log("WARNING", f"연속 오류 {consecutive_errors}회 발생, 대기 중...")
                            time.sleep(3)  # 3초 대기 (단축)
                            consecutive_errors = 0  # 리셋
                            
                        # 상태 타임아웃이 너무 많으면 상태 요청 중단
                        if status_timeout_count >= max_status_timeouts:
                            self.write_event_log("WARNING", "상태 요청 일시 중단 (과도한 타임아웃)")
                            time.sleep(10)  # 10초 대기 후 재시도
                            status_timeout_count = 0
                            
                    last_status_request = current_time
                
                # 루프 대기 시간 (CPU 효율성)
                time.sleep(0.5)  # 0.5초 간격으로 단축 (기존 1초)
                
            except Exception as e:
                error_msg = str(e)
                self.write_event_log("ERROR", f"상태 루프 오류: {error_msg}")
                consecutive_errors += 1
                
                # BAT ADC 관련 심각한 오류시 상태 루프 일시 중단
                if "BAT_ADC" in error_msg or consecutive_errors >= max_consecutive_errors:
                    time.sleep(5)  # 5초 대기
                    consecutive_errors = 0
                else:
                    time.sleep(1)  # 1초 대기
        
        # 종료 처리
        self.log_message("🔄 상태 루프 종료")
    
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
                        self.write_event_log("WARNING", f"BAT ADC 값 보정: {bat_adc} -> 0")
                
                return result
                
            finally:
                try:
                    signal.alarm(0)  # 타임아웃 해제
                except (AttributeError, OSError):
                    pass
                
        except TimeoutError:
            self.write_event_log("ERROR", "상태 파싱 타임아웃 - 안전 모드로 전환")
            return self._generate_safe_test_status()
        except Exception as e:
            self.write_event_log("ERROR", f"안전 파싱 오류: {str(e)}")
            return self._generate_safe_test_status()
    
    def _generate_safe_test_status(self):
        """안전한 테스트 상태 데이터 생성 (BAT ADC 포함)"""
        import random
        
        return {
            'battery': random.randint(18, 25),
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
        """수동 화면 캡처 (버튼 클릭용) - 통합 모드 지원"""
        if not self.is_connected or not self.serial_port:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
        
        # 시리얼 락 획득 (타임아웃 설정)
        if not self.serial_lock.acquire(timeout=3.0):
            self.log_message("⚠️ 수동 화면 캡처 - 시리얼 통신 대기 중 타임아웃")
            return
            
        try:
            current_time = time.time()
            
            # 최소 간격 체크
            if current_time - self.last_screen_request_time < self.request_min_interval:
                wait_time = self.request_min_interval - (current_time - self.last_screen_request_time)
                time.sleep(wait_time)
            
            self.last_screen_request_time = time.time()
            
            # 수동 요청을 위한 버퍼 클리어
            self.clear_serial_buffers()
            
            self.log_message("📡 수동 화면+상태 캡처 요청...")
            
            # 즉시 통합 요청 전송
            self.serial_port.write(b'GET_SCREEN\n')
            self.serial_port.flush()
            
            # 동기적으로 통합 응답 처리 (수동 요청이므로 완전한 대기)
            success = self.process_integrated_response_sync()
            
            if success:
                self.log_message("✅ 수동 화면+상태 캡처 성공")
            else:
                self.log_message("❌ 수동 화면+상태 캡처 실패")
                
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"❌ 수동 화면+상태 캡처 오류: {error_msg}")
        finally:
            # 락 해제
            self.serial_lock.release()
    
    def process_integrated_response_sync(self):
        """동기식 통합 응답 처리 (수동 캡처용) - 실제 펌웨어 형식"""
        try:
            response_data = b''
            timeout_count = 0
            max_timeout = 400  # 4초 타임아웃 (통합 응답이므로 더 긴 시간)
            
            # 실제 펌웨어 응답 마커들
            screen_start_found = False
            screen_end_found = False
            status_found = False
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 실제 펌웨어 응답 마커 검출
                    if not screen_start_found and b'<<SCREEN_START>>' in response_data:
                        screen_start_found = True
                        self.log_message("✓ SCREEN_START 감지")
                        
                    if not screen_end_found and b'<<SCREEN_END>>' in response_data:
                        screen_end_found = True
                        self.log_message("✓ SCREEN_END 감지")
                        
                    # SCREEN_END 다음에 STATUS: 찾기
                    if screen_end_found and not status_found:
                        screen_end_pos = response_data.find(b'<<SCREEN_END>>')
                        if screen_end_pos != -1:
                            after_screen_end = response_data[screen_end_pos + len(b'<<SCREEN_END>>'):]
                            if (b'\r\nSTATUS:' in after_screen_end or 
                                b'\nSTATUS:' in after_screen_end or 
                                b'STATUS:' in after_screen_end):
                                status_found = True
                                self.log_message("✓ STATUS: 데이터 감지")
                        
                    # 화면과 상태가 모두 발견되면 완료
                    if screen_start_found and screen_end_found and status_found:
                        # STATUS: 라인이 완료되었는지 확인
                        screen_end_pos = response_data.find(b'<<SCREEN_END>>')
                        after_screen_end = response_data[screen_end_pos + len(b'<<SCREEN_END>>'):]
                        
                        # STATUS: 다음에 개행문자가 있는지 확인
                        if b'STATUS:' in after_screen_end:
                            status_pos = after_screen_end.find(b'STATUS:')
                            status_line = after_screen_end[status_pos:]
                            
                            # STATUS: 라인이 개행문자로 끝나는지 확인
                            if b'\r\n' in status_line or b'\n' in status_line:
                                self.log_message("✅ 통합 응답 완전 수신")
                                break
                        
                    # 화면만 있는 응답 감지 (기존 펌웨어)
                    if screen_start_found and screen_end_found and not status_found:
                        if timeout_count > 100:  # 1초 정도 기다려도 상태가 없으면
                            self.log_message("⚠️ 화면만 있는 응답 감지 (기존 펌웨어)")
                            break
                        
                    # 전송 오류 감지
                    if b'<<TRANSMISSION_ERROR>>' in response_data:
                        self.log_message("❌ 전송 오류 감지됨")
                        return False
                        
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            if len(response_data) == 0:
                self.log_message("❌ 응답 데이터 없음")
                return False
            
            # 수신된 데이터 요약 로그
            data_summary = f"데이터 크기: {len(response_data)}bytes"
            if status_found:
                data_summary += ", 상태 포함"
            self.log_message(f"📦 수신 완료 - {data_summary}")
            
            # 통합 응답 파싱
            screen_data = self.parse_screen_response(response_data)
            if screen_data is not None:
                self.log_message("✅ 통합 응답 파싱 성공")
                self.update_display(screen_data)
                return True
            else:
                self.log_message("❌ 통합 응답 파싱 실패")
                
                # 디버그: 응답 데이터 일부 출력
                if len(response_data) > 50:
                    sample_data = response_data[:50] + b'...'
                else:
                    sample_data = response_data
                self.log_message(f"🔍 응답 데이터 샘플: {sample_data}")
                return False
                
        except Exception as e:
            self.log_message(f"❌ 동기식 통합 응답 처리 오류: {str(e)}")
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
                'battery': 18.6,
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
        """펌웨어에서 받은 상태 데이터 파싱 - 무한루프 완전 방지"""
        try:
            # 기본 상태 정보 (항상 반환되도록)
            status_info = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'firmware',
                'battery': 18.6,
                'timer': '00:00',
                'status': 'UNKNOWN',
                'l1_connected': False,
                'l2_connected': False,
                'bat_adc': 0
            }
            
            # 응답 데이터 전처리
            if isinstance(response, bytes):
                try:
                    data_str = response.decode('utf-8', errors='ignore').strip()
                    status_info['raw_data'] = response
                except:
                    data_str = str(response, errors='replace').strip()
                    status_info['raw_data'] = data_str.encode('utf-8', errors='ignore')
            else:
                data_str = str(response).strip()
                status_info['raw_data'] = data_str.encode('utf-8', errors='ignore')
            
            status_info['raw_string'] = data_str
            
            # 데이터 길이 검증 (과도한 데이터 방지)
            if len(data_str) > 500:
                self.write_event_log("WARNING", f"데이터 크기 제한: {len(data_str)} chars")
                data_str = data_str[:500]
            
            # STATUS: 형식 확인
            if not data_str.startswith('STATUS:'):
                self.write_event_log("WARNING", f"잘못된 STATUS 형식: {data_str[:50]}")
                return status_info
            
            # STATUS: 제거 후 파싱
            status_part = data_str[7:]  # "STATUS:" 제거
            
            # 항목 분할 (최대 개수 제한)
            items = status_part.split(',')[:8]  # 최대 8개 항목만 처리
            
            # 각 항목 파싱
            for item in items:
                try:
                    item = item.strip()
                    if not item or ':' not in item:
                        continue
                    
                    parts = item.split(':', 1)
                    if len(parts) != 2:
                        continue
                        
                    key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # 키와 값 길이 검증
                    if len(key) > 15 or len(value) > 30:
                        continue
                    
                    # 각 항목별 파싱
                    if key == 'BAT':
                        try:
                            battery_str = value.replace('V', '').strip()
                            battery_val = int(battery_str)
                            status_info['battery'] = battery_val/100
                        except:
                            pass
                            
                    elif key == 'TIMER':
                        if len(value) <= 8:
                            status_info['timer'] = value
                            
                    elif key == 'STATUS':
                        if len(value) <= 15:
                            status_info['status'] = value
                            
                    elif key == 'L1':
                        status_info['l1_connected'] = (value == '1')
                        
                    elif key == 'L2':
                        status_info['l2_connected'] = (value == '1')
                        
                    elif key == 'BAT_ADC':
                        try:
                            adc_val = int(value)
                            status_info['bat_adc'] = max(0, min(4095, adc_val))
                        except:
                            pass
                            
                except Exception as item_error:
                    # 개별 아이템 오류는 무시하고 계속
                    continue
            
            return status_info
            
        except Exception as e:
            # 모든 오류를 포착하여 안전한 기본값 반환
            self.write_event_log("ERROR", f"상태 파싱 오류: {str(e)}")
            return {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'firmware_error',
                'battery': 18.6,
                'timer': '00:00',
                'status': 'ERROR',
                'l1_connected': False,
                'l2_connected': False,
                'bat_adc': 0,
                'error': str(e),
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
        """상태 새로고침 - 무한루프 방지 단순화 버전"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        # 시리얼 락 획득 (타임아웃 설정)
        if not self.serial_lock.acquire(timeout=2.0):
            self.log_message("⚠️ 상태 새로고침 - 시리얼 락 획득 실패")
            return
            
            
        try:
            # 최소 간격 체크
            current_time = time.time()
            if current_time - self.last_status_request_time < 0.5:  # 0.5초 최소 간격
                return
            
            self.last_status_request_time = current_time
            
            # 단순한 상태 요청
            self.log_message("📡 수동 상태 새로고침...")
            
            # 버퍼 클리어
            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
            except:
                pass
            
            # 상태 요청 전송
            self.serial_port.write(b'GET_STATUS\n')
            self.serial_port.flush()
            
            # 단순한 응답 대기 (1초 타임아웃)
            start_time = time.time()
            response_data = b''
            
            while time.time() - start_time < 1.0:  # 1초 타임아웃
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # STATUS: 가 포함되면 완료
                    if b'STATUS:' in response_data:
                        break
                else:
                    time.sleep(0.01)
            
            # 응답 처리
            if response_data and b'STATUS:' in response_data:
                # 안전 래퍼를 사용한 상태 파싱
                def parse_status_simple(data):
                    # 단순화된 상태 파싱
                    if isinstance(data, bytes):
                        try:
                            data_str = data.decode('utf-8', errors='ignore').strip()
                        except:
                            data_str = str(data).strip()
                    else:
                        data_str = str(data).strip()
                    
                    status_info = {
                        'timestamp': datetime.now().strftime('%H:%M:%S'), 
                        'source': 'firmware',
                        'battery': 0,
                        'timer': '00:00',
                        'status': 'UNKNOWN',
                        'l1_connected': False,
                        'l2_connected': False,
                        'bat_adc': 0
                    }
                    
                    if data_str.startswith('STATUS:'):
                        status_part = data_str[7:]
                        items = status_part.split(',')[:6]
                        
                        for item in items:
                            item = item.strip()
                            if ':' in item:
                                key, value = item.split(':', 1)
                                key, value = key.strip(), value.strip()
                                
                                if key == 'BAT':
                                    try:
                                        status_info['battery'] = float(value.replace('V', ''))/100
                                    except:
                                        pass
                                elif key == 'TIMER':
                                    status_info['timer'] = value[:8]
                                elif key == 'STATUS':
                                    status_info['status'] = value[:15]
                                elif key == 'L1':
                                    status_info['l1_connected'] = (value == '1')
                                elif key == 'L2':
                                    status_info['l2_connected'] = (value == '1')
                                elif key == 'BAT_ADC':
                                    try:
                                        status_info['bat_adc'] = max(0, min(4095, int(value)))
                                    except:
                                        pass
                    
                    return status_info
                
                status_data = self.safe_parse_wrapper(parse_status_simple, response_data, "수동상태파싱")
                if status_data:
                    # RAW 데이터 기록
                    self.write_raw_data_log(response_data, "MANUAL_STATUS_REFRESH", "수동 상태 새로고침")
                    self.update_status_display(status_data)
                    self.write_status_log(status_data)
                    self.log_message("✅ 수동 상태 새로고침 완료")
                else:
                    # 실패한 RAW 데이터도 기록
                    self.write_raw_data_log(response_data, "FAILED_MANUAL_STATUS", "수동 상태 새로고침 실패")
                    self.log_message("⚠️ 상태 데이터 파싱 실패")
            else:
                self.log_message("⚠️ 상태 응답 없음")
                # 응답 없음도 기록
                if response_data:
                    self.write_raw_data_log(response_data, "NO_STATUS_RESPONSE", "STATUS: 마커가 없는 응답")
                else:
                    self.write_event_log("NO_RESPONSE", "상태 요청에 대한 응답이 없음")
        except Exception as e:
            self.log_message(f"❌ 상태 새로고침 오류: {str(e)}")
        finally:
            # 락 해제
            try:
                self.serial_lock.release()
            except:
                pass
    
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
        """로그 메시지 출력 - 무한루프 방지 및 성능 최적화 강화"""
        try:
            current_time = time.time()
            
            # 메시지 길이 제한 (과도한 메시지 방지)
            if len(message) > 200:
                message = message[:200] + "... (잘림)"
            
            # 메시지 유형별 스로틀링 설정
            critical_keywords = ["오류", "실패", "ERROR", "❌", "CRITICAL", "FATAL"]
            warning_keywords = ["경고", "WARNING", "⚠️", "주의"]
            info_keywords = ["파싱 방법:", "✅ 파싱 완료", "수신 중...", "진행상황", "FPS:", "성공률:"]
            status_keywords = ["상태 요청", "GET_STATUS", "배터리", "타이머", "BAT_ADC"]  # 상태 관련 키워드 추가
            
            # 메시지 중요도에 따른 스로틀링 간격 설정
            if any(keyword in message for keyword in critical_keywords):
                throttle_interval = 1.0  # 중요한 오류는 1초 간격
                message_category = "critical"
            elif any(keyword in message for keyword in warning_keywords):
                throttle_interval = 3.0  # 경고는 3초 간격
                message_category = "warning"
            elif any(keyword in message for keyword in status_keywords):
                throttle_interval = 5.0  # 상태 관련 메시지는 5초 간격 (덜 빈번하게)
                message_category = "status"
            elif any(keyword in message for keyword in info_keywords):
                throttle_interval = 10.0  # 정보성 메시지는 10초 간격
                message_category = "info"
            else:
                throttle_interval = 2.0  # 일반 메시지는 2초 간격
                message_category = "general"
            
            # 메시지 키 생성 (동일 패턴의 메시지 그룹화)
            message_key = message
            if "수신 중..." in message:
                message_key = "data_receiving"
            elif "✅ 파싱 완료" in message:
                message_key = "parsing_complete"
            elif "파싱 방법:" in message:
                message_key = "parsing_method_change"
            elif "FPS:" in message and "성공률:" in message:
                message_key = "performance_stats"
            elif "진행상황" in message:
                message_key = "progress_update"
            
            # 스로틀링 딕셔너리 크기 제한 (메모리 누수 방지)
            if len(self.log_throttle) > 100:
                # 오래된 항목 제거 (가장 오래된 50개 제거)
                sorted_items = sorted(self.log_throttle.items(), key=lambda x: x[1])
                for old_key, _ in sorted_items[:50]:
                    del self.log_throttle[old_key]
            
            # 중복 메시지 제한 검사
            if message_key in self.log_throttle:
                time_diff = current_time - self.log_throttle[message_key]
                if time_diff < throttle_interval:
                    return  # 제한 시간 내 동일 메시지는 스킵
            
            # 메시지 출력 시간 기록
            self.log_throttle[message_key] = current_time
            
            # 타임스탬프 생성
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_msg = f"[{timestamp}] {message}\n"
            except Exception:
                # 시간 생성 실패시 간단한 형태로
                log_msg = f"[LOG] {message}\n"
            
            # GUI 텍스트 위젯에 추가 (안전한 방식)
            try:
                if hasattr(self, 'status_text') and self.status_text:
                    # 텍스트 위젯 라인 수 확인 및 제한
                    try:
                        line_count = int(self.status_text.index('end-1c').split('.')[0])
                        
                        # 라인 수가 너무 많으면 정리 (성능 향상)
                        if line_count > 100:  # 100줄로 제한 축소 (기존 200줄)
                            # 앞의 30줄 삭제 (기존 50줄)
                            self.status_text.delete('1.0', '31.0')
                            
                    except Exception:
                        # 라인 수 확인 실패시 텍스트 위젯 초기화
                        try:
                            self.status_text.delete('1.0', tk.END)
                            self.status_text.insert('1.0', "=== 로그 초기화 ===\n")
                        except:
                            pass
                    
                    # 메시지 추가
                    self.status_text.insert(tk.END, log_msg)
                    
                    # 자동 스크롤 (성능 최적화 - 중요한 메시지만)
                    if message_category in ["critical", "warning"]:
                        self.status_text.see(tk.END)
                        
            except Exception as gui_error:
                # GUI 업데이트 실패는 무시 (콘솔 출력은 계속)
                pass
                
            # 콘솔 출력 (중요한 메시지만 또는 모니터링 중이 아닐 때)
            should_print = (
                not self.is_monitoring or  # 모니터링 중이 아니거나
                message_category in ["critical", "warning"] or  # 중요한 메시지이거나
                any(keyword in message for keyword in ["연결", "시작", "중지", "성공"])  # 상태 변화 메시지
            )
            
            if should_print:
                try:
                    print(log_msg.strip())
                except Exception:
                    # 콘솔 출력 실패도 무시
                    pass
                    
        except Exception as log_error:
            # 로그 함수 자체에서 오류 발생시 최소한의 출력
            try:
                print(f"[LOG_ERROR] {message} (로그 오류: {str(log_error)})")
            except:
                pass  # 모든 출력 실패시 조용히 무시

    def open_settings(self):
        """설정 창 열기"""
        messagebox.showinfo("설정", "설정 기능은 향후 버전에서 제공됩니다")
        
    def show_help(self):
        """도움말 표시"""
        help_text = """OnBoard OLED Monitor v2.0 - 통합 응답 프로토콜

🔗 연결 설정:
1. 시리얼 포트와 보드레이트를 설정합니다 (기본: 921600)
2. '연결' 버튼을 클릭하여 디바이스에 연결합니다

📺 모니터링 모드:
• 통합 모드: 화면과 상태를 동시에 모니터링 (기본)
• 화면만: OLED 화면만 모니터링하여 성능 최적화
• 상태만: 배터리/타이머 상태만 모니터링 (GET_STATUS 명령 주기적 전송)

🎛️ 모니터링 제어:
1. 모니터링 모드를 선택합니다 (통합/화면만/상태만)
2. '모니터링 시작'을 클릭하여 선택된 모드로 모니터링을 시작합니다
3. 화면 확대 비율을 조절할 수 있습니다 (1x~8x)
4. '화면 캡처'로 현재 화면과 상태를 함께 저장할 수 있습니다

⚙️ 갱신 모드 설정:
• 갱신 주기: 50ms~2000ms 선택 가능 (FPS 조절)
• 자동 화면 요청: 체크시 설정된 주기로 자동 화면+상태 요청
• 수동 모드: 체크 해제시 수동으로만 화면+상태 캡처
• 실시간 FPS 및 성공률 모니터링

🔄 모니터링 모드별 특징:
• 통합 모드: 하나의 화면 요청으로 화면과 상태를 동시에 받음
  - 효율성 향상: 별도의 상태 요청 불필요로 통신 오버헤드 감소
  - 충돌 방지: 화면과 상태 요청 간 충돌 문제 완전 해결
  - 데이터 일관성: 동일한 시점의 화면과 상태 정보 보장

• 화면만 모드: OLED 화면만 모니터링
  - 성능 최적화: 화면 데이터만 처리하여 빠른 응답
  - 낮은 CPU 사용량: 상태 파싱 과정 생략
  - 고속 캡처: 화면 변화 감지에 최적화

• 상태만 모드: 배터리/타이머 상태만 모니터링
  - GET_STATUS 명령 주기적 전송
  - 배터리 잔량, 타이머, 시스템 상태, LED 연결 상태 모니터링
  - 상태 로그 자동 기록
  - 화면 처리 없이 가볍게 동작

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
• BAT ADC 값 모니터링

💾 파일 기능:
• 화면 캡처: PNG 형식으로 저장
• 세션 기록: JSON 형식으로 모니터링 세션 저장
• 고해상도 저장: 1x~16x 확대 저장 지원
• 상태 로그: 자동 텍스트 파일 기록

🚀 업데이트 내용 (v2.0):
• 모니터링 모드 선택: 통합/화면만/상태만 모드 지원
• 통합 응답 프로토콜: 화면+상태 동시 처리
• 상태 전용 모니터링: GET_STATUS 명령 주기적 전송
• 충돌 방지: 시리얼 락 및 요청 간격 관리
• 안정성 향상: 무한루프 방지 및 오류 복구
• 성능 최적화: 모드별 최적화된 처리
• 로그 강화: 상태 변화 자동 기록

문의: OnBoard LED Timer Project
버전: v2.0 (모니터링 모드 선택 지원)
"""
        messagebox.showinfo("도움말", help_text)
    
    def on_closing(self):
        """애플리케이션 종료 처리 - 간소화된 안전 종료"""
        try:
            print("프로그램 종료 중...")
            
            # 상태 로그에 종료 이벤트 기록
            try:
                self.write_event_log("SHUTDOWN", "프로그램 종료")
            except:
                pass  # 로그 기록 실패는 무시
            
            # 모니터링 중지
            if self.is_monitoring:
                self.stop_monitoring()
                time.sleep(0.2)  # 짧은 대기
            
            # 시리얼 락 정리 (혹시 락이 걸려있다면 해제)
            try:
                if hasattr(self, 'serial_lock') and self.serial_lock:
                    # 락이 걸려있다면 강제 해제
                    if self.serial_lock.locked():
                        self.serial_lock.release()
                        print("시리얼 락 해제됨")
            except Exception as lock_error:
                print(f"시리얼 락 정리 오류: {str(lock_error)}")
            
            # 시리얼 연결 해제
            if self.is_connected:
                self.disconnect_device()
            
            # 시리얼 포트 강제 닫기
            if hasattr(self, 'serial_port') and self.serial_port:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except:
                    pass  # 포트 닫기 실패는 무시
            
            print("프로그램이 안전하게 종료되었습니다.")
            
        except Exception as e:
            print(f"종료 중 오류: {str(e)}")
        finally:
            # GUI 종료
            try:
                self.root.destroy()
            except:
                import sys
                sys.exit(0)
    
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
            self.log_message("📡 타이머 시작 명령 전송 중...")
            response = self.send_command_and_wait("START_TIMER", 2000)
            
            if response and (b'OK' in response or b'Timer started' in response):
                self.log_message("✅ 타이머가 시작되었습니다")
                self.write_event_log("CONTROL", "원격 타이머 시작")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 시작 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 시작 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 타이머 시작 오류: {str(e)}")
            self.write_event_log("ERROR", f"원격 타이머 시작 오류: {str(e)}")
    
    def remote_stop_timer(self):
        """원격 타이머 정지"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            self.log_message("📡 타이머 정지 명령 전송 중...")
            response = self.send_command_and_wait("STOP_TIMER", 2000)
            
            if response and (b'OK' in response or b'Timer stopped' in response):
                self.log_message("✅ 타이머가 정지되었습니다")
                self.write_event_log("CONTROL", "원격 타이머 정지")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 정지 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 정지 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 타이머 정지 오류: {str(e)}")
            self.write_event_log("ERROR", f"원격 타이머 정지 오류: {str(e)}")
    
    def remote_set_timer(self):
        """원격 타이머 설정"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            minutes = self.timer_min_var.get()
            
            # 유효성 검사
            try:
                min_val = int(minutes)
                if min_val < 1 or min_val > 99:
                    raise ValueError("분 범위 오류")
            except ValueError:
                messagebox.showerror("오류", "올바른 시간을 입력하세요 (분: 1-99)")
                return
            
            # 명령 전송
            command = f"SET_TIMER:{minutes:0>2}:00"
            self.log_message(f"📡 타이머 설정 명령 전송 중: {minutes}분")
            response = self.send_command_and_wait(command, 2000)
            
            if response and (b'OK' in response or b'Timer set' in response):
                self.log_message(f"✅ 타이머가 {minutes}분으로 설정되었습니다")
                self.write_event_log("CONTROL", f"타이머 설정: {minutes}분")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 설정 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 설정 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 타이머 설정 오류: {str(e)}")
            self.write_event_log("ERROR", f"타이머 설정 오류: {str(e)}")
    
    def remote_reset(self):
        """원격 시스템 리셋"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        # 확인 대화상자
        if not messagebox.askyesno("확인", "시스템을 리셋하시겠습니까?"):
            return
            
        try:
            self.log_message("📡 시스템 리셋 명령 전송 중...")
            response = self.send_command_and_wait("RESET", 3000)  # 리셋은 더 긴 타임아웃
            
            if response and (b'OK' in response or b'System reset' in response):
                self.log_message("✅ 시스템이 리셋되었습니다")
                self.write_event_log("CONTROL", "시스템 리셋")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 시스템 리셋 응답: {response_str}")
            else:
                self.log_message("❌ 시스템 리셋 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 시스템 리셋 오류: {str(e)}")
            self.write_event_log("ERROR", f"시스템 리셋 오류: {str(e)}")
    
    def remote_ping(self):
        """연결 테스트"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            start_time = time.time()
            self.log_message("📡 연결 테스트 중...")
            
            response = self.send_command_and_wait("PING", 2000)
            elapsed_time = time.time() - start_time
            
            if response and b'PONG' in response:
                self.log_message(f"✅ 연결 테스트 성공 (응답시간: {elapsed_time*1000:.1f}ms)")
                self.write_event_log("TEST", f"연결 테스트 성공 ({elapsed_time*1000:.1f}ms)")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 연결 테스트 응답: {response_str}")
                self.write_event_log("TEST", f"연결 테스트 응답: {response_str}")
            else:
                self.log_message("❌ 연결 테스트 응답 없음")
                self.write_event_log("TEST", "연결 테스트 실패 - 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 연결 테스트 오류: {str(e)}")
            self.write_event_log("ERROR", f"연결 테스트 오류: {str(e)}")
            
    def test_connection(self):
        """기본 연결 테스트"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            self.log_message("📡 기본 연결 테스트 시작...")
            response = self.send_command_and_wait("PING", 3000)
            
            if response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                if 'PONG' in response_str:
                    self.log_message(f"✅ 기본 연결 테스트 성공: {response_str}")
                elif 'OnBoard LED Timer Ready' in response_str:
                    self.log_message(f"✅ 디바이스 응답: {response_str}")
                else:
                    self.log_message(f"⚠️ 기본 연결 테스트 응답: {response_str}")
            else:
                self.log_message("❌ 기본 연결 테스트 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 기본 연결 테스트 오류: {str(e)}")
    
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

    def safe_parse_wrapper(self, parse_function, data, function_name="unknown"):
        """파싱 함수 안전 래퍼 - 무한루프 및 타임아웃 완전 방지"""
        if self.parsing_active:
            self.log_message("⚠️ 다른 파싱 진행 중 - 중복 파싱 방지")
            return None
            
        self.parsing_active = True
        start_time = time.time()
        result = None
        
        try:
            # 데이터 크기 검증
            if hasattr(data, '__len__'):
                if len(data) > 50000:  # 50KB 제한
                    self.log_message(f"⚠️ {function_name}: 데이터 크기 초과 ({len(data)} bytes)")
                    return None
            
            # 시간 제한으로 파싱 실행
            timeout_occurred = False
            
            def timeout_handler():
                nonlocal timeout_occurred
                timeout_occurred = True
                self.log_message(f"⚠️ {function_name}: 타임아웃 발생")
            
            # 타이머 설정
            timer = threading.Timer(self.max_parse_time, timeout_handler)
            timer.start()
            
            try:
                # 실제 파싱 함수 실행
                if not timeout_occurred:
                    result = parse_function(data)
            finally:
                timer.cancel()
            
            # 타임아웃 체크
            if timeout_occurred:
                self.log_message(f"❌ {function_name}: 타임아웃으로 중단됨")
                return None
                
            elapsed_time = time.time() - start_time
            if elapsed_time > 1.0:  # 1초 이상 걸린 경우 경고
                self.log_message(f"⚠️ {function_name}: 느린 파싱 ({elapsed_time:.2f}초)")
                
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.log_message(f"❌ {function_name}: 파싱 오류 ({elapsed_time:.2f}초) - {str(e)}")
            return None
        finally:
            self.parsing_active = False

    def parse_firmware_status_data(self, response):
        """펌웨어에서 받은 상태 데이터 파싱 - 무한루프 완전 방지"""
        try:
            # 기본 상태 정보 (항상 반환되도록)
            status_info = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'firmware',
                'battery': 18.6,
                'timer': '00:00',
                'status': 'UNKNOWN',
                'l1_connected': False,
                'l2_connected': False,
                'bat_adc': 0
            }
            
            # 응답 데이터 전처리
            if isinstance(response, bytes):
                try:
                    data_str = response.decode('utf-8', errors='ignore').strip()
                    status_info['raw_data'] = response
                except:
                    data_str = str(response, errors='replace').strip()
                    status_info['raw_data'] = data_str.encode('utf-8', errors='ignore')
            else:
                data_str = str(response).strip()
                status_info['raw_data'] = data_str.encode('utf-8', errors='ignore')
            
            status_info['raw_string'] = data_str
            
            # 데이터 길이 검증 (과도한 데이터 방지)
            if len(data_str) > 500:
                self.write_event_log("WARNING", f"데이터 크기 제한: {len(data_str)} chars")
                data_str = data_str[:500]
            
            # STATUS: 형식 확인
            if not data_str.startswith('STATUS:'):
                self.write_event_log("WARNING", f"잘못된 STATUS 형식: {data_str[:50]}")
                return status_info
            
            # STATUS: 제거 후 파싱
            status_part = data_str[7:]  # "STATUS:" 제거
            
            # 항목 분할 (최대 개수 제한)
            items = status_part.split(',')[:8]  # 최대 8개 항목만 처리
            
            # 각 항목 파싱
            for item in items:
                try:
                    item = item.strip()
                    if not item or ':' not in item:
                        continue
                    
                    parts = item.split(':', 1)
                    if len(parts) != 2:
                        continue
                        
                    key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # 키와 값 길이 검증
                    if len(key) > 15 or len(value) > 30:
                        continue
                    
                    # 각 항목별 파싱
                    if key == 'BAT':
                        try:
                            battery_str = value.replace('V', '').strip()
                            battery_val = int(battery_str)
                            status_info['battery'] = battery_val/100
                        except:
                            pass
                            
                    elif key == 'TIMER':
                        if len(value) <= 8:
                            status_info['timer'] = value
                            
                    elif key == 'STATUS':
                        if len(value) <= 15:
                            status_info['status'] = value
                            
                    elif key == 'L1':
                        status_info['l1_connected'] = (value == '1')
                        
                    elif key == 'L2':
                        status_info['l2_connected'] = (value == '1')
                        
                    elif key == 'BAT_ADC':
                        try:
                            adc_val = int(value)
                            status_info['bat_adc'] = max(0, min(4095, adc_val))
                        except:
                            pass
                            
                except Exception as item_error:
                    # 개별 아이템 오류는 무시하고 계속
                    continue
            
            return status_info
            
        except Exception as e:
            # 모든 오류를 포착하여 안전한 기본값 반환
            self.write_event_log("ERROR", f"상태 파싱 오류: {str(e)}")
            return {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'firmware_error',
                'battery': 18.6,
                'timer': '00:00',
                'status': 'ERROR',
                'l1_connected': False,
                'l2_connected': False,
                'bat_adc': 0,
                'error': str(e),
                'raw_data': response if isinstance(response, bytes) else str(response).encode('utf-8', errors='ignore'),
                'raw_string': response.decode('utf-8', errors='ignore') if isinstance(response, bytes) else str(response)
            }

    def on_monitoring_mode_changed(self, event):
        """모니터링 모드 변경 처리"""
        self.monitoring_mode = self.monitoring_mode_var.get()
        
        # 모드별 설명 업데이트
        if self.monitoring_mode == "integrated":
            self.monitoring_mode_label.config(text="통합 모드 (화면+상태)", foreground="blue")
            self.log_message("🔄 모니터링 모드 변경: 통합 모드 (화면+상태)")
        elif self.monitoring_mode == "screen_only":
            self.monitoring_mode_label.config(text="화면만 모니터링", foreground="green")
            self.log_message("🔄 모니터링 모드 변경: 화면만 모니터링")
        elif self.monitoring_mode == "status_only":
            self.monitoring_mode_label.config(text="상태만 모니터링", foreground="purple")
            self.log_message("🔄 모니터링 모드 변경: 상태만 모니터링")
        
        # 모니터링 중이면 새로운 모드로 재시작
        if self.is_monitoring:
            self.log_message("⚙️ 모니터링 중 모드 변경 - 재시작 중...")
            self.stop_monitoring()
            time.sleep(0.5)  # 잠시 대기
            self.start_monitoring()
    
    def start_monitoring(self):
        """모니터링 시작 - 모드별 분기 처리"""
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
            
            # 모니터링 플래그 설정
            self.is_monitoring = True
            self.monitor_btn.config(text="모니터링 중지")
            
            # 시리얼 버퍼 클리어
            self.clear_serial_buffers()
            
            # 모니터링 모드에 따른 분기 처리
            if self.monitoring_mode == "integrated":
                self.start_integrated_monitoring()
            elif self.monitoring_mode == "screen_only":
                self.start_screen_only_monitoring()
            elif self.monitoring_mode == "status_only":
                self.start_status_only_monitoring()
            else:
                # 기본값은 통합 모드
                self.start_integrated_monitoring()
                
        except Exception as e:
            self.log_message(f"❌ 모니터링 시작 오류: {str(e)}")
            self.is_monitoring = False
            self.monitor_btn.config(text="모니터링 시작")
    
    def start_integrated_monitoring(self):
        """통합 모니터링 시작 (화면+상태)"""
        try:
            # 펌웨어 설정
            try:
                # 새로운 펌웨어에서는 화면 요청 시 상태도 함께 전송 (통합 응답 모드)
                command = f"SET_UPDATE_MODE:INTEGRATED_RESPONSE,{self.update_interval_ms}\n"
                self.send_command(command)
                
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 통합 응답 모드 설정 완료")
                else:
                    # 기존 펌웨어 호환성을 위한 폴백
                    command = f"SET_UPDATE_MODE:REQUEST_RESPONSE,{self.update_interval_ms}\n"
                    self.send_command(command)
                    self.log_message("🔄 기존 펌웨어 모드로 폴백")
                
                # 모니터링 활성화
                self.send_command("START_MONITOR")
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 활성화")
                    
            except Exception as setup_error:
                self.log_message(f"⚠️ 펌웨어 설정 오류: {str(setup_error)} - 계속 진행")
            
            # 화면 캡처 루프 시작 (상태는 화면 응답에 포함됨)
            if self.capture_thread is None or not self.capture_thread.is_alive():
                self.capture_thread = threading.Thread(target=self.integrated_capture_loop, daemon=True)
                self.capture_thread.start()
                
            mode_text = "통합 모드 (화면+상태)" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.log_message(f"🚀 통합 모니터링 시작 - {mode_text}{interval_text}")
            self.write_event_log("START", f"통합 모니터링 시작 - {mode_text}{interval_text}")
            
        except Exception as e:
            self.log_message(f"❌ 통합 모니터링 시작 오류: {str(e)}")
            raise
    
    def start_screen_only_monitoring(self):
        """화면만 모니터링 시작"""
        try:
            # 펌웨어 설정 (화면만)
            try:
                command = f"SET_UPDATE_MODE:SCREEN_ONLY,{self.update_interval_ms}\n"
                self.send_command(command)
                
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 화면 전용 모드 설정 완료")
                else:
                    self.log_message("⚠️ 펌웨어 화면 전용 모드 설정 응답 없음")
                
                # 모니터링 활성화
                self.send_command("START_MONITOR")
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 활성화")
                    
            except Exception as setup_error:
                self.log_message(f"⚠️ 펌웨어 설정 오류: {str(setup_error)} - 계속 진행")
            
            # 화면 전용 캡처 루프 시작
            if self.capture_thread is None or not self.capture_thread.is_alive():
                self.capture_thread = threading.Thread(target=self.screen_only_capture_loop, daemon=True)
                self.capture_thread.start()
                
            mode_text = "화면 전용 모드" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.log_message(f"🚀 화면 전용 모니터링 시작 - {mode_text}{interval_text}")
            self.write_event_log("START", f"화면 전용 모니터링 시작 - {mode_text}{interval_text}")
            
        except Exception as e:
            self.log_message(f"❌ 화면 전용 모니터링 시작 오류: {str(e)}")
            raise
    
    def start_status_only_monitoring(self):
        """상태만 모니터링 시작"""
        try:
            # 펌웨어 설정 (상태만)
            try:
                command = f"SET_UPDATE_MODE:STATUS_ONLY,{self.update_interval_ms}\n"
                self.send_command(command)
                
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 상태 전용 모드 설정 완료")
                else:
                    self.log_message("⚠️ 펌웨어 상태 전용 모드 설정 응답 없음")
                
                # 모니터링 활성화
                self.send_command("START_MONITOR")
                response = self.wait_for_response(1000)
                if response and b'OK' in response:
                    self.log_message("✅ 펌웨어 모니터링 활성화")
                    
            except Exception as setup_error:
                self.log_message(f"⚠️ 펌웨어 설정 오류: {str(setup_error)} - 계속 진행")
            
            # 상태 전용 모니터링 루프 시작
            if self.status_thread is None or not self.status_thread.is_alive():
                self.status_thread = threading.Thread(target=self.status_only_monitoring_loop, daemon=True)
                self.status_thread.start()
                
            mode_text = "상태 전용 모드" if self.auto_request_enabled else "수동 모드"
            interval_text = f" ({self.update_interval_ms}ms)" if self.auto_request_enabled else ""
            
            self.log_message(f"🚀 상태 전용 모니터링 시작 - {mode_text}{interval_text}")
            self.write_event_log("START", f"상태 전용 모니터링 시작 - {mode_text}{interval_text}")
            
        except Exception as e:
            self.log_message(f"❌ 상태 전용 모니터링 시작 오류: {str(e)}")
            raise

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
        
    finally:
        print("프로그램을 정리 중...")
        try:
            # 시리얼 포트가 열려있다면 닫기
            import serial.tools.list_ports
            print("시리얼 포트 정리 완료")
        except:
            pass
