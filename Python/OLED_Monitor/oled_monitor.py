#!/usr/bin/env python3
"""
OLED Monitor Tool for OnBoard LED Timer
STM32 펌웨어의 1.3" OLED 디스플레이 실시간 모니터링 도구

Features:
- 실시간 OLED 화면 캡처
- 상태 정보 모니터링
- 화면 저장 및 기록
- 원격 제어 (향후 확장)

Author: OnBoard LED Timer Project
Date: 2024-01-01
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
        
        # GUI 설정
        self.setup_gui()
        
    def setup_gui(self):
        """GUI 인터페이스 설정"""
        self.root = tk.Tk()
        self.root.title("OnBoard OLED Monitor v1.1 - 실시간 모니터링 및 원격 제어")
        self.root.geometry("900x700")
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
        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(conn_frame, textvariable=self.baud_var, width=10)
        baud_combo['values'] = ['9600', '115200', '230400', '460800']
        baud_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # 연결 버튼
        self.connect_btn = ttk.Button(conn_frame, text="연결", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # 상태 표시
        self.status_label = ttk.Label(conn_frame, text="연결 안됨", foreground="red")
        self.status_label.grid(row=0, column=5, padx=5, pady=5)
        
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
        """모니터링 시작"""
        if not self.is_connected:
            messagebox.showwarning("경고", "먼저 디바이스에 연결하세요")
            return
            
        self.is_monitoring = True
        self.monitor_btn.config(text="모니터링 중지")
        
        # 펌웨어에 모니터링 시작 명령 전송
        try:
            self.serial_port.write(b'START_MONITOR\n')
            self.serial_port.flush()
            response = self.wait_for_response(1000)
            if response and b'OK:Monitoring started' in response:
                self.log_message("펌웨어 모니터링 모드 활성화됨")
            else:
                self.log_message("펌웨어 모니터링 모드 활성화 실패")
        except Exception as e:
            self.log_message(f"모니터링 시작 오류: {str(e)}")
        
        # 화면 캡처 스레드 시작
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
        # 상태 모니터링 스레드 시작
        self.status_thread = threading.Thread(target=self.status_loop, daemon=True)
        self.status_thread.start()
        
        self.log_message("실시간 모니터링 시작")
        
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        self.monitor_btn.config(text="모니터링 시작")
        
        # 펌웨어에 모니터링 중지 명령 전송
        if self.is_connected:
            try:
                self.serial_port.write(b'STOP_MONITOR\n')
                self.serial_port.flush()
                response = self.wait_for_response(1000)
                if response and b'OK:Monitoring stopped' in response:
                    self.log_message("펌웨어 모니터링 모드 비활성화됨")
                else:
                    self.log_message("펌웨어 모니터링 모드 비활성화 실패")
            except Exception as e:
                self.log_message(f"모니터링 중지 오류: {str(e)}")
        
        self.log_message("모니터링 중지")
        
    def capture_loop(self):
        """화면 캡처 루프"""
        while self.is_monitoring:
            try:
                self.capture_screen()
                time.sleep(0.1)  # 100ms 간격
            except Exception as e:
                self.log_message(f"캡처 오류: {str(e)}")
                time.sleep(1)
                
    def status_loop(self):
        """상태 모니터링 루프"""
        while self.is_monitoring:
            try:
                self.request_status()
                time.sleep(1)  # 1초 간격
            except Exception as e:
                self.log_message(f"상태 요청 오류: {str(e)}")
                time.sleep(2)
                
    def capture_screen(self):
        """화면 캡처"""
        if not self.is_connected or not self.serial_port:
            return
            
        try:
            # 이전 데이터 클리어 (버퍼 비우기)
            if self.serial_port.in_waiting > 0:
                old_data = self.serial_port.read(self.serial_port.in_waiting)
                self.log_message(f"이전 버퍼 데이터 제거: {len(old_data)} bytes")
            
            # 화면 요청 명령 전송 (먼저 간단한 테스트로 시작)
            test_mode = False  # 테스트 모드 비활성화 - 실제 데이터 처리
            
            if test_mode:
                self.serial_port.write(b'GET_SIMPLE\n')
                self.log_message("GET_SIMPLE 명령어 전송")
            else:
                self.serial_port.write(b'GET_SCREEN\n')
                self.log_message("GET_SCREEN 명령어 전송")
            
            self.serial_port.flush()
            
            # 응답 대기 및 파싱 - 더 긴 타임아웃과 안정적인 수신
            response_data = b''
            timeout_count = 0
            max_timeout = 150  # 1500ms 타임아웃 (증가)
            
            self.log_message("화면 데이터 수신 시작...")
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 진행상황 로그 (5회마다)
                    if timeout_count % 5 == 0:
                        self.log_message(f"수신 중... {len(response_data)} bytes")
                    
                    # SCREEN_END 패턴을 찾으면 완료
                    if b'SCREEN_END' in response_data:
                        self.log_message(f"수신 완료: {len(response_data)} bytes")
                        break
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            # 수신된 데이터 디버깅 정보
            if len(response_data) > 0:
                # 처음 200바이트를 텍스트로 디코딩하여 헤더 확인
                try:
                    header_text = response_data[:200].decode('utf-8', errors='ignore')
                    self.log_message(f"수신된 헤더: {repr(header_text)}")
                except:
                    self.log_message("헤더 디코딩 실패")
                
                # 마지막 100바이트도 확인
                try:
                    footer_text = response_data[-100:].decode('utf-8', errors='ignore')
                    self.log_message(f"수신된 푸터: {repr(footer_text)}")
                except:
                    self.log_message("푸터 디코딩 실패")
            
            if b'SCREEN_END' in response_data:
                if test_mode:
                    # 테스트 모드에서는 간단한 패턴 생성
                    self.log_message("테스트 데이터 수신 성공")
                    screen_data = self.generate_test_screen()
                    self.update_display(screen_data)
                else:
                    # 실제 펌웨어 데이터 파싱
                    screen_data = self.parse_firmware_screen_data(response_data)
                    if screen_data is not None:
                        self.update_display(screen_data)
                        
                        # 자동 저장이 활성화된 경우
                        if self.auto_save_var.get():
                            self.auto_save_screen(screen_data)
                    else:
                        # 파싱 실패시 테스트 패턴 사용
                        self.log_message("펌웨어 데이터 파싱 실패, 테스트 패턴 사용")
                        screen_data = self.generate_test_screen()
                        self.update_display(screen_data)
            else:
                # 타임아웃 또는 응답 없음
                if len(response_data) > 0:
                    self.log_message(f"불완전한 응답: {len(response_data)} bytes (타임아웃)")
                else:
                    self.log_message("응답 없음 (타임아웃)")
                
                # 실패시 테스트 패턴 사용
                screen_data = self.generate_test_screen()
                self.update_display(screen_data)
                
        except Exception as e:
            self.log_message(f"화면 캡처 실패: {str(e)}")
            # 오류 발생시 테스트 패턴 사용
            screen_data = self.generate_test_screen()
            self.update_display(screen_data)
    
    def parse_firmware_screen_data(self, data):
        """펌웨어에서 받은 화면 데이터 파싱"""
        try:
            # 디버깅 모드 설정
            debug_mode = False  # 디버깅 비활성화
            
            if debug_mode:
                self.log_message(f"수신된 총 데이터 크기: {len(data)} bytes")
            
            # 데이터에서 여러 응답이 섞여있을 수 있으므로 마지막 SCREEN_START를 찾기
            last_start_idx = data.rfind(b'SCREEN_START')
            if last_start_idx == -1:
                self.log_message("SCREEN_START를 찾을 수 없음")
                return None
            
            # 마지막 SCREEN_START 이후의 데이터만 사용
            screen_data_part = data[last_start_idx:]
            
            if debug_mode:
                self.log_message(f"SCREEN_START 위치: {last_start_idx}")
                self.log_message(f"화면 데이터 부분 크기: {len(screen_data_part)} bytes")
            
            # SCREEN_START와 SIZE 정보 찾기 (상대적 위치)
            start_idx = screen_data_part.find(b'SCREEN_START')
            size_idx = screen_data_part.find(b'SIZE:128x64')
            end_idx = screen_data_part.find(b'SCREEN_END')
            
            if start_idx == -1 or size_idx == -1 or end_idx == -1:
                self.log_message(f"헤더 찾기 실패 - START:{start_idx}, SIZE:{size_idx}, END:{end_idx}")
                return None
            
            # SIZE 헤더 다음 개행 문자 이후부터 이미지 데이터 시작
            size_line_end = screen_data_part.find(b'\n', size_idx)
            if size_line_end == -1:
                self.log_message("SIZE 라인 끝을 찾을 수 없음")
                return None
            
            img_start = size_line_end + 1  # \n 다음부터 이미지 데이터
            
            # SCREEN_END 앞의 개행 문자 찾기 (역방향 검색)
            search_start = max(0, end_idx - 10)
            newline_before_end = screen_data_part.rfind(b'\n', search_start, end_idx)
            
            if newline_before_end != -1:
                img_end = newline_before_end
            else:
                img_end = end_idx
            
            # 실제 이미지 데이터 추출
            img_data = screen_data_part[img_start:img_end]
            actual_img_size = len(img_data)
            
            if debug_mode:
                self.log_message(f"이미지 데이터 위치: {img_start} ~ {img_end}, 크기: {actual_img_size} bytes")
            
            # 이미지 데이터 크기 검증 및 조정
            if actual_img_size < 1024:
                self.log_message(f"이미지 데이터 크기 부족: {actual_img_size} bytes, 패딩 추가")
                # 부족한 부분은 0으로 패딩
                img_data = img_data + b'\x00' * (1024 - actual_img_size)
            elif actual_img_size > 1024:
                self.log_message(f"이미지 데이터 크기 초과: {actual_img_size} bytes, 자르기")
                # 초과하는 부분은 자르기
                img_data = img_data[:1024]
            
            # OLED 라이브러리의 reverse 함수와 동일한 비트 뒤집기 함수
            def reverse_byte(byte_val):
                """OLED 라이브러리의 reverse 함수와 동일한 로직"""
                temp = byte_val
                temp = ((temp & 0x55) << 1) | ((temp & 0xaa) >> 1)
                temp = ((temp & 0x33) << 2) | ((temp & 0xcc) >> 2)
                temp = ((temp & 0x0f) << 4) | ((temp & 0xf0) >> 4)
                return temp
            
            # OLED 데이터를 PIL 이미지로 변환
            img_array = np.zeros((self.OLED_HEIGHT, self.OLED_WIDTH), dtype=np.uint8)
            
            # OLED 라이브러리와 동일한 방식으로 처리
            # Width = 128/8 = 16 bytes per row
            width_bytes = 16
            
            for j in range(self.OLED_HEIGHT):  # 64 rows
                for i in range(width_bytes):   # 16 bytes per row
                    byte_idx = i + j * width_bytes
                    if byte_idx < len(img_data):
                        # 원본 바이트 데이터
                        original_byte = img_data[byte_idx]
                        # OLED 라이브러리처럼 비트 뒤집기
                        reversed_byte = reverse_byte(original_byte)
                        
                        # 각 비트를 픽셀로 변환 (8픽셀 = 1바이트)
                        for bit in range(8):
                            x = i * 8 + bit  # 가로 위치
                            y = j            # 세로 위치
                            
                            if x < self.OLED_WIDTH and y < self.OLED_HEIGHT:
                                # 비트 확인 (MSB first)
                                bit_value = (reversed_byte >> (7 - bit)) & 1
                                if bit_value:
                                    img_array[y, x] = 255  # 흰색 픽셀
                                else:
                                    img_array[y, x] = 0    # 검은색 픽셀
            
            if debug_mode:
                self.log_message("이미지 파싱 성공")
                # 픽셀 통계 출력
                white_pixels = np.sum(img_array == 255)
                black_pixels = np.sum(img_array == 0)
                self.log_message(f"픽셀 통계 - 흰색: {white_pixels}, 검은색: {black_pixels}")
                
                # 처음 몇 바이트의 변환 과정 출력
                if len(img_data) >= 4:
                    for i in range(min(4, len(img_data))):
                        original = img_data[i]
                        reversed_val = reverse_byte(original)
                        self.log_message(f"바이트 {i}: 0x{original:02x} -> 0x{reversed_val:02x} (binary: {reversed_val:08b})")
                
                # 16진수 덤프 (처음 64바이트만)
                if len(img_data) >= 64:
                    hex_dump = ""
                    for i in range(0, 64, 16):
                        hex_line = " ".join(f"{img_data[i+j]:02x}" for j in range(min(16, 64-i)))
                        hex_dump += f"{i:04x}: {hex_line}\n"
                    self.log_message(f"이미지 데이터 Hex Dump (처음 64바이트):\n{hex_dump}")
            
            return img_array
            
        except Exception as e:
            self.log_message(f"데이터 파싱 오류: {str(e)}")
            import traceback
            self.log_message(f"상세 오류: {traceback.format_exc()}")
            return None
        
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
            # PIL 이미지로 변환
            img = Image.fromarray(screen_data)
            
            # 확대
            scale = self.scale_var.get()
            img = img.resize((self.OLED_WIDTH * scale, self.OLED_HEIGHT * scale), Image.NEAREST)
            
            # Tkinter PhotoImage로 변환
            photo = ImageTk.PhotoImage(img)
            
            # 캔버스 업데이트
            self.canvas.delete("all")
            self.canvas.create_image(256, 128, image=photo)
            self.canvas.image = photo  # 참조 유지
            
            self.current_screen = screen_data
            
        except Exception as e:
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
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        
        self.status_text.insert(tk.END, log_msg)
        self.status_text.see(tk.END)
        print(log_msg.strip())  # 콘솔에도 출력
        
    def open_settings(self):
        """설정 창 열기"""
        messagebox.showinfo("설정", "설정 기능은 향후 버전에서 제공됩니다")
        
    def show_help(self):
        """도움말 표시"""
        help_text = """OnBoard OLED Monitor v1.1

🔗 연결 설정:
1. 시리얼 포트와 보드레이트를 설정합니다 (기본: 115200)
2. '연결' 버튼을 클릭하여 디바이스에 연결합니다

📺 모니터링:
1. '모니터링 시작'을 클릭하여 실시간 모니터링을 시작합니다
2. 화면 확대 비율을 조절할 수 있습니다 (1x~8x)
3. '화면 캡처'로 현재 화면을 저장할 수 있습니다
4. 자동 저장 기능으로 주기적 저장이 가능합니다

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

문의: OnBoard LED Timer Project
버전: v1.1 (실시간 모니터링 및 원격 제어)
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
            self.serial_port.write(b'START_TIMER\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response()
            if response and b'OK:Timer started' in response:
                self.log_message("타이머가 시작되었습니다")
            else:
                self.log_message("타이머 시작 실패")
                
        except Exception as e:
            self.log_message(f"원격 제어 오류: {str(e)}")
    
    def remote_stop_timer(self):
        """원격 타이머 정지"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            self.serial_port.write(b'STOP_TIMER\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response()
            if response and b'OK:Timer stopped' in response:
                self.log_message("타이머가 정지되었습니다")
            else:
                self.log_message("타이머 정지 실패")
                
        except Exception as e:
            self.log_message(f"원격 제어 오류: {str(e)}")
    
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
            
            command = f"SET_TIMER:{minutes:0>2}:{seconds:0>2}\n"
            self.serial_port.write(command.encode())
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response()
            if response and b'OK:Timer set' in response:
                self.log_message(f"타이머가 {minutes}:{seconds}으로 설정되었습니다")
            else:
                self.log_message("타이머 설정 실패")
                
        except Exception as e:
            self.log_message(f"원격 제어 오류: {str(e)}")
    
    def remote_reset(self):
        """원격 시스템 리셋"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        # 확인 대화상자
        if not messagebox.askyesno("확인", "시스템을 리셋하시겠습니까?"):
            return
            
        try:
            self.serial_port.write(b'RESET\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response()
            if response and b'OK:System reset' in response:
                self.log_message("시스템이 리셋되었습니다")
            else:
                self.log_message("시스템 리셋 실패")
                
        except Exception as e:
            self.log_message(f"원격 제어 오류: {str(e)}")
    
    def remote_ping(self):
        """연결 테스트"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            start_time = time.time()
            self.serial_port.write(b'PING\n')
            self.serial_port.flush()
            
            # 응답 확인
            response = self.wait_for_response()
            elapsed_time = time.time() - start_time
            
            if response and b'PONG' in response:
                self.log_message(f"연결 테스트 성공 (응답시간: {elapsed_time*1000:.1f}ms)")
            else:
                self.log_message("연결 테스트 실패")
                
        except Exception as e:
            self.log_message(f"연결 테스트 오류: {str(e)}")
    
    def wait_for_response(self, timeout_ms=500):
        """응답 대기 (원격 제어용)"""
        response_data = b''
        timeout_count = 0
        max_timeout = timeout_ms // 10  # 10ms 단위
        
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
        
        return response_data

    def test_connection(self):
        """기본 연결 테스트 (TEST 명령어)"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            self.serial_port.write(b'TEST\n')
            self.serial_port.flush()
            
            response = self.wait_for_response(1000)
            if response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                self.log_message(f"TEST 응답: {response_str}")
            else:
                self.log_message("TEST 응답 없음")
                
        except Exception as e:
            self.log_message(f"TEST 명령어 오류: {str(e)}")

    def test_simple_screen(self):
        """간단한 화면 데이터 테스트 (GET_SIMPLE 명령어)"""
        if not self.is_connected:
            messagebox.showwarning("경고", "디바이스가 연결되지 않았습니다")
            return
            
        try:
            # 이전 데이터 클리어
            if self.serial_port.in_waiting > 0:
                old_data = self.serial_port.read(self.serial_port.in_waiting)
                self.log_message(f"이전 버퍼 데이터 제거: {len(old_data)} bytes")
            
            self.serial_port.write(b'GET_SIMPLE\n')
            self.serial_port.flush()
            self.log_message("GET_SIMPLE 명령어 전송")
            
            # 응답 대기
            response_data = b''
            timeout_count = 0
            max_timeout = 150  # 1.5초 타임아웃
            
            self.log_message("GET_SIMPLE 응답 수신 중...")
            
            while timeout_count < max_timeout:
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting)
                    response_data += chunk
                    
                    # 진행상황 표시
                    if timeout_count % 10 == 0:
                        self.log_message(f"수신 중... {len(response_data)} bytes")
                    
                    if b'SCREEN_END' in response_data:
                        break
                else:
                    time.sleep(0.01)
                    timeout_count += 1
            
            if len(response_data) > 0:
                self.log_message(f"GET_SIMPLE 응답 수신 완료: {len(response_data)} bytes")
                
                # 실제 펌웨어 데이터 파싱 시도
                screen_data = self.parse_firmware_screen_data(response_data)
                if screen_data is not None:
                    self.log_message("GET_SIMPLE 데이터 파싱 성공")
                    self.update_display(screen_data)
                else:
                    self.log_message("GET_SIMPLE 데이터 파싱 실패")
                    # 파싱 실패시 수신된 텍스트 출력
                    try:
                        text_part = response_data.decode('utf-8', errors='ignore')
                        self.log_message(f"텍스트 부분: {repr(text_part)}")
                    except:
                        pass
                    
                    # 16진수 덤프
                    if len(response_data) > 0:
                        hex_dump = ""
                        for i in range(0, min(128, len(response_data)), 16):
                            hex_line = " ".join(f"{response_data[i+j]:02x}" for j in range(min(16, len(response_data)-i)))
                            hex_dump += f"{i:04x}: {hex_line}\n"
                        self.log_message(f"응답 데이터 Hex Dump:\n{hex_dump}")
                    
                    # 테스트 패턴 표시
                    screen_data = self.generate_test_screen()
                    self.update_display(screen_data)
            else:
                self.log_message("GET_SIMPLE 응답 없음")
                
        except Exception as e:
            self.log_message(f"GET_SIMPLE 명령어 오류: {str(e)}")
            import traceback
            self.log_message(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    app = OLEDMonitor()
    app.run() 