#!/usr/bin/env python3
"""
OLED Monitor Tool for OnBoard LED Timer - Request-Response Protocol v1.4
STM32 펌웨어의 1.3" OLED 디스플레이 실시간 모니터링 도구

Features:
- 요청-응답 기반 실시간 OLED 화면 캡처
- 사용자 정의 갱신 주기 (50ms~2000ms)
- GET_SCREEN, GET_STATUS 명령어 기반 프로토콜
- 상태 정보 모니터링
- 화면 저장 및 기록
- 원격 제어 (타이머 시작/중지/설정)

Protocol:
- 펌웨어: 요청시에만 화면 데이터 전송 (자동 전송 없음)
- 모니터링 도구: 설정된 주기마다 GET_SCREEN 명령 전송

Author: OnBoard LED Timer Project
Date: 2024-01-01
Version: 1.4 - Request-Response Protocol
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

class OLEDMonitor:
    def __init__(self):
        self.serial_port = None
        self.is_connected = False
        self.is_monitoring = False
        self.capture_thread = None
        self.status_thread = None
        
        # OLED 설정
        self.OLED_WIDTH = 128
        self.OLED_HEIGHT = 64
        self.IMAGE_SIZE = (self.OLED_WIDTH // 8) * self.OLED_HEIGHT  # 1024 bytes
        
        # 현재 화면 데이터
        self.current_screen = None
        self.current_status = {}
        
        # 파싱 방법 설정 (가장 안정적인 방법으로 기본값 변경)
        self.parsing_method = "method3_rotated_180"  # 세로 뒤집기가 가장 안정적
        
        # 화면 갱신 주기 설정 (밀리초 단위)
        self.update_interval_ms = 50  # 기본 50ms (20 FPS)로 변경
        self.auto_request_enabled = False  # 자동 요청 모드
        
        # 성능 통계 추적
        self.performance_stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'last_capture_time': 0,
            'fps_counter': 0,
            'fps_start_time': time.time()
        }
        
        # 로그 출력 최적화 - 중복 방지
        self.log_throttle = {}  # 메시지별 마지막 출력 시간
        self.log_throttle_interval = 2.0  # 2초 내 동일 메시지는 한 번만 출력
        
        # GUI 설정
        self.setup_gui()
        
    def setup_gui(self):
        """GUI 인터페이스 설정"""
        self.root = tk.Tk()
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
        
        # 디버깅 버튼들
        test_btn = ttk.Button(top_frame, text="TEST", 
                            command=self.test_connection)
        test_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        simple_btn = ttk.Button(top_frame, text="GET_SIMPLE", 
                              command=self.test_simple_screen)
        simple_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 자동 저장 체크박스
        self.auto_save_var = tk.BooleanVar()
        auto_save_cb = ttk.Checkbutton(top_frame, text="자동 저장", 
                                      variable=self.auto_save_var)
        auto_save_cb.pack(side=tk.RIGHT)
        
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
        
        ttk.Label(setting_frame, text="타이머 설정:").pack(side=tk.LEFT)
        
        self.timer_min_var = tk.StringVar(value="05")
        min_spin = ttk.Spinbox(setting_frame, from_=0, to=99, width=3,
                              textvariable=self.timer_min_var, format="%02.0f")
        min_spin.pack(side=tk.LEFT, padx=(5, 2))
        
        ttk.Label(setting_frame, text=":").pack(side=tk.LEFT)
        
        self.timer_sec_var = tk.StringVar(value="30")
        sec_spin = ttk.Spinbox(setting_frame, from_=0, to=59, width=3,
                              textvariable=self.timer_sec_var, format="%02.0f")
        sec_spin.pack(side=tk.LEFT, padx=(2, 5))
        
        set_timer_btn = ttk.Button(setting_frame, text="타이머 설정", 
                                 command=self.remote_set_timer)
        set_timer_btn.pack(side=tk.LEFT, padx=(5, 0))
        
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
        """디바이스 연결"""
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
            
            self.serial_port = serial.Serial(port, baud, timeout=1)
            self.is_connected = True
            
            self.connect_btn.config(text="연결 해제")
            self.status_label.config(text="연결됨", foreground="green")
            
            self.log_message(f"포트 {port}에 연결됨 (보드레이트: {baud})")
            
        except Exception as e:
            messagebox.showerror("연결 오류", f"연결할 수 없습니다: {str(e)}")
            self.log_message(f"연결 오류: {str(e)}")
            
    def disconnect_device(self):
        """디바이스 연결 해제"""
        if self.is_monitoring:
            self.stop_monitoring()
            
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None
            
        self.is_connected = False
        self.connect_btn.config(text="연결")
        self.status_label.config(text="연결 안됨", foreground="red")
        self.log_message("연결이 해제되었습니다")
        
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
        """모니터링 시작 - 요청-응답 방식으로 완전 전환"""
        if not self.is_connected:
            messagebox.showwarning("경고", "먼저 디바이스에 연결하세요")
            return
            
        self.is_monitoring = True
        self.monitor_btn.config(text="모니터링 중지")
        
        # 갱신 주기 동기화
        self.update_interval_ms = int(self.interval_var.get())
        self.auto_request_enabled = self.auto_request_var.get()
        
        # 펌웨어에 요청-응답 모드 설정 (필수)
        try:
            self.clear_serial_buffers()
            
            # 1단계: 펌웨어를 요청-응답 모드로 설정
            command = f"SET_UPDATE_MODE:REQUEST_RESPONSE,{self.update_interval_ms}\n"
            self.serial_port.write(command.encode())
            self.serial_port.flush()
            
            response = self.wait_for_response(3000)  # 타임아웃 증가 2000 -> 3000
            if response and b'OK:Request-Response mode set' in response:
                self.log_message(f"✅ 펌웨어 요청-응답 모드 설정 완료 (주기: {self.update_interval_ms}ms)")
            else:
                self.log_message("⚠️ 펌웨어 모드 설정 응답 확인 실패 - 계속 진행")
                
            # 2단계: 모니터링 활성화 (요청-응답 방식)
            self.serial_port.write(b'START_MONITOR\n')
            self.serial_port.flush()
            
            response = self.wait_for_response(3000)  # 타임아웃 증가 2000 -> 3000
            if response and b'OK:Monitoring started' in response:  # 응답 문자열 수정
                self.log_message("✅ 펌웨어 모니터링 모드 활성화됨")
            else:
                self.log_message("⚠️ 펌웨어 모니터링 활성화 응답 확인 실패 - 계속 진행")
                
        except Exception as e:
            self.log_message(f"❌ 펌웨어 설정 오류: {str(e)}")
        
        # 화면 캡처 스레드 시작 (요청-응답 기반)
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
        # 상태 모니터링 스레드 시작 (요청-응답 기반)
        self.status_thread = threading.Thread(target=self.status_loop, daemon=True)
        self.status_thread.start()
        
        mode_text = f"자동 모드 ({self.update_interval_ms}ms)" if self.auto_request_enabled else "수동 모드"
        self.log_message(f"🚀 요청-응답 기반 모니터링 시작 - {mode_text}")
        
        # UI 상태 업데이트
        if self.auto_request_enabled:
            self.update_mode_label.config(text=f"자동 모드 ({self.update_interval_ms}ms)", foreground="green")
        else:
            self.update_mode_label.config(text="수동 모드", foreground="orange")
        
    def stop_monitoring(self):
        """모니터링 중지 - 완전한 상태 초기화"""
        self.is_monitoring = False
        self.monitor_btn.config(text="모니터링 시작")
        
        # 스레드 완전 종료 대기
        if hasattr(self, 'capture_thread') and self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)  # 2초 대기
            
        if hasattr(self, 'status_thread') and self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=2.0)  # 2초 대기
        
        # 펌웨어에 모니터링 중지 명령 전송
        if self.is_connected and self.serial_port:
            try:
                # 버퍼 완전 클리어
                self.clear_serial_buffers()
                
                # 모니터링 중지 명령
                self.serial_port.write(b'STOP_MONITOR\n')
                self.serial_port.flush()
                
                # 응답 대기
                response = self.wait_for_response(1000)
                if response and b'OK:Monitoring stopped' in response:
                    self.log_message("✅ 펌웨어 모니터링 모드 비활성화됨")
                else:
                    self.log_message("⚠️ 펌웨어 모니터링 모드 비활성화 응답 없음")
                    
                # 추가 정리: 남은 데이터 완전 제거
                time.sleep(0.1)  # 100ms 대기
                self.clear_serial_buffers()
                
            except Exception as e:
                self.log_message(f"❌ 모니터링 중지 오류: {str(e)}")
        
        # 성능 통계 리셋
        self.performance_stats['fps_counter'] = 0
        self.performance_stats['fps_start_time'] = time.time()
        
        self.log_message("🛑 모니터링 완전 중지 및 상태 초기화 완료")
        
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
        """화면 캡처 루프 - 최적화된 요청-응답 방식"""
        consecutive_failures = 0
        max_failures = 5
        last_request_time = 0
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 자동 요청 모드에서만 주기적으로 화면 요청
                if self.auto_request_enabled:
                    # 설정된 주기에 따라 화면 요청
                    interval_seconds = self.update_interval_ms / 1000.0
                    
                    if current_time - last_request_time >= interval_seconds:
                        success = self.request_screen_update()
                        last_request_time = current_time
                        
                        if success:
                            consecutive_failures = 0  # 성공시 실패 카운터 리셋
                        else:
                            consecutive_failures += 1
                    
                    # 다음 요청까지 대기 (CPU 사용률 최적화)
                    sleep_time = max(0.01, min(0.05, interval_seconds / 20))  # 10ms~50ms 범위
                    time.sleep(sleep_time)
                else:
                    # 수동 모드에서는 긴 대기 (CPU 절약)
                    time.sleep(0.1)  # 100ms 대기
                    consecutive_failures = 0  # 수동 모드에서는 실패 카운터 리셋
                    
                # 연속 실패 처리
                if consecutive_failures >= max_failures:
                    self.log_message(f"🚨 연속 {max_failures}회 실패로 캡처 루프 일시 중단 (2초)")
                    time.sleep(2)  # 2초 대기 후 재시도
                    consecutive_failures = 0
                    
            except Exception as e:
                consecutive_failures += 1
                self.log_message(f"❌ 캡처 루프 오류 ({consecutive_failures}/{max_failures}): {str(e)}")
                
                if consecutive_failures >= max_failures:
                    self.log_message("🚨 캡처 루프 오류로 일시 중단")
                    time.sleep(2)  # 2초 대기 후 재시도
                    consecutive_failures = 0
                else:
                    time.sleep(0.5)  # 실패시 짧은 대기
    
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
                
                # 자동 저장이 활성화된 경우
                if self.auto_save_var.get():
                    self.auto_save_screen(screen_data)
                    
                return True
            
            return False
                
        except Exception as e:
            self.log_message(f"❌ 화면 응답 처리 오류: {str(e)}")
            return False
    
    def status_loop(self):
        """상태 모니터링 루프 - 요청-응답 방식으로 전환"""
        while self.is_monitoring:
            try:
                # GET_STATUS 명령어로 상태 정보 요청
                if self.is_connected and self.serial_port:
                    self.serial_port.write(b'GET_STATUS\n')
                    self.serial_port.flush()
                    
                    # 응답 대기 및 처리
                    response = self.wait_for_response(1000)
                    if response:
                        status_data = self.parse_firmware_status_data(response)
                        if status_data:
                            self.update_status_display(status_data)
                
                time.sleep(2)  # 2초 간격으로 상태 요청
            except Exception as e:
                self.log_message(f"상태 루프 오류: {str(e)}")
                time.sleep(2)
    
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
    
    def parse_firmware_status_data(self, data):
        """펌웨어에서 받은 상태 데이터 파싱"""
        try:
            data_str = data.decode('utf-8', errors='ignore').strip()
            
            # STATUS: 형식인지 확인
            if not data_str.startswith('STATUS:'):
                return None
            
            # STATUS: 제거
            status_part = data_str[7:]  # "STATUS:" 제거
            
            # 각 항목 파싱
            status_info = {'timestamp': datetime.now().strftime('%H:%M:%S'), 'source': 'firmware'}
            
            items = status_part.split(',')
            for item in items:
                if ':' in item:
                    key, value = item.split(':', 1)
                    
                    if key == 'BAT':
                        # 배터리: "75%" -> 75
                        status_info['battery'] = int(value.replace('%', ''))
                    elif key == 'TIMER':
                        # 타이머: "05:30"
                        status_info['timer'] = value
                    elif key == 'STATUS':
                        # 상태: "RUNNING"
                        status_info['status'] = value
                    elif key == 'L1':
                        # L1 연결: "1" -> True
                        status_info['l1_connected'] = (value == '1')
                    elif key == 'L2':
                        # L2 연결: "0" -> False
                        status_info['l2_connected'] = (value == '1')
            
            return status_info
            
        except Exception as e:
            self.log_message(f"상태 데이터 파싱 오류: {str(e)}")
            return None
        
    def update_display(self, screen_data):
        """화면 디스플레이 업데이트"""
        try:
            # PIL 이미지로 변환 (L 모드로 직접 생성하여 성능 향상)
            img = Image.fromarray(screen_data, mode='L')
            
            # 확대 (NEAREST 방식으로 빠른 처리)
            scale = self.scale_var.get()
            if scale > 1:
                new_size = (self.OLED_WIDTH * scale, self.OLED_HEIGHT * scale)
                img = img.resize(new_size, Image.NEAREST)
            
            # Tkinter PhotoImage로 변환
            photo = ImageTk.PhotoImage(img)
            
            # 캔버스 업데이트 (이전 이미지 제거 후 새 이미지 추가)
            self.canvas.delete("screen_image")  # 태그로 삭제하여 성능 향상
            canvas_x = (self.canvas.winfo_width() // 2) if self.canvas.winfo_width() > 1 else 256
            canvas_y = (self.canvas.winfo_height() // 2) if self.canvas.winfo_height() > 1 else 128
            self.canvas.create_image(canvas_x, canvas_y, image=photo, tags="screen_image")
            self.canvas.image = photo  # 참조 유지
            
            self.current_screen = screen_data
            
        except Exception as e:
            # 오류 로그도 간소화
            if hasattr(self, '_last_display_error') and time.time() - self._last_display_error < 5:
                return  # 5초 내 동일 오류는 스킵
            self._last_display_error = time.time()
            self.log_message(f"화면 업데이트 오류: {str(e)}")
            
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
        
        status_text = f"""배터리: {status_data.get('battery', 'N/A')}%
타이머: {status_data.get('timer', 'N/A')}
상태: {status_data.get('status', 'N/A')}
L1 연결: {'예' if status_data.get('l1_connected', False) else '아니오'}
L2 연결: {'예' if status_data.get('l2_connected', False) else '아니오'}
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
            self.request_status()
        else:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            
    def save_screen(self):
        """화면 저장"""
        if self.current_screen is None:
            messagebox.showwarning("경고", "저장할 화면이 없습니다")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                img = Image.fromarray(self.current_screen)
                img.save(filename)
                self.log_message(f"화면이 저장되었습니다: {filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {str(e)}")
                
    def auto_save_screen(self, screen_data):
        """자동 화면 저장"""
        if not os.path.exists("captures"):
            os.makedirs("captures")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captures/oled_capture_{timestamp}.png"
        
        try:
            img = Image.fromarray(screen_data)
            img.save(filename)
        except Exception as e:
            self.log_message(f"자동 저장 실패: {str(e)}")
            
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
        """애플리케이션 종료 처리"""
        if self.is_monitoring:
            self.stop_monitoring()
        if self.is_connected:
            self.disconnect_device()
        self.root.destroy()
        
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
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 시작 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 시작 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 원격 제어 오류: {str(e)}")
    
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
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 타이머 정지 응답: {response_str}")
            else:
                self.log_message("❌ 타이머 정지 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 원격 제어 오류: {str(e)}")
    
    def remote_set_timer(self):
        """원격 타이머 설정"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            minutes = self.timer_min_var.get()
            seconds = self.timer_sec_var.get()
            
            # 유효성 검사
            try:
                min_val = int(minutes)
                sec_val = int(seconds)
                if min_val < 0 or min_val > 99 or sec_val < 0 or sec_val > 59:
                    raise ValueError("시간 범위 오류")
            except ValueError:
                messagebox.showerror("오류", "올바른 시간을 입력하세요 (분: 0-99, 초: 0-59)")
                return
            
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            command = f"SET_TIMER:{minutes:0>2}:{seconds:0>2}\n"
            self.serial_port.write(command.encode())
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response(2000)  # 타임아웃 증가
            if response and b'OK:Timer set' in response:
                self.log_message(f"✅ 타이머가 {minutes}:{seconds}으로 설정되었습니다")
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
        """연결 테스트"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            start_time = time.time()
            self.serial_port.write(b'PING\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response(2000)  # 타임아웃 증가
            elapsed_time = time.time() - start_time
            
            if response and b'PONG' in response:
                self.log_message(f"✅ 연결 테스트 성공 (응답시간: {elapsed_time*1000:.1f}ms)")
            elif response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"⚠️ 연결 테스트 응답: {response_str}")
            else:
                self.log_message("❌ 연결 테스트 응답 없음")
                
        except Exception as e:
            self.log_message(f"❌ 연결 테스트 오류: {str(e)}")
    
    def wait_for_response(self, timeout_ms=500):
        """응답 대기 (원격 제어용) - 강화된 버전"""
        if not self.serial_port:
            return None
            
        response_data = b''
        timeout_count = 0
        max_timeout = timeout_ms // 10  # 10ms 단위
        
        while timeout_count < max_timeout:
            try:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 완전한 응답 확인 (개행 문자 또는 응답 완료 패턴)
                    if b'\n' in response_data or b'OK:' in response_data or b'ERROR:' in response_data:
                        # 추가 데이터가 있을 수 있으니 잠시 더 대기
                        time.sleep(0.05)  # 50ms 추가 대기
                        
                        # 남은 데이터가 있다면 수신
                        if self.serial_port.in_waiting > 0:
                            final_chunk = self.serial_port.read(self.serial_port.in_waiting)
                            response_data += final_chunk
                        
                        break
                else:
                    time.sleep(0.01)
                    timeout_count += 1
                    
            except Exception as e:
                self.log_message(f"⚠️ 응답 수신 오류: {str(e)}")
                break
        
        # 응답 데이터 후처리
        if len(response_data) > 0:
            try:
                # 디코딩 가능한 텍스트만 반환
                decoded_response = response_data.decode('utf-8', errors='ignore')
                if decoded_response.strip():
                    return response_data
            except:
                pass
        
        return response_data if len(response_data) > 0 else None

    def test_connection(self):
        """기본 연결 테스트 (PING 명령어로 변경)"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 명령 전송 전 버퍼 클리어
            self.clear_serial_buffers()
            
            # PING 명령어로 변경 (더 안정적)
            self.serial_port.write(b'PING\n')
            self.serial_port.flush()
            
            response = self.wait_for_response(3000)  # 타임아웃 증가
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
        # 파싱 방법 변경 로그는 throttle 시스템으로 제한됨
        self.log_message(f"파싱 방법 변경: {self.parsing_method}")
        if self.current_screen is not None:
            self.update_display(self.current_screen)

    def apply_parsing_method(self):
        """파싱 방법 적용"""
        self.parsing_method = self.parsing_var.get()
        # 수동 적용은 항상 로그 출력
        self.log_message(f"파싱 방법 수동 적용: {self.parsing_method}")
        if self.current_screen is not None:
            self.update_display(self.current_screen)

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

if __name__ == "__main__":
    app = OLEDMonitor()
    app.run() 