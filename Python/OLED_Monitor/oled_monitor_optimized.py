# -*- coding: utf-8 -*-
"""
최적화된 OLED 모니터 애플리케이션
기존 중복 코드를 제거하고 모듈화된 구조로 재작성
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np
from PIL import Image, ImageTk
import json

# 새로운 모듈화된 컴포넌트들
from core.constants import *
from parsers.unified_parser import UnifiedDataParser
from utils_enhanced.logger import EnhancedLogger
from utils_enhanced.communication import SerialCommunicator
from utils_enhanced.performance import PerformanceMonitor
from utils_enhanced.config_manager import ConfigManager
from utils_enhanced.file_manager import FileManager

class OptimizedOLEDMonitor:
    """최적화된 OLED 모니터 클래스"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OLED Monitor - 최적화 버전")
        self.root.geometry("1200x800")
        
        # 핵심 컴포넌트 초기화
        self.logger = EnhancedLogger("OLEDMonitor")
        
        # 로거 중복 방지를 위해 basicConfig 제거
        # 대신 루트 로거의 핸들러 중복 방지
        import logging
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        
        self.communicator = SerialCommunicator(auto_reconnect=True)
        self.parser = UnifiedDataParser()
        self.performance_monitor = PerformanceMonitor()
        self.config_manager = ConfigManager()
        self.file_manager = FileManager()
        
        # 상태 변수
        self.is_monitoring = False
        self.current_screen_data = None
        self.current_status_data = None
        self.display_scale = DEFAULT_SCALE
        
        # GUI 컴포넌트
        self.screen_canvas = None
        self.status_labels = {}
        self.control_buttons = {}
        
        # 설정 로드
        self.load_configuration()
        
        # GUI 초기화
        self.setup_gui()
        
        # 이벤트 콜백 등록
        self.setup_callbacks()
        
        # 초기화 완료 로그
        self.logger.info("최적화된 OLED 모니터 초기화 완료")
        
        # 통신 상태 모니터링 추가
        self.communication_stats = {
            'last_command_time': 0,
            'last_response_time': 0,
            'command_count': 0,
            'response_count': 0
        }
    
    def load_configuration(self):
        """설정 로드"""
        try:
            config = self.config_manager.load_config()
            self.display_scale = config.get('display.scale', DEFAULT_SCALE)
            self.refresh_interval = config.get('monitoring.refresh_interval', DEFAULT_REFRESH_INTERVAL)
            
            self.logger.info(f"설정 로드 완료: 스케일={self.display_scale}, 갱신간격={self.refresh_interval}ms")
            
        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
            self.use_default_config()
    
    def use_default_config(self):
        """기본 설정 사용"""
        self.display_scale = DEFAULT_SCALE
        self.refresh_interval = DEFAULT_REFRESH_INTERVAL
        self.logger.info("기본 설정 사용")
    
    def setup_gui(self):
        """GUI 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 좌측 패널 - 화면 표시
        left_panel = ttk.LabelFrame(main_frame, text="OLED 화면", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 화면 캔버스
        self.setup_screen_canvas(left_panel)
        
        # 우측 패널 - 제어 및 상태
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 연결 제어
        self.setup_connection_panel(right_panel)
        
        # 모니터링 제어
        self.setup_monitoring_panel(right_panel)
        
        # 상태 표시
        self.setup_status_panel(right_panel)
        
        # 성능 표시
        self.setup_performance_panel(right_panel)
        
        # 메뉴바
        self.setup_menu()
    
    def setup_screen_canvas(self, parent):
        """화면 캔버스 설정"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 스케일 제어
        scale_frame = ttk.Frame(canvas_frame)
        scale_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(scale_frame, text="스케일:").pack(side=tk.LEFT)
        
        self.scale_var = tk.IntVar(value=self.display_scale)
        scale_spinbox = ttk.Spinbox(
            scale_frame, 
            from_=MIN_SCALE, 
            to=MAX_SCALE, 
            textvariable=self.scale_var,
            width=5,
            command=self.on_scale_changed
        )
        scale_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # 캔버스
        self.screen_canvas = tk.Canvas(
            canvas_frame,
            width=OLED_WIDTH * self.display_scale,
            height=OLED_HEIGHT * self.display_scale,
            bg='black',
            relief=tk.SUNKEN,
            bd=2
        )
        self.screen_canvas.pack()
        
        # 초기 화면 표시
        self.display_test_screen()
    
    def setup_connection_panel(self, parent):
        """연결 제어 패널"""
        conn_frame = ttk.LabelFrame(parent, text="연결 제어", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 포트 선택
        ttk.Label(conn_frame, text="포트:").pack(anchor=tk.W)
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=20)
        self.port_combo.pack(fill=tk.X, pady=(0, 5))
        
        # 통신속도 선택
        ttk.Label(conn_frame, text="통신속도:").pack(anchor=tk.W)
        
        self.baudrate_var = tk.IntVar(value=self.config_manager.get('communication.baudrate', SERIAL_BAUDRATE))
        self.baudrate_combo = ttk.Combobox(
            conn_frame, 
            textvariable=self.baudrate_var, 
            values=SUPPORTED_BAUDRATES,
            width=20,
            state="readonly"
        )
        self.baudrate_combo.pack(fill=tk.X, pady=(0, 5))
        self.baudrate_combo.bind('<<ComboboxSelected>>', self.on_baudrate_changed)
        
        # 포트 새로고침 버튼
        ttk.Button(conn_frame, text="포트 새로고침", command=self.refresh_ports).pack(fill=tk.X, pady=(0, 5))
        
        # 연결/해제 버튼
        self.connect_button = ttk.Button(conn_frame, text="연결", command=self.toggle_connection)
        self.connect_button.pack(fill=tk.X, pady=(0, 5))
        
        # 연결 상태 표시
        self.connection_status = ttk.Label(conn_frame, text="연결 안됨", foreground="red")
        self.connection_status.pack(anchor=tk.W)
        
        # 초기 포트 목록 로드
        self.refresh_ports()
    
    def setup_monitoring_panel(self, parent):
        """모니터링 제어 패널"""
        monitor_frame = ttk.LabelFrame(parent, text="모니터링 제어", padding=10)
        monitor_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 모니터링 시작/중지 버튼
        self.monitor_button = ttk.Button(monitor_frame, text="모니터링 시작", command=self.toggle_monitoring)
        self.monitor_button.pack(fill=tk.X, pady=(0, 5))
        
        # 갱신 간격 설정
        ttk.Label(monitor_frame, text="갱신 간격 (ms):").pack(anchor=tk.W)
        
        self.interval_var = tk.IntVar(value=self.refresh_interval)
        interval_spinbox = ttk.Spinbox(
            monitor_frame,
            from_=50,
            to=5000,
            textvariable=self.interval_var,
            width=10,
            command=self.on_interval_changed
        )
        interval_spinbox.pack(fill=tk.X, pady=(0, 5))
        
        # 엔터키와 포커스 이벤트도 바인딩
        interval_spinbox.bind('<Return>', lambda e: self.on_interval_changed())
        interval_spinbox.bind('<FocusOut>', lambda e: self.on_interval_changed())
        
        # 수동 요청 버튼들
        button_frame = ttk.Frame(monitor_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="화면 요청", command=self.request_screen_manual).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="상태 요청", command=self.request_status_manual).pack(side=tk.LEFT)
        
        # 테스트 버튼 추가
        test_frame = ttk.Frame(monitor_frame)
        test_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(test_frame, text="PING 테스트", command=self.test_ping).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(test_frame, text="연결 테스트", command=self.test_connection_status).pack(side=tk.LEFT)
    
    def setup_status_panel(self, parent):
        """상태 표시 패널"""
        status_frame = ttk.LabelFrame(parent, text="상태 정보", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 상태 라벨들
        status_fields = [
            ('battery', '배터리'),
            ('timer', '타이머'),
            ('status', '상태'),
            ('l1_connected', 'L1 연결'),
            ('l2_connected', 'L2 연결'),
            ('bat_adc', '배터리 ADC')
        ]
        
        for field, label in status_fields:
            frame = ttk.Frame(status_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
            
            value_label = ttk.Label(frame, text="N/A", relief=tk.SUNKEN, width=15)
            value_label.pack(side=tk.LEFT, padx=(5, 0))
            
            self.status_labels[field] = value_label
    
    def setup_performance_panel(self, parent):
        """성능 표시 패널"""
        perf_frame = ttk.LabelFrame(parent, text="성능 정보", padding=10)
        perf_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 성능 정보 라벨들
        self.perf_labels = {}
        perf_fields = [
            ('fps', 'FPS'),
            ('parsing_time', '파싱 시간'),
            ('success_rate', '성공률')
        ]
        
        for field, label in perf_fields:
            frame = ttk.Frame(perf_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
            
            value_label = ttk.Label(frame, text="N/A", relief=tk.SUNKEN, width=15)
            value_label.pack(side=tk.LEFT, padx=(5, 0))
            
            self.perf_labels[field] = value_label
        
        # 통신 상태 패널 추가
        comm_frame = ttk.LabelFrame(parent, text="통신 상태", padding=10)
        comm_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 통신 상태 라벨들
        self.comm_labels = {}
        comm_fields = [
            ('commands_sent', '명령 전송'),
            ('responses_received', '응답 수신'),
            ('last_activity', '마지막 활동')
        ]
        
        for field, label in comm_fields:
            frame = ttk.Frame(comm_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
            
            value_label = ttk.Label(frame, text="N/A", relief=tk.SUNKEN, width=15)
            value_label.pack(side=tk.LEFT, padx=(5, 0))
            
            self.comm_labels[field] = value_label
    
    def setup_menu(self):
        """메뉴바 설정"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="화면 저장", command=self.save_screen)
        file_menu.add_command(label="세션 저장", command=self.save_session)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.on_closing)
        
        # 도구 메뉴
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도구", menu=tools_menu)
        tools_menu.add_command(label="설정", command=self.open_settings)
        tools_menu.add_command(label="로그 보기", command=self.open_logs)
        tools_menu.add_command(label="통계 초기화", command=self.reset_stats)
        
        # 도움말 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="정보", command=self.show_about)
    
    def setup_callbacks(self):
        """이벤트 콜백 설정"""
        # 통신 이벤트 콜백
        self.communicator.register_event_callback('connection', self.on_connection_event)
        self.communicator.register_data_callback('data', self.on_data_received)
        
        # 윈도우 종료 이벤트
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def refresh_ports(self):
        """포트 목록 새로고침"""
        try:
            ports = self.communicator.get_available_ports()
            port_list = [port['device'] for port in ports]
            
            self.port_combo['values'] = port_list
            
            if port_list:
                # OnBoard 장치 자동 감지
                onboard_port = self.communicator.find_device_port(['OnBoard', 'STM32', 'USB Serial'])
                if onboard_port:
                    self.port_var.set(onboard_port)
                elif not self.port_var.get():
                    self.port_var.set(port_list[0])
            
            self.logger.info(f"포트 목록 새로고침: {len(port_list)}개 포트 발견")
            
        except Exception as e:
            self.logger.error(f"포트 목록 새로고침 실패: {e}")
            messagebox.showerror("오류", f"포트 목록을 가져올 수 없습니다: {e}")
    
    def toggle_connection(self):
        """연결/해제 토글"""
        if self.communicator.is_connected():
            self.disconnect_device()
        else:
            self.connect_device()
    
    def connect_device(self):
        """장치 연결"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("오류", "포트를 선택하세요")
            return
        
        try:
            # 설정된 통신속도 사용
            baudrate = self.baudrate_var.get()
            self.logger.info(f"연결 시도: {port} @ {baudrate} bps")
            
            if self.communicator.connect(port, baudrate):
                self.connect_button.config(text="연결 해제")
                self.connection_status.config(text=f"연결됨 ({baudrate} bps)", foreground="green")
                self.logger.info(f"장치 연결 성공: {port} @ {baudrate} bps")
            else:
                messagebox.showerror("오류", "장치 연결에 실패했습니다")
                
        except Exception as e:
            self.logger.error(f"장치 연결 실패: {e}")
            messagebox.showerror("오류", f"연결 실패: {e}")
    
    def disconnect_device(self):
        """장치 연결 해제"""
        try:
            if self.is_monitoring:
                self.stop_monitoring()
            
            self.communicator.disconnect()
            self.connect_button.config(text="연결")
            self.connection_status.config(text="연결 안됨", foreground="red")
            self.logger.info("장치 연결 해제")
            
        except Exception as e:
            self.logger.error(f"장치 연결 해제 실패: {e}")
    
    def toggle_monitoring(self):
        """모니터링 시작/중지"""
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def start_monitoring(self):
        """모니터링 시작"""
        if not self.communicator.is_connected():
            messagebox.showerror("오류", "장치가 연결되지 않았습니다")
            return
        
        self.is_monitoring = True
        self.monitor_button.config(text="모니터링 중지")
        
        # 모니터링 스레드 시작
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("모니터링 시작")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        self.monitor_button.config(text="모니터링 시작")
        self.logger.info("모니터링 중지")
    
    def monitoring_loop(self):
        """모니터링 루프"""
        self.logger.info(f"모니터링 루프 시작 - 갱신 간격: {self.refresh_interval}ms")
        
        while self.is_monitoring:
            try:
                start_time = time.time()
                
                # 화면 데이터 요청
                self.request_screen_data()
                
                # 상태 데이터 요청
                self.request_status_data()
                
                # 성능 측정
                elapsed_time = time.time() - start_time
                self.performance_monitor.record_timing('monitoring_cycle', elapsed_time)
                
                # 갱신 간격 대기 (실제 사용되는 값 로그)
                sleep_time = self.refresh_interval / 1000.0
                self.logger.debug(f"다음 요청까지 대기: {sleep_time:.3f}초")
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(1)  # 오류 발생 시 잠시 대기
        
        self.logger.info("모니터링 루프 종료")
    
    def request_screen_data(self):
        """화면 데이터 요청"""
        if self.communicator.is_connected():
            self.communication_stats['command_count'] += 1
            self.communication_stats['last_command_time'] = time.time()
            
            self.logger.debug(f"화면 데이터 요청 전송: {COMMANDS['SCREEN_REQUEST']}")
            result = self.communicator.send_command(COMMANDS['SCREEN_REQUEST'])
            
            if not result:
                self.logger.error("화면 데이터 요청 전송 실패")
            else:
                self.logger.debug("화면 데이터 요청 전송 성공")
    
    def request_status_data(self):
        """상태 데이터 요청"""
        if self.communicator.is_connected():
            self.communication_stats['command_count'] += 1
            self.communication_stats['last_command_time'] = time.time()
            
            self.logger.debug(f"상태 데이터 요청 전송: {COMMANDS['STATUS_REQUEST']}")
            result = self.communicator.send_command(COMMANDS['STATUS_REQUEST'])
            
            if not result:
                self.logger.error("상태 데이터 요청 전송 실패")
            else:
                self.logger.debug("상태 데이터 요청 전송 성공")
    
    def request_screen_manual(self):
        """수동 화면 요청"""
        self.request_screen_data()
    
    def request_status_manual(self):
        """수동 상태 요청"""
        self.request_status_data()
    
    def test_ping(self):
        """PING 테스트"""
        if self.communicator.is_connected():
            self.logger.info("PING 테스트 시작")
            result = self.communicator.send_command(COMMANDS['PING'])
            if result:
                self.logger.info("PING 명령 전송 성공")
            else:
                self.logger.error("PING 명령 전송 실패")
        else:
            messagebox.showwarning("경고", "장치가 연결되지 않았습니다")
    
    def test_connection_status(self):
        """연결 상태 테스트"""
        if self.communicator.is_connected():
            stats = self.communicator.get_stats()
            port_info = stats.get('port_info', {})
            
            status_msg = f"""연결 상태:
포트: {port_info.get('device', 'N/A')}
보드레이트: {port_info.get('baudrate', 'N/A')}
전송 바이트: {stats.get('bytes_sent', 0)}
수신 바이트: {stats.get('bytes_received', 0)}
명령 전송: {stats.get('commands_sent', 0)}
응답 수신: {stats.get('responses_received', 0)}"""
            
            messagebox.showinfo("연결 상태", status_msg)
            self.logger.info(f"연결 상태 확인: {stats}")
        else:
            messagebox.showwarning("경고", "장치가 연결되지 않았습니다")
    
    def on_data_received(self, data: bytes):
        """데이터 수신 이벤트"""
        try:
            # 통신 통계 업데이트
            self.communication_stats['response_count'] += 1
            self.communication_stats['last_response_time'] = time.time()
            
            # 데이터 크기 로그 (한 번만)
            self.logger.debug(f"데이터 수신: {len(data)} bytes")
            
            # 통합 파서로 데이터 파싱
            screen_data, status_data = self.parser.parse_combined_data(data)
            
            # 화면 데이터 처리
            if screen_data is not None:
                self.current_screen_data = screen_data
                self.root.after(0, self.update_screen_display)
                self.logger.debug("화면 데이터 업데이트 예약")
            
            # 상태 데이터 처리
            if status_data is not None:
                self.current_status_data = status_data
                self.root.after(0, self.update_status_display)
                self.logger.debug(f"상태 데이터 업데이트 예약: {status_data.get('status', 'UNKNOWN')}")
                
                # 상태 로그 기록 (한 번만)
                self.logger.log_status(status_data)
            
            # 데이터가 없으면 경고 (한 번만)
            if screen_data is None and status_data is None:
                self.logger.warning("파싱된 데이터가 없음")
                
        except Exception as e:
            self.logger.error(f"데이터 처리 오류: {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
    
    def update_screen_display(self):
        """화면 표시 업데이트"""
        if self.current_screen_data is None:
            self.logger.debug("화면 데이터가 없음")
            return
        
        try:
            # 데이터 타입 확인
            if not isinstance(self.current_screen_data, np.ndarray):
                self.logger.error(f"잘못된 화면 데이터 타입: {type(self.current_screen_data)}")
                return
            
            # 데이터 크기 확인
            if self.current_screen_data.shape != (OLED_HEIGHT, OLED_WIDTH):
                self.logger.error(f"잘못된 화면 데이터 크기: {self.current_screen_data.shape}, 예상: ({OLED_HEIGHT}, {OLED_WIDTH})")
                return
            
            # numpy 배열을 PIL 이미지로 변환
            img = Image.fromarray(self.current_screen_data, mode='L')
            
            # 스케일링
            scaled_size = (OLED_WIDTH * self.display_scale, OLED_HEIGHT * self.display_scale)
            img = img.resize(scaled_size, Image.NEAREST)
            
            # Tkinter 이미지로 변환
            photo = ImageTk.PhotoImage(img)
            
            # 캔버스에 표시
            self.screen_canvas.delete("all")
            self.screen_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.screen_canvas.image = photo  # 참조 유지
            
            self.logger.debug(f"화면 표시 업데이트 완료: {self.current_screen_data.shape}")
            
        except Exception as e:
            self.logger.error(f"화면 표시 업데이트 오류: {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
    
    def update_status_display(self):
        """상태 표시 업데이트"""
        if self.current_status_data is None:
            return
        
        try:
            # 상태 라벨 업데이트
            for field, label in self.status_labels.items():
                value = self.current_status_data.get(field, "N/A")
                
                if field == 'battery':
                    # 배터리 값을 전압으로 표시 (0~5000 -> 0.00~50.00V)
                    if isinstance(value, (int, float)) and value != "N/A":
                        voltage = value / 100.0
                        value = f"{voltage:.2f}V"
                    else:
                        value = "N/A"
                elif field == 'bat_adc':
                    # ADC 값도 전압으로 변환 (0~4095 -> 0.00~3.30V, 3.3V 기준)
                    if isinstance(value, (int, float)) and value != "N/A":
                        adc_voltage = (value / 4095.0) * 3.3
                        value = f"{adc_voltage:.2f}V"
                    else:
                        value = "N/A"
                elif field in ['l1_connected', 'l2_connected']:
                    value = "연결됨" if value else "연결안됨"
                
                label.config(text=str(value))
            
            # 성능 정보 업데이트
            self.update_performance_display()
            
        except Exception as e:
            self.logger.error(f"상태 표시 업데이트 오류: {e}")
    
    def update_performance_display(self):
        """성능 표시 업데이트"""
        try:
            # 파싱 통계
            parsing_stats = self.parser.get_parsing_stats()
            
            # 통신 통계
            comm_stats = self.communicator.get_stats()
            
            # 성능 통계
            perf_stats = self.performance_monitor.get_stats()
            
            # 성능 표시 업데이트 (안전한 값 추출)
            fps_value = perf_stats.get('fps', 0)
            if isinstance(fps_value, (int, float)):
                self.perf_labels['fps'].config(text=f"{fps_value:.1f}")
            else:
                self.perf_labels['fps'].config(text="0.0")
            
            # 파싱 시간 (안전한 값 추출)
            parsing_time = parsing_stats.get('average_parsing_time', 0)
            if isinstance(parsing_time, (int, float)):
                self.perf_labels['parsing_time'].config(text=f"{parsing_time*1000:.1f}ms")
            else:
                self.perf_labels['parsing_time'].config(text="0.0ms")
            
            # 성공률 계산 (안전한 값 추출)
            success_rate = parsing_stats.get('status_success_rate', 0)
            if isinstance(success_rate, (int, float)):
                self.perf_labels['success_rate'].config(text=f"{success_rate*100:.1f}%")
            else:
                self.perf_labels['success_rate'].config(text="0.0%")
            
            # 통신 상태 업데이트
            self.comm_labels['commands_sent'].config(text=str(self.communication_stats['command_count']))
            self.comm_labels['responses_received'].config(text=str(self.communication_stats['response_count']))
            
            # 마지막 활동 시간
            last_activity = self.communication_stats['last_response_time']
            if last_activity > 0:
                elapsed = time.time() - last_activity
                self.comm_labels['last_activity'].config(text=f"{elapsed:.1f}초 전")
            else:
                self.comm_labels['last_activity'].config(text="없음")
            
        except Exception as e:
            self.logger.error(f"성능 표시 업데이트 오류: {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
    
    def display_test_screen(self):
        """테스트 화면 표시"""
        test_screen = self.parser.screen_parser.create_test_screen("checkerboard")
        self.current_screen_data = test_screen
        self.update_screen_display()
    
    def on_scale_changed(self):
        """스케일 변경 이벤트"""
        try:
            new_scale = self.scale_var.get()
            if MIN_SCALE <= new_scale <= MAX_SCALE:
                self.display_scale = new_scale
                
                # 캔버스 크기 조정
                new_width = OLED_WIDTH * new_scale
                new_height = OLED_HEIGHT * new_scale
                self.screen_canvas.config(width=new_width, height=new_height)
                
                # 화면 재표시
                self.update_screen_display()
                
                # 설정 저장
                self.config_manager.set('display.scale', new_scale)
                
        except Exception as e:
            self.logger.error(f"스케일 변경 오류: {e}")
    
    def on_interval_changed(self):
        """갱신 간격 변경 이벤트"""
        try:
            new_interval = self.interval_var.get()
            if 50 <= new_interval <= 5000:
                self.refresh_interval = new_interval
                self.config_manager.set('monitoring.refresh_interval', new_interval)
                self.logger.info(f"갱신 간격 변경: {new_interval}ms")
                
        except Exception as e:
            self.logger.error(f"갱신 간격 변경 오류: {e}")
    
    def on_baudrate_changed(self, event):
        """통신속도 변경 이벤트"""
        try:
            new_baudrate = self.baudrate_var.get()
            if new_baudrate in SUPPORTED_BAUDRATES:
                self.config_manager.set('communication.baudrate', new_baudrate)
                self.logger.info(f"통신속도 변경: {new_baudrate}")
                messagebox.showinfo("설정 변경", f"통신속도가 {new_baudrate}로 변경되었습니다.")
            else:
                messagebox.showwarning("경고", "지원되지 않는 통신속도입니다.")
        except Exception as e:
            self.logger.error(f"통신속도 변경 오류: {e}")
    
    def on_connection_event(self, event_type: str, event_data: Dict):
        """연결 이벤트 처리"""
        if event_type == 'connected':
            self.root.after(0, lambda: self.connection_status.config(text="연결됨", foreground="green"))
        elif event_type == 'disconnected':
            self.root.after(0, lambda: self.connection_status.config(text="연결 안됨", foreground="red"))
    
    def save_screen(self):
        """화면 저장"""
        if self.current_screen_data is None:
            messagebox.showwarning("경고", "저장할 화면 데이터가 없습니다")
            return
        
        try:
            filename = self.file_manager.save_image(self.current_screen_data)
            messagebox.showinfo("성공", f"화면이 저장되었습니다: {filename}")
            self.logger.info(f"화면 저장: {filename}")
            
        except Exception as e:
            self.logger.error(f"화면 저장 실패: {e}")
            messagebox.showerror("오류", f"화면 저장 실패: {e}")
    
    def save_session(self):
        """세션 저장"""
        try:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'screen_data': self.current_screen_data.tolist() if self.current_screen_data is not None else None,
                'status_data': self.current_status_data,
                'config': self.config_manager.get_all(),
                'stats': {
                    'parsing': self.parser.get_parsing_stats(),
                    'communication': self.communicator.get_stats(),
                    'performance': self.performance_monitor.get_stats()
                }
            }
            
            filename = self.file_manager.save_json(session_data)
            messagebox.showinfo("성공", f"세션이 저장되었습니다: {filename}")
            self.logger.info(f"세션 저장: {filename}")
            
        except Exception as e:
            self.logger.error(f"세션 저장 실패: {e}")
            messagebox.showerror("오류", f"세션 저장 실패: {e}")
    
    def open_settings(self):
        """설정 창 열기"""
        # 설정 창 구현 (간단한 버전)
        settings_window = tk.Toplevel(self.root)
        settings_window.title("설정")
        settings_window.geometry("400x300")
        
        # 설정 항목들
        ttk.Label(settings_window, text="설정 기능은 추후 구현 예정").pack(pady=20)
        
        ttk.Button(settings_window, text="닫기", command=settings_window.destroy).pack(pady=10)
    
    def open_logs(self):
        """로그 보기"""
        try:
            log_dir = self.logger.log_dir
            import os
            os.startfile(log_dir)  # Windows에서 폴더 열기
            
        except Exception as e:
            self.logger.error(f"로그 폴더 열기 실패: {e}")
            messagebox.showerror("오류", f"로그 폴더를 열 수 없습니다: {e}")
    
    def reset_stats(self):
        """통계 초기화"""
        try:
            self.parser.reset_stats()
            self.communicator.reset_stats()
            self.performance_monitor.reset()
            
            messagebox.showinfo("성공", "통계가 초기화되었습니다")
            self.logger.info("통계 초기화")
            
        except Exception as e:
            self.logger.error(f"통계 초기화 실패: {e}")
            messagebox.showerror("오류", f"통계 초기화 실패: {e}")
    
    def show_about(self):
        """정보 표시"""
        about_text = """
OLED Monitor - 최적화 버전

버전: 2.0.0
개발자: OnBoard Team

특징:
- 모듈화된 구조
- 최적화된 파싱 엔진
- 향상된 성능 모니터링
- 비동기 통신 지원
- 자동 재연결 기능
"""
        messagebox.showinfo("정보", about_text)
    
    def on_closing(self):
        """애플리케이션 종료"""
        try:
            # 모니터링 중지
            if self.is_monitoring:
                self.stop_monitoring()
            
            # 연결 해제
            if self.communicator.is_connected():
                self.communicator.disconnect()
            
            # 설정 저장
            self.config_manager.save_config()
            
            # 로거 종료
            self.logger.close()
            
            self.logger.info("애플리케이션 종료")
            
        except Exception as e:
            print(f"종료 중 오류: {e}")
        finally:
            self.root.destroy()
    
    def run(self):
        """애플리케이션 실행"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            self.logger.error(f"애플리케이션 실행 오류: {e}")
            messagebox.showerror("치명적 오류", f"애플리케이션 오류: {e}")

if __name__ == "__main__":
    app = OptimizedOLEDMonitor()
    app.run() 