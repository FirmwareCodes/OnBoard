#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배터리 로그 분석 GUI 애플리케이션
STM32L412 OnBoard 시스템용
"""

import sys
import os
import traceback
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QLineEdit, QComboBox, 
                            QTextEdit, QFileDialog, QMessageBox, QProgressBar,
                            QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,
                            QTabWidget, QTableWidget, QTableWidgetItem,
                            QSplitter, QFrame, QToolButton, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon

# 배터리 파서 임포트
from battery_log_parser import BatteryLogParser

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# 한글 폰트 설정
plt.rcParams['font.family'] = ['Malgun Gothic', 'NanumGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class AnalysisWorker(QThread):
    """배터리 분석 작업을 수행하는 워커 스레드"""
    
    progress = pyqtSignal(int)  # 진행률
    message = pyqtSignal(str)   # 상태 메시지
    finished = pyqtSignal(dict) # 완료 시 결과
    error = pyqtSignal(str)     # 에러 메시지
    
    def __init__(self, file_path, load_value, load_type, battery_capacity, battery_type):
        super().__init__()
        self.file_path = file_path
        self.load_value = load_value
        self.load_type = load_type
        self.battery_capacity = battery_capacity
        self.battery_type = battery_type
        self.parser = BatteryLogParser()
    
    def run(self):
        try:
            self.progress.emit(10)
            self.message.emit("로그 파일 파싱 중...")
            
            # 파일 파싱
            data = self.parser.parse_log_file(self.file_path)
            if data is None:
                self.error.emit("로그 파일 파싱에 실패했습니다.")
                return
            
            self.progress.emit(30)
            self.message.emit("배터리 성능 분석 중...")
            
            # 성능 분석
            analysis = self.parser.analyze_with_ui_input(
                df=data,
                load_value=self.load_value,
                load_type=self.load_type,
                battery_capacity_ah=self.battery_capacity,
                battery_type=self.battery_type
            )
            
            self.progress.emit(60)
            self.message.emit("사이클 수명 분석 중...")
            
            # 사이클 수명 분석
            cycle_analysis = self.parser.calculate_cycle_life_estimation(
                df=data,
                load_watts=self.load_value if self.load_type == 'watts' else None,
                load_amps=self.load_value if self.load_type == 'amps' else None,
                battery_capacity_ah=self.battery_capacity,
                battery_type=self.battery_type
            )
            
            self.progress.emit(80)
            self.message.emit("분석 요약 생성 중...")
            
            # 요약 정보 생성
            summary = self.parser.get_analysis_summary(
                df=data,
                load_value=self.load_value,
                load_type=self.load_type,
                battery_capacity_ah=self.battery_capacity,
                battery_type=self.battery_type
            )
            
            self.progress.emit(100)
            self.message.emit("분석 완료!")
            
            # 결과 반환
            result = {
                'data': data,
                'analysis': analysis,
                'cycle_analysis': cycle_analysis,
                'summary': summary,
                'file_path': self.file_path
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"분석 중 오류 발생: {str(e)}\n{traceback.format_exc()}")

class HelpDialog(QDialog):
    """배터리 용어 및 계산 설명 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("배터리 분석 용어 설명")
        self.setGeometry(200, 200, 800, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 제목
        title_label = QLabel("🔋 배터리 분석 용어 및 계산 방법")
        title_label.setFont(QFont("", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 기본 용어 탭
        basic_tab = QWidget()
        tab_widget.addTab(basic_tab, "📚 기본 용어")
        self.setup_basic_terms_tab(basic_tab)
        
        # 부하 계산 탭
        load_tab = QWidget()
        tab_widget.addTab(load_tab, "⚡ 부하 계산")
        self.setup_load_calculation_tab(load_tab)
        
        # 분석 지표 탭
        analysis_tab = QWidget()
        tab_widget.addTab(analysis_tab, "📊 분석 지표")
        self.setup_analysis_metrics_tab(analysis_tab)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    def setup_basic_terms_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <h3>🔋 배터리 기본 용어</h3>
        
        <h4>📏 전압 관련</h4>
        <ul>
        <li><b>명목 전압 (Nominal Voltage)</b>: 배터리의 표준 작동 전압 (6S = 22.2V)</li>
        <li><b>최대 전압 (Max Voltage)</b>: 완전 충전 시 전압 (6S = 25.2V)</li>
        <li><b>최소 전압 (Min Voltage)</b>: 사용 가능한 최저 전압 (6S = 18.0V)</li>
        <li><b>전압 강하</b>: 시간에 따른 전압 감소량</li>
        <li><b>추천 충전 완료 전압</b>: 배터리 수명을 고려한 충전 상한 전압</li>
        <li><b>추천 방전 종료 전압</b>: 배터리 수명을 고려한 방전 하한 전압</li>
        </ul>
        
        <h4>⚡ 전류 및 전력</h4>
        <ul>
        <li><b>암페어 (A)</b>: 전류의 단위, 초당 흐르는 전자의 양</li>
        <li><b>와트 (W)</b>: 전력의 단위, 전압 × 전류 (P = V × I)</li>
        <li><b>암페어시 (Ah)</b>: 배터리 용량, 1시간 동안 공급할 수 있는 전류량</li>
        </ul>
        
        <h4>🔄 충전 상태</h4>
        <ul>
        <li><b>SOC (State of Charge)</b>: 현재 충전량 / 전체 용량 × 100 (%)</li>
        <li><b>DOD (Depth of Discharge)</b>: 방전 깊이, 사용한 용량 비율</li>
        <li><b>사이클</b>: 충전 → 방전 → 충전의 한 번 완료</li>
        </ul>
        
        <h4>💪 성능 지표</h4>
        <ul>
        <li><b>C-rate</b>: 방전율, 1C = 1시간에 전체 용량 방전</li>
        <li><b>건강도</b>: 배터리 상태 점수 (0-100점)</li>
        <li><b>효율성</b>: 이론값 대비 실제 성능 비율</li>
        <li><b>내부 저항</b>: 배터리 내부의 전기 저항 (낮을수록 좋음)</li>
        </ul>
        
        <h4>🔧 내부 저항</h4>
        <ul>
        <li><b>단위</b>: Ω (옴) 또는 mΩ (밀리옴)</li>
        <li><b>우수</b>: 20-50mΩ/cell (신품 수준)</li>
        <li><b>양호</b>: 50-100mΩ/cell (정상 범위)</li>
        <li><b>보통</b>: 100-200mΩ/cell (모니터링 필요)</li>
        <li><b>주의</b>: 200-500mΩ/cell (성능 저하)</li>
        <li><b>교체 필요</b>: 500mΩ/cell 이상</li>
        </ul>
        
        <h4>⚡ 충전/방전 이벤트</h4>
        <ul>
        <li><b>급격한 전압 상승</b>: 충전 시작 또는 부하 제거 감지</li>
        <li><b>충전 이벤트</b>: 1V 이상의 급격한 전압 상승</li>
        <li><b>부하 종료</b>: 0.2V~1V의 전압 상승 (부하 제거)</li>
        <li><b>데이터 필터링</b>: 충전/부하 종료 구간을 분석에서 제외</li>
        </ul>
        """)
        
        layout.addWidget(text)
    
    def setup_load_calculation_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <h3>⚡ 부하 계산 방식</h3>
        
        <h4>🔌 와트 (W) 입력 시</h4>
        <p><b>일정 전력 부하</b> - 전압이 변해도 전력은 일정하게 유지</p>
        <ul>
        <li>공식: P = V × I (전력 = 전압 × 전류)</li>
        <li>전압 ↓ → 전류 ↑ (전력 유지를 위해)</li>
        <li>예시: 50W 부하</li>
        <li>&nbsp;&nbsp;• 25V에서: 2.0A (50W ÷ 25V)</li>
        <li>&nbsp;&nbsp;• 20V에서: 2.5A (50W ÷ 20V)</li>
        <li>&nbsp;&nbsp;• 18V에서: 2.78A (50W ÷ 18V)</li>
        </ul>
        
        <h4>🔋 암페어 (A) 입력 시</h4>
        <p><b>일정 전류 부하</b> - 전압이 변해도 전류는 일정하게 유지</p>
        <ul>
        <li>공식: I = 일정값 (전류 = 설정값 고정)</li>
        <li>전압 ↓ → 전력 ↓ (전류는 그대로)</li>
        <li>예시: 2.0A 부하</li>
        <li>&nbsp;&nbsp;• 25V에서: 50W (25V × 2.0A)</li>
        <li>&nbsp;&nbsp;• 20V에서: 40W (20V × 2.0A)</li>
        <li>&nbsp;&nbsp;• 18V에서: 36W (18V × 2.0A)</li>
        </ul>
        
        <h4>🎯 실제 사용 예시</h4>
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f0f0f0;">
            <th>부하 타입</th><th>설정값</th><th>25V</th><th>22V</th><th>20V</th><th>18V</th>
        </tr>
        <tr>
            <td rowspan="2"><b>50W 부하</b></td>
            <td>전류</td><td>2.0A</td><td>2.27A</td><td>2.5A</td><td>2.78A</td>
        </tr>
        <tr>
            <td>전력</td><td>50W</td><td>50W</td><td>50W</td><td>50W</td>
        </tr>
        <tr>
            <td rowspan="2"><b>2A 부하</b></td>
            <td>전류</td><td>2.0A</td><td>2.0A</td><td>2.0A</td><td>2.0A</td>
        </tr>
        <tr>
            <td>전력</td><td>50W</td><td>44W</td><td>40W</td><td>36W</td>
        </tr>
        </table>
        
        <h4>💡 선택 가이드</h4>
        <ul>
        <li><b>와트 선택</b>: LED 조명, 히터 등 일정 전력 소비 장치</li>
        <li><b>암페어 선택</b>: 모터, 저항 부하 등 일정 전류 소비 장치</li>
        </ul>
        """)
        
        layout.addWidget(text)
    
    def setup_analysis_metrics_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <h3>📊 분석 지표 상세 설명</h3>
        
        <h4>💚 건강도 점수 (0-100점)</h4>
        <ul>
        <li><b>90-100점</b>: 우수 - 새 배터리 수준의 성능</li>
        <li><b>75-89점</b>: 양호 - 정상적인 사용 가능</li>
        <li><b>60-74점</b>: 보통 - 주의 깊은 모니터링 필요</li>
        <li><b>40-59점</b>: 주의 - 성능 저하, 교체 검토</li>
        <li><b>0-39점</b>: 교체 필요 - 즉시 교체 권장</li>
        </ul>
        
        <h4>⚡ C-rate (방전율)</h4>
        <ul>
        <li><b>1C</b>: 1시간에 전체 용량 방전 (2.5Ah → 2.5A)</li>
        <li><b>0.5C</b>: 2시간에 전체 용량 방전 (2.5Ah → 1.25A)</li>
        <li><b>2C</b>: 30분에 전체 용량 방전 (2.5Ah → 5A)</li>
        <li>일반적으로 1C 이하가 배터리 수명에 유리</li>
        </ul>
        
        <h4>🔄 사이클 수명</h4>
        <ul>
        <li><b>예상 사이클 수명</b>: 80% 용량까지 사용 가능한 충방전 횟수</li>
        <li><b>DOD 영향</b>: 방전 깊이가 클수록 수명 단축</li>
        <li>&nbsp;&nbsp;• 20% DOD: 5,000+ 사이클</li>
        <li>&nbsp;&nbsp;• 50% DOD: 2,000+ 사이클</li>
        <li>&nbsp;&nbsp;• 80% DOD: 1,000+ 사이클</li>
        <li>&nbsp;&nbsp;• 100% DOD: 500+ 사이클</li>
        </ul>
        
        <h4>📈 효율성 등급</h4>
        <ul>
        <li><b>우수</b>: 이론값의 90% 이상 성능</li>
        <li><b>양호</b>: 이론값의 75-89% 성능</li>
        <li><b>보통</b>: 이론값의 60-74% 성능</li>
        <li><b>개선 필요</b>: 이론값의 60% 미만</li>
        </ul>
        
        <h4>⚠️ 스트레스 요인</h4>
        <ul>
        <li><b>전압 스트레스</b>: 최소 전압 이하 사용 시 수명 단축</li>
        <li><b>C-rate 스트레스</b>: 높은 방전율 사용 시 발열 및 수명 단축</li>
        <li><b>온도 스트레스</b>: 전압 변동성으로 추정하는 온도 영향</li>
        <li><b>DOD 스트레스</b>: 깊은 방전 사용 시 용량 감소 가속화</li>
        </ul>
        
        <h4>🎯 추천 전압 설정 (6S 배터리 기준)</h4>
        <ul>
        <li><b>충전 완료 전압</b>: 25.2V (4.2V/cell) - 완전 충전</li>
        <li><b>방전 종료 전압</b>: 19.8V (3.3V/cell) - 수명 연장을 위한 권장</li>
        <li><b>안전 최소 전압</b>: 18.0V (3.0V/cell) - 절대 하한선</li>
        <li><b>명목 전압</b>: 22.2V (3.7V/cell) - 표준 작동 전압</li>
        </ul>
        
        <h4>📊 데이터 품질</h4>
        <ul>
        <li><b>양호</b>: 충전 이벤트 제외 후 70% 이상 데이터 유지</li>
        <li><b>제한적</b>: 충전 이벤트 제외 후 70% 미만 데이터</li>
        <li><b>충전 감지</b>: 0.2V 이상 급격한 전압 상승 자동 감지</li>
        <li><b>부하 종료</b>: 부하 제거로 인한 전압 회복 감지</li>
        </ul>
        
        <h4>🎯 사용 권장사항</h4>
        <ul>
        <li>DOD 80% 이하 사용 권장 (19.8V 이상 유지)</li>
        <li>C-rate 1C 이하 유지</li>
        <li>최소 전압 (18V) 이하 방전 금지</li>
        <li>정기적인 완전 충전 수행 (25.2V까지)</li>
        <li>고온 환경 장시간 사용 금지</li>
        <li>충전 중 데이터는 분석에서 자동 제외</li>
        </ul>
        """)
        
        layout.addWidget(text)

class BatteryAnalyzerGUI(QMainWindow):
    """배터리 분석 GUI 메인 클래스"""
    
    def __init__(self):
        super().__init__()
        self.parser = BatteryLogParser()
        self.current_data = None
        self.current_analysis = None
        self.current_cycle_analysis = None
        self.current_summary = None
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("배터리 로그 분석기 - STM32L412 OnBoard")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 상단 제어 패널
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 상태 메시지
        self.status_label = QLabel("파일을 선택하고 분석 설정을 입력하세요.")
        main_layout.addWidget(self.status_label)
        
        # 탭 위젯 (결과 표시)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 탭 생성
        self.create_tabs()
        
        # 스타일 적용
        self.apply_styles()
    
    def create_control_panel(self):
        """제어 패널 생성"""
        panel = QGroupBox("분석 설정")
        layout = QGridLayout(panel)
        
        # 파일 선택
        layout.addWidget(QLabel("로그 파일:"), 0, 0)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("로그 파일을 선택하세요...")
        layout.addWidget(self.file_path_edit, 0, 1, 1, 2)
        
        self.browse_button = QPushButton("파일 선택")
        self.browse_button.clicked.connect(self.browse_file)
        layout.addWidget(self.browse_button, 0, 3)
        
        # 부하 설정
        layout.addWidget(QLabel("부하 타입:"), 1, 0)
        self.load_type_combo = QComboBox()
        self.load_type_combo.addItems(["watts", "amps"])
        self.load_type_combo.currentTextChanged.connect(self.update_load_unit)
        layout.addWidget(self.load_type_combo, 1, 1)
        
        # 부하 도움말 버튼 (부하 타입 옆에)
        help_button_load = QToolButton()
        help_button_load.setText("?")
        help_button_load.setMaximumSize(25, 25)
        help_button_load.setToolTip("부하 타입 설명")
        help_button_load.clicked.connect(self.show_load_help)
        layout.addWidget(help_button_load, 1, 2)
        
        self.load_value_spin = QDoubleSpinBox()
        self.load_value_spin.setRange(0.1, 1000.0)
        self.load_value_spin.setValue(50.0)
        self.load_value_spin.setSuffix(" W")
        layout.addWidget(self.load_value_spin, 1, 3)
        
        # 배터리 설정
        layout.addWidget(QLabel("배터리 타입:"), 2, 0)
        self.battery_type_combo = QComboBox()
        self.battery_type_combo.addItems(["6s", "3s", "single"])
        layout.addWidget(self.battery_type_combo, 2, 1)
        
        # 배터리 도움말 버튼 (배터리 타입 옆에)
        help_button_battery = QToolButton()
        help_button_battery.setText("?")
        help_button_battery.setMaximumSize(25, 25)
        help_button_battery.setToolTip("배터리 타입 설명")
        help_button_battery.clicked.connect(self.show_battery_help)
        layout.addWidget(help_button_battery, 2, 2)
        
        self.capacity_spin = QDoubleSpinBox()
        self.capacity_spin.setRange(0.1, 100.0)
        self.capacity_spin.setValue(2.5)
        self.capacity_spin.setSuffix(" Ah")
        layout.addWidget(self.capacity_spin, 2, 3)
        
        # 분석 시작 버튼
        self.analyze_button = QPushButton("🔍 분석 시작")
        self.analyze_button.setMinimumHeight(40)
        self.analyze_button.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_button, 3, 0, 1, 2)
        
        # 전체 도움말 버튼
        self.help_button = QPushButton("❓ 용어 설명")
        self.help_button.setMinimumHeight(40)
        self.help_button.clicked.connect(self.show_help_dialog)
        layout.addWidget(self.help_button, 3, 2, 1, 2)
        
        return panel
    
    def create_tabs(self):
        """결과 표시 탭들 생성"""
        # 요약 탭
        self.summary_tab = QWidget()
        self.tab_widget.addTab(self.summary_tab, "📊 분석 요약")
        self.setup_summary_tab()
        
        # 그래프 탭
        self.graph_tab = QWidget()
        self.tab_widget.addTab(self.graph_tab, "📈 그래프")
        self.setup_graph_tab()
        
        # 상세 분석 탭
        self.detail_tab = QWidget()
        self.tab_widget.addTab(self.detail_tab, "📋 상세 분석")
        self.setup_detail_tab()
        
        # 보고서 탭
        self.report_tab = QWidget()
        self.tab_widget.addTab(self.report_tab, "📄 보고서")
        self.setup_report_tab()
    
    def setup_summary_tab(self):
        """요약 탭 설정"""
        layout = QVBoxLayout(self.summary_tab)
        
        # 주요 지표 패널
        indicators_panel = QGroupBox("주요 지표")
        indicators_layout = QGridLayout(indicators_panel)
        
        # 지표 레이블들 (초기에는 빈값)
        self.health_score_label = QLabel("건강도: -")
        self.avg_voltage_label = QLabel("평균 전압: -")
        self.duration_label = QLabel("테스트 시간: -")
        self.cycles_label = QLabel("예상 사이클: -")
        self.efficiency_label = QLabel("효율성: -")
        self.c_rate_label = QLabel("C-rate: -")
        self.load_type_label = QLabel("부하 타입: -")
        self.load_value_label = QLabel("부하 값: -")
        self.resistance_label = QLabel("내부 저항: -")
        self.resistance_grade_label = QLabel("저항 등급: -")
        
        indicators_layout.addWidget(self.health_score_label, 0, 0)
        indicators_layout.addWidget(self.avg_voltage_label, 0, 1)
        indicators_layout.addWidget(self.duration_label, 1, 0)
        indicators_layout.addWidget(self.cycles_label, 1, 1)
        indicators_layout.addWidget(self.efficiency_label, 2, 0)
        indicators_layout.addWidget(self.c_rate_label, 2, 1)
        indicators_layout.addWidget(self.load_type_label, 3, 0)
        indicators_layout.addWidget(self.load_value_label, 3, 1)
        indicators_layout.addWidget(self.resistance_label, 4, 0)
        indicators_layout.addWidget(self.resistance_grade_label, 4, 1)
        
        layout.addWidget(indicators_panel)
        
        # 데이터 품질 패널 추가
        quality_panel = QGroupBox("데이터 품질 및 이벤트")
        quality_layout = QGridLayout(quality_panel)
        
        self.original_data_label = QLabel("원본 데이터: -")
        self.analysis_data_label = QLabel("분석 데이터: -")
        self.charging_events_label = QLabel("충전/부하종료: -")
        self.data_quality_label = QLabel("데이터 품질: -")
        
        quality_layout.addWidget(self.original_data_label, 0, 0)
        quality_layout.addWidget(self.analysis_data_label, 0, 1)
        quality_layout.addWidget(self.charging_events_label, 1, 0)
        quality_layout.addWidget(self.data_quality_label, 1, 1)
        
        layout.addWidget(quality_panel)
        
        # 추천 전압 패널 추가
        voltage_panel = QGroupBox("추천 전압 설정")
        voltage_layout = QGridLayout(voltage_panel)
        
        self.recommended_100_label = QLabel("충전 완료: -")
        self.recommended_0_label = QLabel("방전 종료: -")
        self.safe_range_label = QLabel("안전 범위: -")
        self.cell_voltage_label = QLabel("셀당 권장: -")
        
        voltage_layout.addWidget(self.recommended_100_label, 0, 0)
        voltage_layout.addWidget(self.recommended_0_label, 0, 1)
        voltage_layout.addWidget(self.safe_range_label, 1, 0)
        voltage_layout.addWidget(self.cell_voltage_label, 1, 1)
        
        layout.addWidget(voltage_panel)
        
        # 권장사항 패널
        recommendations_panel = QGroupBox("권장사항")
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(150)
        recommendations_layout = QVBoxLayout(recommendations_panel)
        recommendations_layout.addWidget(self.recommendations_text)
        
        layout.addWidget(recommendations_panel)
        
        layout.addStretch()
    
    def setup_graph_tab(self):
        """그래프 탭 설정"""
        layout = QVBoxLayout(self.graph_tab)
        
        # matplotlib 캔버스
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 그래프 제어 버튼들
        button_layout = QHBoxLayout()
        
        self.refresh_graph_button = QPushButton("🔄 그래프 새로고침")
        self.refresh_graph_button.clicked.connect(self.update_graphs)
        button_layout.addWidget(self.refresh_graph_button)
        
        self.save_graph_button = QPushButton("💾 그래프 저장")
        self.save_graph_button.clicked.connect(self.save_graphs)
        button_layout.addWidget(self.save_graph_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def setup_detail_tab(self):
        """상세 분석 탭 설정"""
        layout = QVBoxLayout(self.detail_tab)
        
        # 데이터 테이블
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
    
    def setup_report_tab(self):
        """보고서 탭 설정"""
        layout = QVBoxLayout(self.report_tab)
        
        # 보고서 텍스트
        self.report_text = QTextEdit()
        self.report_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.report_text)
        
        # 보고서 제어 버튼들
        button_layout = QHBoxLayout()
        
        self.generate_report_button = QPushButton("📄 종합 보고서 생성")
        self.generate_report_button.clicked.connect(self.generate_comprehensive_report)
        button_layout.addWidget(self.generate_report_button)
        
        self.save_report_button = QPushButton("💾 보고서 저장")
        self.save_report_button.clicked.connect(self.save_report)
        button_layout.addWidget(self.save_report_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def apply_styles(self):
        """스타일 적용"""
        style = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 8px;
            margin: 10px 0px;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        QToolButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        }
        QToolButton:hover {
            background-color: #1976D2;
        }
        QToolButton:pressed {
            background-color: #1565C0;
        }
        """
        self.setStyleSheet(style)
    
    def update_load_unit(self, load_type):
        """부하 단위 업데이트"""
        if load_type == "watts":
            self.load_value_spin.setSuffix(" W")
        else:
            self.load_value_spin.setSuffix(" A")
    
    def browse_file(self):
        """파일 선택 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "배터리 로그 파일 선택", 
            "", 
            "텍스트 파일 (*.txt);;로그 파일 (*.log);;CSV 파일 (*.csv);;모든 파일 (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def start_analysis(self):
        """분석 시작"""
        file_path = self.file_path_edit.text().strip()
        
        if not file_path:
            QMessageBox.warning(self, "경고", "로그 파일을 선택해주세요.")
            return
        
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "경고", "선택한 파일이 존재하지 않습니다.")
            return
        
        # 분석 설정 가져오기
        load_value = self.load_value_spin.value()
        load_type = self.load_type_combo.currentText()
        battery_capacity = self.capacity_spin.value()
        battery_type = self.battery_type_combo.currentText()
        
        # UI 비활성화
        self.analyze_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 워커 스레드 시작
        self.worker = AnalysisWorker(
            file_path, load_value, load_type, battery_capacity, battery_type
        )
        
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.message.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        
        self.worker.start()
    
    def on_analysis_finished(self, result):
        """분석 완료 처리"""
        self.current_data = result['data']
        self.current_analysis = result['analysis']
        self.current_cycle_analysis = result.get('cycle_analysis')
        self.current_summary = result.get('summary')
        
        # UI 업데이트
        self.update_summary_display()
        self.update_graphs()
        self.update_detail_table()
        
        # UI 활성화
        self.analyze_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("분석 완료! 결과를 확인하세요.")
        
        QMessageBox.information(self, "완료", "배터리 분석이 완료되었습니다!")
    
    def on_analysis_error(self, error_msg):
        """분석 오류 처리"""
        self.analyze_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("분석 중 오류가 발생했습니다.")
        
        QMessageBox.critical(self, "오류", error_msg)
    
    def update_summary_display(self):
        """요약 정보 업데이트"""
        if not self.current_summary:
            return
        
        summary = self.current_summary
        
        # 주요 지표 업데이트
        self.health_score_label.setText(f"건강도: {summary.get('health_score', 0):.0f}/100 ({summary.get('health_grade', '-')})")
        self.avg_voltage_label.setText(f"평균 전압: {summary.get('avg_voltage', 0):.3f}V")
        self.duration_label.setText(f"테스트 시간: {summary.get('duration_hours', 0):.2f}시간")
        self.cycles_label.setText(f"예상 사이클: {summary.get('estimated_cycles', 0):,}회")
        self.efficiency_label.setText(f"효율성: {summary.get('efficiency', '-')}")
        self.c_rate_label.setText(f"C-rate: {summary.get('c_rate', 0):.2f}C")
        self.load_type_label.setText(f"부하 타입: {self.load_type_combo.currentText()}")
        self.load_value_label.setText(f"부하 값: {self.load_value_spin.value():.2f} {self.load_type_combo.currentText()}")
        
        # 내부 저항 정보 표시
        if 'internal_resistance' in summary:
            resistance_ohm = summary['internal_resistance']
            if resistance_ohm < 1:
                self.resistance_label.setText(f"내부 저항: {resistance_ohm*1000:.1f}mΩ")
            else:
                self.resistance_label.setText(f"내부 저항: {resistance_ohm:.3f}Ω")
        else:
            self.resistance_label.setText("내부 저항: -")
        
        if 'resistance_grade' in summary:
            grade = summary['resistance_grade']
            cell_resistance = summary.get('resistance_per_cell', 0)
            self.resistance_grade_label.setText(f"저항 등급: {grade} ({cell_resistance:.1f}mΩ/cell)")
        else:
            self.resistance_grade_label.setText("저항 등급: -")
        
        # 데이터 품질 정보 업데이트
        if self.current_analysis:
            if 'original_data_info' in self.current_analysis:
                original_info = self.current_analysis['original_data_info']
                filtered_info = self.current_analysis['filtered_data_info']
                
                self.original_data_label.setText(f"원본 데이터: {original_info['total_records']:,}개")
                self.analysis_data_label.setText(f"분석 데이터: {filtered_info['analysis_records']:,}개")
                self.charging_events_label.setText(f"충전/부하종료: {original_info['charging_events']}개 이벤트")
                
                quality = filtered_info['data_quality']
                quality_text = {"good": "양호", "limited": "제한적"}.get(quality, quality)
                self.data_quality_label.setText(f"데이터 품질: {quality_text}")
                
                if filtered_info['excluded_records'] > 0:
                    self.data_quality_label.setText(
                        f"데이터 품질: {quality_text} (제외: {filtered_info['excluded_records']}개)")
            else:
                self.original_data_label.setText("원본 데이터: -")
                self.analysis_data_label.setText("분석 데이터: -")
                self.charging_events_label.setText("충전/부하종료: -")
                self.data_quality_label.setText("데이터 품질: -")
            
            # 추천 전압 정보 업데이트
            if 'voltage_recommendations' in self.current_analysis:
                voltage_rec = self.current_analysis['voltage_recommendations']
                
                self.recommended_100_label.setText(f"충전 완료: {voltage_rec['recommended_100_percent']:.1f}V")
                self.recommended_0_label.setText(f"방전 종료: {voltage_rec['recommended_0_percent']:.1f}V")
                
                safe_range = voltage_rec['safe_operating_range']
                self.safe_range_label.setText(f"안전 범위: {safe_range['min']:.1f}V~{safe_range['max']:.1f}V")
                
                per_cell = voltage_rec['per_cell_recommendations']
                self.cell_voltage_label.setText(
                    f"셀당 권장: {per_cell['recommended_0_percent_per_cell']:.2f}V~{per_cell['recommended_100_percent_per_cell']:.2f}V")
            else:
                self.recommended_100_label.setText("충전 완료: -")
                self.recommended_0_label.setText("방전 종료: -")
                self.safe_range_label.setText("안전 범위: -")
                self.cell_voltage_label.setText("셀당 권장: -")
        
        # 권장사항 업데이트
        if self.current_analysis and 'health_assessment' in self.current_analysis:
            recommendations = self.current_analysis['health_assessment'].get('recommendations', [])
            rec_text = "\n".join(f"• {rec}" for rec in recommendations)
            self.recommendations_text.setText(rec_text)
    
    def update_graphs(self):
        """그래프 업데이트"""
        if self.current_data is None:
            return
        
        self.figure.clear()
        
        # 2x2 서브플롯 생성
        ax1 = self.figure.add_subplot(2, 2, 1)
        ax2 = self.figure.add_subplot(2, 2, 2)
        ax3 = self.figure.add_subplot(2, 2, 3)
        ax4 = self.figure.add_subplot(2, 2, 4)
        
        data = self.current_data
        
        try:
            # 1. 전압 변화 그래프
            ax1.plot(data.index, data['battery'], 'b-', linewidth=2)
            ax1.set_title('전압 변화')
            ax1.set_xlabel('시간 (레코드)')
            ax1.set_ylabel('전압 (V)')
            ax1.grid(True, alpha=0.3)
            
            # 2. SOC 변화 그래프
            if self.current_analysis:
                config = self.current_analysis['battery_config']
                soc_values = [self.parser._voltage_to_soc(v, config) for v in data['battery']]
                ax2.plot(data.index, soc_values, 'g-', linewidth=2)
                ax2.set_title('SOC 변화 (추정)')
                ax2.set_xlabel('시간 (레코드)')
                ax2.set_ylabel('SOC (%)')
                ax2.grid(True, alpha=0.3)
            
            # 3. 전압 분포 히스토그램
            ax3.hist(data['battery'], bins=20, alpha=0.7, color='orange', edgecolor='black')
            ax3.set_title('전압 분포')
            ax3.set_xlabel('전압 (V)')
            ax3.set_ylabel('빈도')
            ax3.grid(True, alpha=0.3)
            
            # 4. 건강도 차트
            if self.current_summary:
                health_score = self.current_summary.get('health_score', 0)
                colors = ['red' if health_score < 60 else 'orange' if health_score < 75 else 'green']
                bars = ax4.bar(['건강도'], [health_score], color=colors, alpha=0.7)
                ax4.set_title('배터리 건강도')
                ax4.set_ylabel('점수')
                ax4.set_ylim(0, 100)
                ax4.grid(True, alpha=0.3)
                
                # 점수 표시
                for bar in bars:
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                           f'{height:.0f}/100', ha='center', va='bottom', fontweight='bold')
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"그래프 업데이트 오류: {e}")
    
    def update_detail_table(self):
        """상세 데이터 테이블 업데이트"""
        if self.current_data is None:
            return
        
        data = self.current_data
        
        # 테이블 설정
        self.data_table.setRowCount(len(data))
        self.data_table.setColumnCount(len(data.columns))
        self.data_table.setHorizontalHeaderLabels(data.columns.tolist())
        
        # 데이터 채우기
        for i, row in data.iterrows():
            for j, col in enumerate(data.columns):
                value = str(row[col])
                self.data_table.setItem(i, j, QTableWidgetItem(value))
        
        # 테이블 크기 조정
        self.data_table.resizeColumnsToContents()
    
    def generate_comprehensive_report(self):
        """종합 보고서 생성"""
        if self.current_data is None:
            QMessageBox.warning(self, "경고", "분석할 데이터가 없습니다.")
            return
        
        try:
            # 보고서 생성
            result = self.parser.generate_comprehensive_report(
                df=self.current_data,
                load_watts=self.load_value_spin.value() if self.load_type_combo.currentText() == 'watts' else None,
                load_amps=self.load_value_spin.value() if self.load_type_combo.currentText() == 'amps' else None,
                battery_capacity_ah=self.capacity_spin.value(),
                battery_type=self.battery_type_combo.currentText()
            )
            
            if result and 'report_text' in result:
                self.report_text.setText(result['report_text'])
            else:
                QMessageBox.warning(self, "경고", "보고서 생성에 실패했습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"보고서 생성 중 오류: {str(e)}")
    
    def save_graphs(self):
        """그래프 저장"""
        if self.current_data is None:
            QMessageBox.warning(self, "경고", "저장할 그래프가 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "그래프 저장", f"battery_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG 파일 (*.png);;PDF 파일 (*.pdf);;SVG 파일 (*.svg)"
        )
        
        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "완료", f"그래프가 저장되었습니다:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"그래프 저장 실패: {str(e)}")
    
    def save_report(self):
        """보고서 저장"""
        report_text = self.report_text.toPlainText()
        
        if not report_text.strip():
            QMessageBox.warning(self, "경고", "저장할 보고서가 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "보고서 저장", f"battery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "텍스트 파일 (*.txt);;모든 파일 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                QMessageBox.information(self, "완료", f"보고서가 저장되었습니다:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"보고서 저장 실패: {str(e)}")

    def show_help_dialog(self):
        """전체 도움말 다이얼로그 표시"""
        dialog = HelpDialog(self)
        dialog.exec_()
    
    def show_load_help(self):
        """부하 설정 도움말 표시"""
        QMessageBox.information(self, "부하 설정 도움말", 
            "🔌 부하 타입 선택:\n\n"
            "• Watts (와트): 일정 전력 부하\n"
            "  - 전압이 떨어져도 전력은 일정\n"
            "  - 전압 ↓ → 전류 ↑\n"
            "  - 예: LED, 히터, 전력 변환기\n\n"
            "• Amps (암페어): 일정 전류 부하\n"
            "  - 전압이 떨어져도 전류는 일정\n"
            "  - 전압 ↓ → 전력 ↓\n"
            "  - 예: 저항, 직류 모터\n\n"
            "📝 예시:\n"
            "50W 부하: 25V→2A, 20V→2.5A\n"
            "2A 부하: 25V→50W, 20V→40W")
    
    def show_battery_help(self):
        """배터리 설정 도움말 표시"""
        QMessageBox.information(self, "배터리 설정 도움말",
            "🔋 배터리 타입:\n\n"
            "• 6s: 6셀 직렬 (18V~25.2V)\n"
            "  - 명목 전압: 22.2V\n"
            "  - OnBoard 시스템 표준\n\n"
            "• 3s: 3셀 직렬 (9V~12.6V)\n"
            "  - 명목 전압: 11.1V\n\n"
            "• single: 단일 셀 (3V~4.2V)\n"
            "  - 명목 전압: 3.7V\n\n"
            "⚡ 배터리 용량 (Ah):\n"
            "1시간 동안 공급할 수 있는\n"
            "전류량을 나타냅니다.\n\n"
            "예: 2.5Ah → 2.5A로 1시간 사용 가능")

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 설정
    app.setApplicationName("배터리 로그 분석기")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("STM32L412 OnBoard")
    
    # 메인 윈도우 생성 및 표시
    window = BatteryAnalyzerGUI()
    window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 