import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QFileDialog, QLabel, QTextEdit, 
                             QTableWidget, QTableWidgetItem, QTabWidget, QGridLayout,
                             QGroupBox, QProgressBar, QMessageBox, QSplitter, QComboBox,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QSlider, QFrame,
                             QScrollArea, QToolTip)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon, QCursor
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from matplotlib.widgets import SpanSelector
import seaborn as sns
from battery_log_parser import BatteryLogParser
from battery_analytics import BatteryAnalytics

# 한글 폰트 설정
import matplotlib.font_manager as fm
import platform

def setup_korean_font():
    """한글 폰트 설정"""
    system = platform.system()
    
    if system == 'Windows':
        # Windows 시스템 폰트
        font_candidates = [
            'Malgun Gothic',  # 맑은 고딕
            'Microsoft JhengHei',  # 미소
            'NanumGothic',  # 나눔고딕
            'Arial Unicode MS',
            'DejaVu Sans'
        ]
    else:
        # Linux/Mac 폰트
        font_candidates = [
            'NanumGothic',
            'Apple SD Gothic Neo',
            'DejaVu Sans',
            'Liberation Sans'
        ]
    
    # 사용 가능한 폰트 찾기
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    korean_font = None
    
    for font in font_candidates:
        if font in available_fonts:
            korean_font = font
            break
    
    if korean_font:
        plt.rcParams['font.family'] = korean_font
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 문제 해결
        print(f"한글 폰트 설정: {korean_font}")
    else:
        # 기본 설정 - 마이너스 기호 문제 해결
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        print("한글 폰트를 찾을 수 없어 기본 폰트(DejaVu Sans)를 사용합니다.")
    
    # 추가 폰트 설정
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 9
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    
    return korean_font

class HelpButton(QPushButton):
    """도움말 버튼 클래스"""
    
    def __init__(self, help_text, parent=None):
        super().__init__("❓", parent)
        self.help_text = help_text
        self.setFixedSize(20, 20)
        self.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                border: 1px solid #2196f3;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                color: #1976d2;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
        """)
        self.clicked.connect(self.show_help)
    
    def show_help(self):
        """도움말 다이얼로그 표시"""
        QMessageBox.information(self, "계산 원리", self.help_text)

class BatteryLogAnalyzer(QMainWindow):
    """배터리 로그 분석 메인 UI"""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.filtered_data = None  # 필터링된 데이터
        self.analytics = BatteryAnalytics()
        self.parser = BatteryLogParser()
        
        # 파일 경로 관련 속성 초기화
        self.file_path = None  # 단일 파일 경로 (기존 호환성)
        
        # 다중 파일 처리를 위한 새로운 속성들
        self.multiple_data = {}  # 파일별 데이터 저장
        self.file_paths = []     # 선택된 파일 경로들
        self.selected_files = [] # UI에서 선택된 파일들
        self.comparison_mode = False  # 비교 모드 플래그
        
        # 분석 결과 저장
        self.analysis_results = {}
        self.current_selection = None
        
        # 드래그 관련 변수
        self.is_dragging = False
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_xlim = None
        self.original_ylim = None
        
        # 마우스 가운데 버튼 드래그
        self.middle_button_pressed = False
        self.last_mouse_pos = None
        
        # 커서 십자선 및 정보 표시
        self.crosshair_lines = None
        self.cursor_info_text = None
        
        # 시간 범위 선택을 위한 SpanSelector
        self.span_selector = None
        
        # 한글 폰트 설정
        self.korean_font = setup_korean_font()
        
        # OnBoard 로그 분석 항목별 도움말 텍스트
        self.help_texts = self.get_onboard_help_texts()
        
        self.init_ui()
        self.setup_matplotlib_style()
        
    def get_onboard_help_texts(self):
        """OnBoard 로그 분석 항목별 도움말 텍스트"""
        return {
            '평균 전압': """평균 전압 계산:
수식: Σ(전압값) / 데이터 개수
의미: 측정 기간 동안의 평균 배터리 전압
OnBoard 시스템: 18V~25.2V 범위가 정상""",
            
            '전압 안정성': """전압 안정성 계산:
수식: 변동계수 = (표준편차 / 평균) × 100
- CV < 2%: 매우 안정
- CV < 5%: 안정  
- CV > 5%: 불안정
의미: 전압 변동의 일관성 측정""",
            
            '배터리 타입 추정': """배터리 타입 추정:
전압 범위 기반 판단:
- 20V~26V: 리튬이온 6S (OnBoard)
- 11V~13V: 리튬이온 3S 또는 납산
- 3.0V~4.2V: 리튬이온 1S
의미: 평균 전압으로 배터리 구성 추정""",
            
            '건강도 점수': """건강도 점수 계산:
OnBoard 기준:
- 24.5V 이상: 100점 (우수)
- 23.0V 이상: 85점 (양호)
- 22.0V 이상: 70점 (보통)
- 21.0V 이상: 55점 (주의)
- 20.0V 이상: 40점 (교체 고려)
의미: 현재 전압 상태 기반 건강도""",
            
            '방전률': """방전률 계산:
수식: (시작전압 - 종료전압) / 경과시간
단위: V/시간
의미: 시간당 전압 감소량
음수: 충전 중, 양수: 방전 중""",
            
            '이상치 감지': """이상치 감지 (IQR 방법):
1. Q1 = 25% 백분위수
2. Q3 = 75% 백분위수  
3. IQR = Q3 - Q1
4. 이상치 = Q1-1.5×IQR 미만 또는 Q3+1.5×IQR 초과
의미: 정상 범위를 벗어난 측정값""",
            
            '전압 변화율': """전압 변화율 계산:
수식: ((현재값 - 이전값) / 이전값) × 100
단위: %
의미: 연속된 측정값 간의 변화 비율
급격한 변화는 시스템 이상 신호""",
            
            '측정 간격': """측정 간격 계산:
수식: 총 측정시간 / (데이터 개수 - 1)
OnBoard 로그: 일반적으로 1초 간격
의미: 데이터 수집 주기의 일관성""",
            
            'STANDBY 비율': """STANDBY 상태 분석:
수식: STANDBY 데이터 개수 / 전체 데이터 개수 × 100
의미: 시스템이 대기 상태인 시간 비율
높은 비율: 안정적 운영""",
            
            'LED 상태 분석': """LED 상태 분석:
L1, L2 상태 조합 분석:
- X,X: 정상 대기
- 기타 조합: 특정 상태 표시
변화율: 상태 변경 빈도 측정""",
            
            '메모 값 분석': """메모 값 분석:
숫자 메모 값의 통계 분석:
- 평균, 표준편차, 범위
- 트렌드 분석 (선형 회귀)
- 배터리 전압과의 상관관계
의미: 시스템 내부 파라미터 모니터링""",
            
            '주기성 분석': """주기성 분석 (FFT):
1. 데이터 리샘플링 (등간격)
2. 고속 푸리에 변환 적용
3. 주파수 스펙트럼 분석
4. 주요 주기 성분 검출
의미: 반복적 패턴의 주기 탐지""",
            
            '트렌드 분석': """트렌드 분석 (선형 회귀):
수식: y = ax + b (최소자승법)
- a > 0: 상승 트렌드 (충전)
- a < 0: 하락 트렌드 (방전)  
- a ≈ 0: 안정 상태
R² 값: 트렌드의 신뢰도 (0~1)""",
            
            '시간대별 분석': """시간대별 분석:
24시간을 기준으로 시간대별 전압 패턴:
- 각 시간대별 평균, 표준편차
- 최고/최저 전압 시간대
- 일일 변동 패턴 분석
의미: 사용 패턴 및 충전 스케줄 파악"""
        }

    def create_labeled_widget_with_help(self, label_text, widget, help_key):
        """라벨과 위젯, 도움말 버튼을 포함한 레이아웃 생성"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 라벨
        label = QLabel(label_text)
        layout.addWidget(label)
        
        # 도움말 버튼
        if help_key in self.help_texts:
            help_btn = HelpButton(self.help_texts[help_key])
            layout.addWidget(help_btn)
        
        layout.addStretch()
        
        # 위젯
        layout.addWidget(widget)
        
        return container, widget

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(' 배터리 로그 분석기 v2.0 - 진단 & 성능 평가')
        self.setGeometry(100, 100, 1600, 1000)
        
        # 메인 위젯 및 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 툴바 생성
        self.create_toolbar(main_layout)
        
        # 메인 컨텐츠 영역 (Splitter로 나누기)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 왼쪽 패널 (컨트롤 및 정보)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 오른쪽 패널 (그래프 및 분석)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정
        splitter.setSizes([350, 1250])
        
        # 상태바
        self.statusBar().showMessage('파일을 선택하여  분석을 시작하세요.')
        
    def create_toolbar(self, layout):
        """툴바 생성"""
        toolbar_layout = QHBoxLayout()
        
        # 파일 선택 버튼들
        file_buttons_layout = QHBoxLayout()
        
        # 단일 파일 선택 버튼
        self.file_btn = QPushButton('📁 단일 파일 선택')
        self.file_btn.clicked.connect(self.select_single_file)
        self.file_btn.setMinimumHeight(40)
        file_buttons_layout.addWidget(self.file_btn)
        
        # 다중 파일 선택 버튼
        self.multi_file_btn = QPushButton('📂 다중 파일 선택')
        self.multi_file_btn.clicked.connect(self.select_multiple_files)
        self.multi_file_btn.setMinimumHeight(40)
        file_buttons_layout.addWidget(self.multi_file_btn)
        
        toolbar_layout.addLayout(file_buttons_layout)
        
        # 파일 정보 라벨
        self.file_info_label = QLabel('선택된 파일: 없음')
        toolbar_layout.addWidget(self.file_info_label)
        
        toolbar_layout.addStretch()
        
        # 비교 모드 체크박스
        self.comparison_mode_check = QCheckBox('비교 모드')
        self.comparison_mode_check.toggled.connect(self.toggle_comparison_mode)
        self.comparison_mode_check.setToolTip('여러 파일의 데이터를 하나의 그래프에서 비교')
        toolbar_layout.addWidget(self.comparison_mode_check)
        
        # 분석 시작 버튼
        self.analyze_btn = QPushButton('🔍 분석 시작')
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setMinimumHeight(40)
        toolbar_layout.addWidget(self.analyze_btn)
        
        # 보고서 저장 버튼
        self.save_btn = QPushButton('💾 보고서 저장')
        self.save_btn.clicked.connect(self.save_report)
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(40)
        toolbar_layout.addWidget(self.save_btn)
        
        layout.addLayout(toolbar_layout)
        
    def create_left_panel(self):
        """왼쪽 컨트롤 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 파일 선택 상태 그룹
        file_group = QGroupBox('선택된 파일')
        file_layout = QVBoxLayout(file_group)
        
        # 파일 목록 위젯
        self.file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(self.file_list_widget)
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.file_list_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(150)
        file_layout.addWidget(scroll_area)
        
        layout.addWidget(file_group)
        
        # 데이터 정보 그룹
        info_group = QGroupBox('데이터 정보')
        info_layout = QVBoxLayout(info_group)
        
        self.data_info_text = QTextEdit()
        self.data_info_text.setMaximumHeight(150)
        self.data_info_text.setReadOnly(True)
        info_layout.addWidget(self.data_info_text)
        
        layout.addWidget(info_group)
        
        # 필터링 옵션
        filter_group = QGroupBox('필터링 옵션')
        filter_layout = QGridLayout(filter_group)
        
        filter_layout.addWidget(QLabel('시간 범위:'), 0, 0)
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(['전체', '최근 1시간', '최근 6시간', '최근 24시간', '사용자 정의'])
        filter_layout.addWidget(self.time_range_combo, 0, 1)
        
        filter_layout.addWidget(QLabel('배터리 범위 (V):'), 1, 0)
        battery_layout = QHBoxLayout()
        self.battery_min_spin = QDoubleSpinBox()
        self.battery_min_spin.setRange(0, 50)  # OnBoard 모니터 범위 확대
        self.battery_min_spin.setValue(0)
        self.battery_min_spin.setSingleStep(0.1)
        battery_layout.addWidget(self.battery_min_spin)
        
        battery_layout.addWidget(QLabel(' ~ '))
        
        self.battery_max_spin = QDoubleSpinBox()
        self.battery_max_spin.setRange(0, 50)  # OnBoard 모니터 범위 확대
        self.battery_max_spin.setValue(30)    # OnBoard 기본 최대값
        self.battery_max_spin.setSingleStep(0.1)
        battery_layout.addWidget(self.battery_max_spin)
        
        filter_layout.addLayout(battery_layout, 1, 1)
        
        # 필터 적용 버튼 (강조 표시)
        filter_btn = QPushButton('🔄 필터 적용')
        filter_btn.clicked.connect(self.apply_filters)
        filter_btn.setShortcut('Ctrl+F')  # 단축키 추가
        filter_btn.setToolTip('필터 조건을 적용합니다 (Ctrl+F)')
        filter_btn.setStyleSheet("""
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
        """)
        filter_layout.addWidget(filter_btn, 2, 0, 1, 2)
        
        layout.addWidget(filter_group)
        
        # 분석 옵션 (즉시 적용)
        analysis_group = QGroupBox('분석 옵션')
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.show_statistics = QCheckBox('통계 정보 표시')
        self.show_statistics.setChecked(True)
        self.show_statistics.toggled.connect(self.on_analysis_option_changed)
        analysis_layout.addWidget(self.show_statistics)
        
        self.show_anomalies = QCheckBox('이상치 감지')
        self.show_anomalies.setChecked(True)
        self.show_anomalies.toggled.connect(self.on_analysis_option_changed)
        analysis_layout.addWidget(self.show_anomalies)
        
        self.show_trends = QCheckBox('트렌드 라인')
        self.show_trends.setChecked(False)
        self.show_trends.toggled.connect(self.on_analysis_option_changed)
        analysis_layout.addWidget(self.show_trends)
        
        layout.addWidget(analysis_group)
        
        # 선택 구간 분석
        selection_group = QGroupBox('선택 구간 분석')
        selection_layout = QVBoxLayout(selection_group)
        
        self.selection_info = QTextEdit()
        self.selection_info.setMaximumHeight(200)
        self.selection_info.setReadOnly(True)
        selection_layout.addWidget(self.selection_info)
        
        # 선택 구간 초기화 버튼
        clear_selection_btn = QPushButton('선택 구간 초기화')
        clear_selection_btn.clicked.connect(self.clear_selection)
        selection_layout.addWidget(clear_selection_btn)
        
        layout.addWidget(selection_group)
        
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self):
        """오른쪽 그래프 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 메인 그래프 탭
        self.main_graph_tab = self.create_main_graph_tab()
        self.tab_widget.addTab(self.main_graph_tab, '📊 메인 그래프')
        
        # 상세 분석 탭
        self.detail_analysis_tab = self.create_detail_analysis_tab()
        self.tab_widget.addTab(self.detail_analysis_tab, '🔍 상세 분석')
        
        # 통계 탭
        self.statistics_tab = self.create_statistics_tab()
        self.tab_widget.addTab(self.statistics_tab, '📈 통계 정보')
        
        # 새로운 배터리 진단 탭
        self.diagnostic_tab = self.create_diagnostic_tab()
        self.tab_widget.addTab(self.diagnostic_tab, '🔋 배터리 진단')
        
        # 성능 평가 탭
        self.performance_tab = self.create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, '⚡ 성능 평가')
        
        return panel
    
    def create_main_graph_tab(self):
        """메인 그래프 탭 생성 (도움말 포함)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 그래프 컨트롤
        control_layout = QHBoxLayout()
        
        # 그래프 타입 선택
        self.graph_type_combo = QComboBox()
        graph_type_container, self.graph_type_combo = self.create_labeled_widget_with_help(
            '그래프 타입:', 
            self.graph_type_combo, 
            '트렌드 분석'
        )
        self.graph_type_combo.addItems(['시계열', '히스토그램', '박스플롯', '산점도'])
        self.graph_type_combo.currentTextChanged.connect(self.on_graph_option_changed)
        control_layout.addWidget(graph_type_container)
        
        # 시간 표시 옵션
        self.time_display_combo = QComboBox()
        time_display_container, self.time_display_combo = self.create_labeled_widget_with_help(
            '시간 표시:', 
            self.time_display_combo, 
            '측정 간격'
        )
        self.time_display_combo.addItems(['절대시간', '상대시간(시작점 기준)', '경과시간(분)', '경과시간(시간)'])
        self.time_display_combo.currentTextChanged.connect(self.on_graph_option_changed)
        control_layout.addWidget(time_display_container)
        
        # 그리드 옵션
        self.show_grid_check = QCheckBox('격자 표시')
        self.show_grid_check.setChecked(True)
        self.show_grid_check.toggled.connect(self.update_grid_settings_only)
        control_layout.addWidget(self.show_grid_check)
        
        self.show_minor_grid_check = QCheckBox('세부 격자')
        self.show_minor_grid_check.setChecked(False)
        self.show_minor_grid_check.toggled.connect(self.update_grid_settings_only)
        control_layout.addWidget(self.show_minor_grid_check)
        
        # 커서 정보 표시 옵션
        self.show_cursor_info_check = QCheckBox('커서 정보 표시')
        self.show_cursor_info_check.setChecked(True)
        self.show_cursor_info_check.toggled.connect(self.on_graph_option_changed)
        control_layout.addWidget(self.show_cursor_info_check)
        
        control_layout.addStretch()
        
        # 드래그 모드 선택
        control_layout.addWidget(QLabel('마우스 모드:'))
        self.mouse_mode_combo = QComboBox()
        self.mouse_mode_combo.addItems(['선택', '드래그 이동', '구간 선택'])
        self.mouse_mode_combo.currentTextChanged.connect(self.change_mouse_mode)
        control_layout.addWidget(self.mouse_mode_combo)
        
        # 확대/축소 버튼
        zoom_in_btn = QPushButton('🔍+')
        zoom_in_btn.clicked.connect(self.zoom_in)
        control_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton('🔍-')
        zoom_out_btn.clicked.connect(self.zoom_out)
        control_layout.addWidget(zoom_out_btn)
        
        reset_zoom_btn = QPushButton('🔄')
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        control_layout.addWidget(reset_zoom_btn)
        
        layout.addLayout(control_layout)
        
        # OnBoard 그래프 도움말
        graph_help_layout = QHBoxLayout()
        graph_help_layout.addWidget(QLabel('<b>OnBoard 배터리 전압 그래프</b>'))
        main_graph_help_btn = HelpButton("""OnBoard 배터리 전압 그래프:

• 시계열: 시간에 따른 전압 변화 (18V~26V 범위)
• 히스토그램: 전압 분포 패턴
• 박스플롯: 시간대별 전압 분포
• 산점도: 시간-전압 상관관계

OnBoard 시스템 특징:
- 정상 범위: 18V~25.2V (6S 리튬이온)
- 완전 충전: 25.2V
- 정상 운영: 20V~24V
- 주의 필요: 18V 이하

이상치는 빨간 X로 표시됩니다.""")
        graph_help_layout.addWidget(main_graph_help_btn)
        graph_help_layout.addStretch()
        layout.addLayout(graph_help_layout)
        
        # 메인 그래프
        self.main_figure = Figure(figsize=(12, 8))
        self.main_canvas = FigureCanvas(self.main_figure)
        
        # 마우스 이벤트 연결
        self.main_canvas.mpl_connect('button_press_event', self.on_canvas_press)
        self.main_canvas.mpl_connect('button_release_event', self.on_canvas_release)
        self.main_canvas.mpl_connect('motion_notify_event', self.on_canvas_motion)
        self.main_canvas.mpl_connect('scroll_event', self.on_canvas_scroll)
        
        layout.addWidget(self.main_canvas)
        
        return widget
    
    def update_grid_settings_only(self):
        """격자 설정만 업데이트 (전체 그래프 다시 그리지 않음)"""
        try:
            # 현재 표시된 모든 축에 대해 격자 설정 적용
            for ax in self.main_figure.get_axes():
                self.apply_grid_settings(ax)
            
            # 캔버스만 새로고침 (빠른 업데이트)
            self.main_canvas.draw_idle()
        except Exception as e:
            print(f"격자 설정 업데이트 오류: {e}")
            # 오류 발생 시에만 전체 그래프 업데이트
            self.update_main_graph()
    
    def on_analysis_option_changed(self):
        """분석 옵션 변경 시 즉시 적용 (최적화 및 응답성 개선)"""
        if not hasattr(self, '_update_timer'):
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._delayed_update_graphs)
        
        # 기존 타이머 정지 (중복 업데이트 방지)
        self._update_timer.stop()
        
        # 데이터 유효성 검사
        if self.data is None and not self.multiple_data:
            return
        
        try:
            # 즉시 적용 가능한 변경사항 (격자 등)
            self._apply_immediate_changes()
            
            # 무거운 작업은 지연 실행 (50ms 후)
            self._update_timer.start(50)
            
        except Exception as e:
            print(f"분석 옵션 변경 오류: {e}")
            # 오류 시 상태바에 메시지 표시
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'옵션 변경 오류: {str(e)}', 3000)
    
    def _apply_immediate_changes(self):
        """즉시 적용 가능한 UI 변경사항"""
        try:
            # 격자 설정만 즉시 적용 (빠른 업데이트)
            if hasattr(self, 'main_figure') and self.main_figure.get_axes():
                for ax in self.main_figure.get_axes():
                    self.apply_grid_settings(ax)
                
                # 캔버스 빠른 새로고침
                if hasattr(self, 'main_canvas'):
                    self.main_canvas.draw_idle()
        except Exception as e:
            print(f"즉시 변경사항 적용 오류: {e}")
    
    def _delayed_update_graphs(self):
        """지연된 그래프 업데이트 (무거운 작업)"""
        try:
            # 현재 상태 확인
            if self.data is None and not self.multiple_data:
                return
            
            # 비교 모드와 단일 모드 구분하여 업데이트
            if self.comparison_mode and self.multiple_data:
                # 비교 모드: 메인 그래프만 업데이트 (성능 최적화)
                self._update_comparison_main_only()
            else:
                # 단일 모드: 메인 그래프만 업데이트
                self._update_single_main_only()
            
            # 상태바 업데이트
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage('분석 옵션이 적용되었습니다.', 2000)
                
        except Exception as e:
            print(f"지연 그래프 업데이트 오류: {e}")
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'그래프 업데이트 실패: {str(e)}', 3000)
    
    def _update_comparison_main_only(self):
        """비교 모드에서 메인 그래프만 업데이트 (최적화)"""
        try:
            self.main_figure.clear()
            self.create_comparison_time_series()
            if hasattr(self, 'main_canvas'):
                self.main_canvas.draw_idle()
        except Exception as e:
            print(f"비교 모드 메인 그래프 업데이트 오류: {e}")
    
    def _update_single_main_only(self):
        """단일 모드에서 메인 그래프만 업데이트 (최적화)"""
        try:
            self.main_figure.clear()
            
            # 현재 그래프 타입에 따라 분기
            graph_type = self.graph_type_combo.currentText()
            
            if graph_type == '시계열':
                self.plot_time_series()
            elif graph_type == '히스토그램':
                self.plot_histogram()
            elif graph_type == '박스플롯':
                self.plot_boxplot()
            elif graph_type == '산점도':
                self.plot_scatter()
            
            if hasattr(self, 'main_canvas'):
                self.main_canvas.draw_idle()
                
        except Exception as e:
            print(f"단일 모드 메인 그래프 업데이트 오류: {e}")
    
    def create_detail_analysis_tab(self):
        """상세 분석 탭 생성 (OnBoard 특화, 도움말 포함)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 제목과 도움말
        detail_title_layout = QHBoxLayout()
        detail_title_layout.addWidget(QLabel('<b>OnBoard 시스템 상세 분석</b>'))
        detail_help_btn = HelpButton("""OnBoard 상세 분석:

1. 이동평균 분석: 전압 트렌드의 부드러운 변화
2. 변화율 분석: 연속 측정값 간의 변화 비율
3. 이상치 분석: IQR 방법으로 비정상 값 탐지
4. 주기성 분석: FFT로 반복 패턴 탐지

OnBoard 적용:
- 충전/방전 사이클 패턴
- 시스템 상태 변화 감지
- 전원 공급 안정성 평가
- 배터리 성능 저하 조기 발견""")
        detail_title_layout.addWidget(detail_help_btn)
        detail_title_layout.addStretch()
        layout.addLayout(detail_title_layout)
        
        # 상세 분석 그래프
        self.detail_figure = Figure(figsize=(12, 10))
        self.detail_canvas = FigureCanvas(self.detail_figure)
        layout.addWidget(self.detail_canvas)
        
        return widget
    
    def create_statistics_tab(self):
        """통계 정보 탭 생성 (OnBoard 특화, 도움말 포함)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 제목과 도움말
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel('<b>OnBoard 로그 통계 분석</b>'))
        stats_help_btn = HelpButton("""OnBoard 로그 통계 분석:

포맷: 13:49:50    25.22V    00:00    STANDBY    X    X    3725

분석 가능한 항목:
• 전압 통계 (평균, 표준편차, 범위)
• 시간 분석 (측정 간격, 총 기간)
• 상태 분포 (STANDBY 비율)
• LED 상태 분석 (L1, L2 조합)
• 메모 파라미터 통계
• 백분위수 분석 (Q1, Q3, 이상치)

각 항목은 OnBoard 시스템 특성에 맞게 해석됩니다.""")
        title_layout.addWidget(stats_help_btn)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 통계 테이블
        self.stats_table = QTableWidget()
        layout.addWidget(self.stats_table)
        
        return widget
    
    def create_diagnostic_tab(self):
        """배터리 진단 탭 생성 (OnBoard 특화, 도움말 포함)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 진단 정보를 여러 섹션으로 나눔
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # OnBoard 전용 종합 진단 그룹
        self.diagnostic_group = QGroupBox('🔬 OnBoard 시스템 종합 진단')
        diagnostic_layout = QVBoxLayout(self.diagnostic_group)
        
        # 제목과 도움말
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel('<b>OnBoard 배터리 시스템 진단 결과</b>'))
        help_btn = HelpButton("""OnBoard 시스템 종합 진단:
13:49:50    25.22V    00:00    STANDBY    X    X    3725 포맷 기반

분석 항목:
• 전압 레벨 (20V~26V 범위)
• 시스템 상태 (STANDBY 등)
• LED 상태 (L1, L2)
• 메모 파라미터 분석
• 시간별 패턴 분석""")
        title_layout.addWidget(help_btn)
        title_layout.addStretch()
        diagnostic_layout.addLayout(title_layout)
        
        self.diagnostic_text = QTextEdit()
        self.diagnostic_text.setMaximumHeight(200)
        self.diagnostic_text.setReadOnly(True)
        diagnostic_layout.addWidget(self.diagnostic_text)
        scroll_layout.addWidget(self.diagnostic_group)
        
        # OnBoard 전압 분석 그룹
        self.voltage_group = QGroupBox('⚡ 전압 상태 분석')
        voltage_layout = QVBoxLayout(self.voltage_group)
        
        voltage_title_layout = QHBoxLayout()
        voltage_title_layout.addWidget(QLabel('<b>OnBoard 전압 범위 분석 (20V~26V)</b>'))
        voltage_help_btn = HelpButton(self.help_texts['평균 전압'] + "\n\n" + self.help_texts['전압 안정성'])
        voltage_title_layout.addWidget(voltage_help_btn)
        voltage_title_layout.addStretch()
        voltage_layout.addLayout(voltage_title_layout)
        
        self.voltage_text = QTextEdit()
        self.voltage_text.setMaximumHeight(150)
        self.voltage_text.setReadOnly(True)
        voltage_layout.addWidget(self.voltage_text)
        scroll_layout.addWidget(self.voltage_group)
        
        # OnBoard 상태 분석 그룹
        self.status_group = QGroupBox('📊 시스템 상태 분석')
        status_layout = QVBoxLayout(self.status_group)
        
        status_title_layout = QHBoxLayout()
        status_title_layout.addWidget(QLabel('<b>STANDBY, LED, 메모 상태 분석</b>'))
        status_help_btn = HelpButton(self.help_texts['STANDBY 비율'] + "\n\n" + self.help_texts['LED 상태 분석'])
        status_title_layout.addWidget(status_help_btn)
        status_title_layout.addStretch()
        status_layout.addLayout(status_title_layout)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        scroll_layout.addWidget(self.status_group)
        
        # OnBoard 건강도 평가 그룹
        self.health_group = QGroupBox('🏥 OnBoard 건강도 평가')
        health_layout = QVBoxLayout(self.health_group)
        
        health_title_layout = QHBoxLayout()
        health_title_layout.addWidget(QLabel('<b>20V~26V 기준 건강도 점수</b>'))
        health_help_btn = HelpButton(self.help_texts['건강도 점수'])
        health_title_layout.addWidget(health_help_btn)
        health_title_layout.addStretch()
        health_layout.addLayout(health_title_layout)
        
        self.health_text = QTextEdit()
        self.health_text.setMaximumHeight(150)
        self.health_text.setReadOnly(True)
        health_layout.addWidget(self.health_text)
        scroll_layout.addWidget(self.health_group)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_performance_tab(self):
        """성능 평가 탭 생성 (OnBoard 특화, 도움말 포함)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 성능 지표 그래프
        graph_layout = QVBoxLayout()
        
        # 그래프 제목과 도움말
        graph_title_layout = QHBoxLayout()
        graph_title_layout.addWidget(QLabel('<b>OnBoard 시스템 성능 지표</b>'))
        graph_help_btn = HelpButton("""OnBoard 성능 지표 그래프:

1. 전압 안정성: 롤링 표준편차
2. 전압 트렌드: 이동평균 + 선형 회귀
3. 시스템 효율성: 변동성 기반 점수
4. 건강도 게이지: 20V~26V 기준 점수

각 그래프는 OnBoard 시스템 특성에 최적화됨""")
        graph_title_layout.addWidget(graph_help_btn)
        graph_title_layout.addStretch()
        graph_layout.addLayout(graph_title_layout)
        
        self.performance_figure = Figure(figsize=(12, 8))
        self.performance_canvas = FigureCanvas(self.performance_figure)
        graph_layout.addWidget(self.performance_canvas)
        
        layout.addLayout(graph_layout)
        
        # OnBoard 효율성 정보
        self.efficiency_group = QGroupBox('⚡ OnBoard 시스템 효율성')
        efficiency_layout = QVBoxLayout(self.efficiency_group)
        
        efficiency_title_layout = QHBoxLayout()
        efficiency_title_layout.addWidget(QLabel('<b>전압 안정성 기반 효율성 지표</b>'))
        efficiency_help_btn = HelpButton("""효율성 계산:

전압 효율성 = (1 - 표준편차/평균) × 100
안정성 효율성 = (1 - 전압범위/평균) × 100
시스템 효율성 = (전압효율성 + 안정성효율성) / 2

OnBoard 기준:
• 90% 이상: 우수
• 80% 이상: 양호  
• 70% 이상: 보통
• 70% 미만: 개선 필요""")
        efficiency_title_layout.addWidget(efficiency_help_btn)
        efficiency_title_layout.addStretch()
        efficiency_layout.addLayout(efficiency_title_layout)
        
        self.efficiency_text = QTextEdit()
        self.efficiency_text.setMaximumHeight(120)
        self.efficiency_text.setReadOnly(True)
        efficiency_layout.addWidget(self.efficiency_text)
        layout.addWidget(self.efficiency_group)
        
        return widget
    
    def setup_matplotlib_style(self):
        """Matplotlib 스타일 설정 (마이너스 기호 문제 완전 해결)"""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 한글 폰트 재설정
        if self.korean_font:
            plt.rcParams['font.family'] = self.korean_font
        else:
            plt.rcParams['font.family'] = 'DejaVu Sans'
        
        # 마이너스 기호 문제 완전 해결
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'DejaVu Sans', 'Arial Unicode MS']
        
        # DPI 및 품질 설정
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 300
        
        # 추가 폰트 크기 설정
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 9
        plt.rcParams['xtick.labelsize'] = 9
        plt.rcParams['ytick.labelsize'] = 9
        plt.rcParams['figure.titlesize'] = 12
        
        # 그리드 및 스타일
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['axes.spines.top'] = False
        plt.rcParams['axes.spines.right'] = False
        
        print("Matplotlib 스타일 설정 완료")
    
    def select_file(self):
        """파일 선택 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '배터리 로그 파일 선택',
            '',
            'Log files (*.log *.txt *.csv);;All files (*.*)'
        )
        
        if file_path:
            self.file_path = file_path
            self.file_info_label.setText(f'선택된 파일: {os.path.basename(file_path)}')
            self.analyze_btn.setEnabled(True)
            self.statusBar().showMessage(f'파일 선택됨: {os.path.basename(file_path)}')
    
    def start_analysis(self):
        """분석 시작 - 단일/다중 파일 지원"""
        try:
            if self.comparison_mode and len(self.selected_files) > 1:
                # 다중 파일 비교 분석
                self.start_multiple_file_analysis()
            else:
                # 단일 파일 분석
                self.start_single_file_analysis()
                
        except Exception as e:
            QMessageBox.critical(self, '오류', f'분석 중 오류가 발생했습니다:\n{str(e)}')
            self.statusBar().showMessage('분석 실패')
    
    def start_single_file_analysis(self):
        """단일 파일 분석"""
        if not self.selected_files:
            QMessageBox.warning(self, '오류', '선택된 파일이 없습니다.')
            return
        
        file_path = self.selected_files[0]
        self.file_path = file_path  # file_path 속성 설정
        
        # 그래프 타입 콤보박스 활성화 (단일 모드)
        self.graph_type_combo.setEnabled(True)
        
        # 파일 파싱
        self.statusBar().showMessage('파일을 파싱하는 중...')
        self.data = self.parser.parse_log_file(file_path)
        
        if self.data is None or len(self.data) == 0:
            QMessageBox.warning(self, '오류', '파일을 파싱할 수 없거나 데이터가 없습니다.')
            return
        
        # 배터리 범위 자동 설정
        self.auto_adjust_battery_range()
        
        # 분석 수행
        self.statusBar().showMessage('데이터를 분석하는 중...')
        self.analysis_results = self.analytics.analyze(self.data)
        
        # UI 업데이트
        self.update_data_info()
        self.update_all_graphs()
        self.update_statistics()
        
        self.save_btn.setEnabled(True)
        self.statusBar().showMessage(f'분석 완료 - {len(self.data)}개 데이터 포인트')
    
    def start_multiple_file_analysis(self):
        """다중 파일 비교 분석"""
        if len(self.selected_files) < 2:
            QMessageBox.warning(self, '오류', '비교 분석을 위해서는 최소 2개 파일이 필요합니다.')
            return
        
        # 다중 데이터 초기화
        self.multiple_data.clear()
        
        # 각 파일 파싱
        total_files = len(self.selected_files)
        failed_files = []
        
        for i, file_path in enumerate(self.selected_files):
            filename = os.path.basename(file_path)
            self.statusBar().showMessage(f'파일 파싱 중... ({i+1}/{total_files}) {filename}')
            
            data = self.parser.parse_log_file(file_path)
            
            if data is not None and len(data) > 0:
                # 파일명을 키로 사용
                self.multiple_data[filename] = {
                    'data': data,
                    'path': file_path,
                    'analysis': None
                }
            else:
                failed_files.append(filename)
        
        # 파싱 실패한 파일 알림
        if failed_files:
            failed_list = '\n'.join(failed_files)
            QMessageBox.warning(self, '파싱 실패', f'다음 파일들을 파싱할 수 없습니다:\n{failed_list}')
        
        # 성공적으로 파싱된 파일이 없는 경우
        if not self.multiple_data:
            QMessageBox.warning(self, '오류', '파싱 가능한 파일이 없습니다.')
            return
        
        # 각 파일 개별 분석
        for filename, file_info in self.multiple_data.items():
            self.statusBar().showMessage(f'분석 중... {filename}')
            file_info['analysis'] = self.analytics.analyze(file_info['data'])
        
        # 첫 번째 파일을 기본 데이터로 설정 (UI 호환성)
        first_filename = list(self.multiple_data.keys())[0]
        self.data = self.multiple_data[first_filename]['data']
        self.analysis_results = self.multiple_data[first_filename]['analysis']
        
        # 배터리 범위 자동 설정 (모든 파일 고려)
        self.auto_adjust_battery_range_multiple()
        
        # UI 업데이트 (비교 모드)
        self.update_data_info_multiple()
        self.update_all_graphs_comparison()
        self.update_statistics_comparison()
        
        self.save_btn.setEnabled(True)
        
        successful_count = len(self.multiple_data)
        total_points = sum(len(info['data']) for info in self.multiple_data.values())
        self.statusBar().showMessage(f'비교 분석 완료 - {successful_count}개 파일, {total_points:,}개 데이터 포인트')
    
    def auto_adjust_battery_range_multiple(self):
        """다중 파일의 데이터에 따른 배터리 범위 자동 조정"""
        if not self.multiple_data:
            return
        
        all_min_voltages = []
        all_max_voltages = []
        
        for file_info in self.multiple_data.values():
            data = file_info['data']
            if 'battery' in data.columns:
                all_min_voltages.append(data['battery'].min())
                all_max_voltages.append(data['battery'].max())
        
        if not all_min_voltages:
            return
        
        global_min = min(all_min_voltages)
        global_max = max(all_max_voltages)
        voltage_range = global_max - global_min
        
        # 여유분을 두고 범위 설정
        range_margin = voltage_range * 0.1  # 10% 여유분
        
        adjusted_min = max(0, global_min - range_margin)
        adjusted_max = global_max + range_margin
        
        # 스핀박스 값 업데이트
        self.battery_min_spin.setValue(adjusted_min)
        self.battery_max_spin.setValue(adjusted_max)
    
    def update_data_info(self):
        """데이터 정보 업데이트"""
        if self.data is None:
            return
        
        # 파일명 처리 - file_path가 None인 경우 대비
        if self.file_path:
            filename = os.path.basename(self.file_path)
        elif self.file_paths:
            filename = os.path.basename(self.file_paths[0])
        else:
            filename = "알 수 없는 파일"
        
        info_text = f"""
파일: {filename}
데이터 포인트: {len(self.data):,}개
시간 범위: {self.data['timestamp'].min()} ~ {self.data['timestamp'].max()}
배터리 전압 범위: {self.data['battery'].min():.2f}V ~ {self.data['battery'].max():.2f}V
평균 배터리 전압: {self.data['battery'].mean():.2f}V
"""
        self.data_info_text.setText(info_text.strip())
    
    def update_all_graphs(self):
        """모든 그래프 업데이트 - 모드별 분기 처리"""
        if self.comparison_mode and self.multiple_data:
            # 비교 모드
            self.update_all_graphs_comparison()
        else:
            # 단일 모드
            self.update_main_graph()
            self.update_detail_analysis()
            self.update_diagnostic_info()
            self.update_performance_analysis()
    
    def update_diagnostic_info(self):
        """OnBoard 로그 특화 진단 정보 업데이트"""
        if self.data is None or not self.analysis_results:
            return
        
        # OnBoard 로그인지 확인
        is_onboard = self.is_onboard_log()
        
        if not is_onboard:
            self.diagnostic_text.setText("OnBoard 로그 포맷이 아닙니다.\n일반 배터리 로그로 처리됩니다.")
            return
        
        # OnBoard 종합 진단
        diagnostic_text = self.generate_onboard_diagnostic_text()
        self.diagnostic_text.setText(diagnostic_text)
        
        # 전압 분석
        voltage_text = self.generate_voltage_analysis_text()
        self.voltage_text.setText(voltage_text)
        
        # 상태 분석  
        status_text = self.generate_status_analysis_text()
        self.status_text.setText(status_text)
        
        # 건강도 분석
        health_text = self.generate_health_analysis_text()
        self.health_text.setText(health_text)
    
    def is_onboard_log(self):
        """OnBoard 로그 포맷인지 확인"""
        if self.data is None:
            return False
        
        # OnBoard 로그의 특징적인 컬럼들 확인
        required_columns = ['timestamp', 'battery', 'timer', 'status', 'L1', 'L2', 'memo']
        has_onboard_columns = all(col in self.data.columns for col in required_columns)
        
        # 전압 범위 확인 (OnBoard는 20V~26V)
        if 'battery' in self.data.columns:
            avg_voltage = self.data['battery'].mean()
            voltage_in_onboard_range = 18.0 <= avg_voltage <= 28.0
        else:
            voltage_in_onboard_range = False
        
        return has_onboard_columns and voltage_in_onboard_range
    
    def generate_onboard_diagnostic_text(self):
        """OnBoard 종합 진단 텍스트 생성"""
        if 'statistics' not in self.analysis_results:
            return "분석 데이터가 없습니다."
        
        stats = self.analysis_results['statistics']
        
        # OnBoard 특화 진단
        avg_voltage = self.data['battery'].mean()
        voltage_std = self.data['battery'].std()
        cv = (voltage_std / avg_voltage) * 100
        
        # OnBoard 전압 등급 판정
        if avg_voltage >= 24.5:
            voltage_grade = "우수 (완전 충전)"
        elif avg_voltage >= 23.0:
            voltage_grade = "양호 (정상 운영)"
        elif avg_voltage >= 22.0:
            voltage_grade = "보통 (모니터링 필요)"
        elif avg_voltage >= 21.0:
            voltage_grade = "주의 (점검 권장)"
        else:
            voltage_grade = "위험 (즉시 점검)"
        
        # 안정성 등급
        if cv < 1.0:
            stability_grade = "매우 안정"
        elif cv < 2.0:
            stability_grade = "안정"
        elif cv < 5.0:
            stability_grade = "보통"
        else:
            stability_grade = "불안정"
        
        diagnostic_text = f"""OnBoard 시스템 종합 진단:

⚡ 전압 상태: {voltage_grade}
   평균 전압: {avg_voltage:.2f}V
   
📊 안정성: {stability_grade}
   변동계수: {cv:.2f}%
   
📈 데이터 품질: {"우수" if len(self.data) > 1000 else "양호" if len(self.data) > 100 else "제한적"}
   측정 포인트: {len(self.data):,}개
   
🔋 배터리 타입: 리튬이온 6S (OnBoard 전용)
   정격 전압: 22.2V (3.7V × 6셀)
"""
        
        return diagnostic_text
    
    def generate_voltage_analysis_text(self):
        """전압 분석 텍스트 생성"""
        voltage_data = self.data['battery']
        
        min_voltage = voltage_data.min()
        max_voltage = voltage_data.max()
        voltage_range = max_voltage - min_voltage
        
        # 전압 분포 분석
        q25 = voltage_data.quantile(0.25)
        q75 = voltage_data.quantile(0.75)
        
        voltage_text = f"""OnBoard 전압 상세 분석:

📊 전압 분포 (20V~26V 기준):
   최소: {min_voltage:.3f}V
   Q1: {q25:.3f}V  
   평균: {voltage_data.mean():.3f}V
   Q3: {q75:.3f}V
   최대: {max_voltage:.3f}V
   
📈 변동성:
   범위: {voltage_range:.3f}V
   표준편차: {voltage_data.std():.3f}V
   
⚡ OnBoard 기준 평가:
   {"정상 운영 범위" if 20.0 <= voltage_data.mean() <= 26.0 else "범위 벗어남"}
   {"안정적 변동" if voltage_range < 1.0 else "큰 변동"}
"""
        
        return voltage_text
    
    def generate_status_analysis_text(self):
        """상태 분석 텍스트 생성"""
        if 'status' not in self.data.columns:
            return "상태 정보가 없습니다."
        
        # STANDBY 비율 계산
        standby_count = (self.data['status'] == 'STANDBY').sum()
        standby_ratio = (standby_count / len(self.data)) * 100
        
        # LED 상태 분석
        led_analysis = ""
        if 'L1' in self.data.columns and 'L2' in self.data.columns:
            x_x_count = ((self.data['L1'] == 'X') & (self.data['L2'] == 'X')).sum()
            led_normal_ratio = (x_x_count / len(self.data)) * 100
            led_analysis = f"""
🔆 LED 상태:
   정상 상태 (X,X): {led_normal_ratio:.1f}%
   이상 상태: {100-led_normal_ratio:.1f}%"""
        
        # 메모 값 분석
        memo_analysis = ""
        if 'memo' in self.data.columns:
            try:
                memo_numeric = pd.to_numeric(self.data['memo'], errors='coerce')
                memo_valid = memo_numeric.dropna()
                if len(memo_valid) > 0:
                    memo_analysis = f"""
    
📝 메모 파라미터:
   범위: {memo_valid.min():.0f} ~ {memo_valid.max():.0f}
   평균: {memo_valid.mean():.1f}
   변동: {memo_valid.std():.1f}"""
            except:
                memo_analysis = "\n📝 메모: 분석 불가"
        
        status_text = f"""OnBoard 시스템 상태 분석:

🔄 운영 상태:
   STANDBY 비율: {standby_ratio:.1f}%
   {"안정적 대기 상태" if standby_ratio > 80 else "활성 상태 많음"}{led_analysis}{memo_analysis}
   
⏱️ 타이머 상태:
   00:00 비율: {((self.data['timer'] == '00:00').sum() / len(self.data) * 100):.1f}%
"""
        
        return status_text
    
    def generate_health_analysis_text(self):
        """건강도 분석 텍스트 생성"""
        if 'health' not in self.analysis_results:
            return "건강도 분석 데이터가 없습니다."
        
        health_data = self.analysis_results['health']
        
        # OnBoard 건강도 점수 계산
        avg_voltage = self.data['battery'].mean()
        if avg_voltage >= 24.5:
            health_score = 100
            health_grade = "우수"
            health_color = "🟢"
        elif avg_voltage >= 23.0:
            health_score = 85
            health_grade = "양호"
            health_color = "🟡"
        elif avg_voltage >= 22.0:
            health_score = 70
            health_grade = "보통"
            health_color = "🟠"
        elif avg_voltage >= 21.0:
            health_score = 55
            health_grade = "주의"
            health_color = "🔴"
        else:
            health_score = 40
            health_grade = "위험"
            health_color = "🔴"
        
        # 권장사항
        if health_score >= 85:
            recommendation = "현재 상태 유지, 정기 모니터링 지속"
        elif health_score >= 70:
            recommendation = "1주일 내 재점검 권장"
        elif health_score >= 55:
            recommendation = "3일 내 시스템 점검 필요"
        else:
            recommendation = "즉시 전문가 점검 및 배터리 교체 검토"
        
        health_text = f"""OnBoard 건강도 평가:

{health_color} 종합 점수: {health_score}점 ({health_grade})

📊 평가 기준 (OnBoard 6S 시스템):
   24.5V 이상: 100점 (완전 충전)
   23.0V 이상: 85점 (정상 운영)  
   22.0V 이상: 70점 (모니터링)
   21.0V 이상: 55점 (주의)
   20.0V 이상: 40점 (교체 고려)
   
💡 권장사항:
   {recommendation}
   
📈 추세:
   {"상승" if self.data['battery'].iloc[-10:].mean() > self.data['battery'].iloc[:10].mean() else "하락" if self.data['battery'].iloc[-10:].mean() < self.data['battery'].iloc[:10].mean() else "안정"}
"""
        
        return health_text
    
    def update_performance_analysis(self):
        """성능 분석 업데이트"""
        if self.data is None or not self.analysis_results:
            return
        
        # 성능 그래프 그리기
        self.plot_performance_graphs()
        
        # 효율성 정보
        if 'efficiency' in self.analysis_results:
            efficiency_info = self.analysis_results['efficiency']
            efficiency_text = ""
            for key, value in efficiency_info.items():
                efficiency_text += f"• {key}: {value}\n"
            self.efficiency_text.setText(efficiency_text)
    
    def plot_performance_graphs(self):
        """성능 지표 그래프 그리기"""
        if self.data is None:
            return
        
        self.performance_figure.clear()
        
        # 2x2 서브플롯 생성
        axes = self.performance_figure.subplots(2, 2)
        
        # 한글 폰트 설정 적용
        if self.korean_font:
            for ax in axes.flat:
                for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                            ax.get_xticklabels() + ax.get_yticklabels()):
                    item.set_fontfamily(self.korean_font)
        
        # 배터리 성능 지표들
        self.plot_voltage_stability(axes[0, 0])
        self.plot_capacity_trend(axes[0, 1])
        self.plot_efficiency_metrics(axes[1, 0])
        self.plot_health_score(axes[1, 1])
        
        self.performance_figure.tight_layout()
        self.performance_canvas.draw()
    
    def plot_voltage_stability(self, ax):
        """전압 안정성 그래프"""
        # 롤링 표준편차로 안정성 측정
        window_size = max(10, len(self.data) // 20)
        rolling_std = self.data['battery'].rolling(window=window_size).std()
        
        x_data, _ = self.prepare_time_axis(self.data)
        
        ax.plot(x_data, rolling_std, color='orange', linewidth=2)
        ax.set_title('전압 안정성 (롤링 표준편차)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('표준편차 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        self.apply_grid_settings(ax)
        
        # 안정성 임계값 표시
        stability_threshold = rolling_std.mean() + rolling_std.std()
        ax.axhline(y=stability_threshold, color='red', linestyle='--', alpha=0.7,
                   label=f'불안정 임계값: {stability_threshold:.4f}V')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
    
    def plot_capacity_trend(self, ax):
        """용량 트렌드 그래프"""
        # 이동 평균으로 용량 트렌드 추정
        window_size = max(20, len(self.data) // 10)
        capacity_trend = self.data['battery'].rolling(window=window_size).mean()
        
        x_data, _ = self.prepare_time_axis(self.data)
        
        ax.plot(x_data, capacity_trend, color='green', linewidth=2)
        ax.set_title('용량 트렌드', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('평균 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        self.apply_grid_settings(ax)
        
        # 트렌드 라인 추가
        if len(capacity_trend.dropna()) > 1:
            z = np.polyfit(range(len(capacity_trend.dropna())), capacity_trend.dropna(), 1)
            p = np.poly1d(z)
            trend_line = p(range(len(capacity_trend.dropna())))
            ax.plot(x_data[:len(trend_line)], trend_line, 'r--', alpha=0.7,
                   label=f'트렌드: {z[0]:.6f}V/측정')
            ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
    
    def plot_efficiency_metrics(self, ax):
        """효율성 메트릭 그래프"""
        # 효율성 점수들을 바 차트로 표시
        efficiency_data = self.analysis_results.get('efficiency', {})
        
        if efficiency_data:
            categories = []
            scores = []
            
            for key, value in efficiency_data.items():
                categories.append(key.replace('효율성', ''))
                # 백분율 문자열에서 숫자 추출
                try:
                    score = float(value.replace('%', ''))
                    scores.append(score)
                except:
                    scores.append(0)
            
            bars = ax.bar(categories, scores, color=['skyblue', 'lightgreen', 'orange', 'pink'])
            ax.set_title('효율성 지표', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            ax.set_ylabel('효율성 (%)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            ax.set_ylim(0, 100)
            
            # 값 레이블 추가
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{score:.1f}%', ha='center', va='bottom',
                       fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            
            plt.setp(ax.get_xticklabels(), rotation=45)
            self.apply_grid_settings(ax)
        else:
            ax.text(0.5, 0.5, '효율성 데이터 없음', transform=ax.transAxes, 
                   ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
    
    def plot_health_score(self, ax):
        """건강도 점수 그래프"""
        health_data = self.analysis_results.get('health', {})
        
        if health_data and '종합 건강도' in health_data:
            # 건강도 점수를 원형 게이지로 표시
            try:
                health_str = health_data['종합 건강도']
                # "우수 (85.2점)" 형태에서 점수 추출
                import re
                score_match = re.search(r'(\d+\.?\d*)', health_str)
                if score_match:
                    health_score = float(score_match.group(1))
                else:
                    health_score = 75  # 기본값
            except:
                health_score = 75
            
            # 원형 게이지 그리기
            theta = np.linspace(0, 2*np.pi, 100)
            r = 1
            
            # 배경 원
            ax.plot(r * np.cos(theta), r * np.sin(theta), 'lightgray', linewidth=8)
            
            # 점수에 따른 색상 결정
            if health_score >= 80:
                color = 'green'
            elif health_score >= 60:
                color = 'orange'
            else:
                color = 'red'
            
            # 점수 호
            score_theta = np.linspace(0, 2*np.pi * health_score/100, int(health_score))
            ax.plot(r * np.cos(score_theta), r * np.sin(score_theta), color, linewidth=8)
            
            # 중앙에 점수 표시
            ax.text(0, 0, f'{health_score:.1f}점', ha='center', va='center', 
                   fontsize=16, fontweight='bold',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            
            ax.set_xlim(-1.5, 1.5)
            ax.set_ylim(-1.5, 1.5)
            ax.set_aspect('equal')
            ax.axis('off')
            ax.set_title('배터리 건강도', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        else:
            ax.text(0.5, 0.5, '건강도 데이터 없음', transform=ax.transAxes, 
                   ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
    
    def update_main_graph(self):
        """메인 그래프 업데이트 - 비교 모드와 단일 모드 구분 처리"""
        if self.data is None and not self.multiple_data:
            return
        
        self.main_figure.clear()
        
        # 비교 모드인지 확인
        if self.comparison_mode and self.multiple_data:
            # 비교 모드: 시계열만 지원 (다른 그래프 타입은 상세 분석 탭에서)
            self.create_comparison_time_series()
        else:
            # 단일 모드: 모든 그래프 타입 지원
            graph_type = self.graph_type_combo.currentText()
            
            if graph_type == '시계열':
                self.plot_time_series()
            elif graph_type == '히스토그램':
                self.plot_histogram()
            elif graph_type == '박스플롯':
                self.plot_boxplot()
            elif graph_type == '산점도':
                self.plot_scatter()
        
        self.main_canvas.draw()
    
    def plot_time_series(self):
        """시계열 그래프 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        # 현재 데이터 가져오기
        current_data = self.get_current_data()
        if current_data is None or len(current_data) == 0:
            ax.text(0.5, 0.5, '표시할 데이터가 없습니다.\n필터 설정을 확인하세요.', 
                   transform=ax.transAxes, ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        # 시간 축 데이터 준비
        x_data, x_label = self.prepare_time_axis(current_data)
        
        # 데이터 유효성 검사
        if len(x_data) != len(current_data['battery']):
            print(f"데이터 길이 불일치: x_data={len(x_data)}, battery={len(current_data['battery'])}")
            return
        
        # 배터리 전압 시계열 그리기
        try:
            line = ax.plot(x_data, current_data['battery'], 
                          linewidth=1.5, label='배터리 전압', color='blue', alpha=0.8)
            
            # 데이터가 실제로 그려졌는지 확인
            if len(line) > 0:
                print(f"시계열 그래프 그리기 성공: {len(current_data)} 포인트")
            else:
                print("시계열 그래프 그리기 실패")
                
        except Exception as e:
            print(f"시계열 그래프 그리기 오류: {e}")
            # 오류 발생 시 인덱스 기반으로 대체
            ax.plot(range(len(current_data)), current_data['battery'], 
                   linewidth=1.5, label='배터리 전압', color='blue', alpha=0.8)
            x_label = '데이터 포인트 인덱스'
        
        # 이상치 표시
        if self.show_anomalies.isChecked() and 'anomalies' in self.analysis_results:
            anomalies = self.analysis_results['anomalies']
            if len(anomalies) > 0:
                # 현재 데이터 범위 내의 이상치만 표시
                anomalies_in_range = anomalies[anomalies.index.isin(current_data.index)]
                if len(anomalies_in_range) > 0:
                    try:
                        anomaly_x_data = self.convert_time_axis(anomalies_in_range['timestamp'], current_data)
                        ax.scatter(anomaly_x_data, anomalies_in_range['battery'],
                                  color='red', s=50, alpha=0.7, label=f'이상치 ({len(anomalies_in_range)}개)', 
                                  zorder=5, marker='x', linewidths=2)
                    except Exception as e:
                        print(f"이상치 표시 오류: {e}")
        
        # 트렌드 라인
        if self.show_trends.isChecked():
            try:
                z = np.polyfit(range(len(current_data)), current_data['battery'], 1)
                p = np.poly1d(z)
                time_span_hours = (current_data['timestamp'].max() - current_data['timestamp'].min()).total_seconds() / 3600
                slope_per_hour = z[0] * (len(current_data) / max(time_span_hours, 1))
                ax.plot(x_data, p(range(len(current_data))),
                        "r--", alpha=0.8, label=f'트렌드 ({slope_per_hour:.4f}V/h)')
            except Exception as e:
                print(f"트렌드 라인 오류: {e}")
        
        # 평균선 표시
        if self.show_statistics.isChecked():
            mean_voltage = current_data['battery'].mean()
            ax.axhline(y=mean_voltage, color='green', linestyle=':', alpha=0.7,
                       label=f'평균: {mean_voltage:.3f}V')
        
        # 선택 구간 표시
        if self.current_selection:
            try:
                selection_start = self.current_selection['start_time']
                selection_end = self.current_selection['end_time']
                
                # 선택 구간을 현재 시간 축 형식으로 변환
                start_x = self.convert_single_time(selection_start, current_data)
                end_x = self.convert_single_time(selection_end, current_data)
                
                ax.axvspan(start_x, end_x, alpha=0.2, color='yellow', 
                          label='선택 구간')
            except Exception as e:
                print(f"선택 구간 표시 오류: {e}")
        
        # 축 라벨 및 제목 설정
        ax.set_xlabel(x_label, fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 시계열', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        
        # Y축 범위를 데이터 범위에 맞게 설정
        voltage_min = current_data['battery'].min()
        voltage_max = current_data['battery'].max()
        voltage_range = voltage_max - voltage_min
        
        # 여유분 추가 (데이터 범위의 5%)
        margin = max(voltage_range * 0.05, 0.1)  # 최소 0.1V 여유분
        ax.set_ylim(voltage_min - margin, voltage_max + margin)
        
        print(f"Y축 범위 설정: {voltage_min - margin:.3f}V ~ {voltage_max + margin:.3f}V")
        
        # 범례 표시
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        
        # 격자 표시
        self.apply_grid_settings(ax)
        
        # 커서 십자선 설정
        self.setup_crosshair(ax)
        
        # 시간 축 포맷 설정
        time_option = self.time_display_combo.currentText()
        if time_option == '절대시간':
            try:
                # 절대시간 처리 개선
                if len(current_data) > 100:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(current_data)//100)))
                else:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=max(1, len(current_data)//20)))
                
                # X축 범위 명시적 설정
                ax.set_xlim(current_data['timestamp'].min(), current_data['timestamp'].max())
                
                # 날짜 형식 자동 조정
                self.main_figure.autofmt_xdate()
                
                print(f"절대시간 축 설정 완료: {current_data['timestamp'].min()} ~ {current_data['timestamp'].max()}")
                
            except Exception as e:
                print(f"절대시간 축 설정 오류: {e}")
                # 오류 발생 시 상대시간으로 대체
                start_time = current_data['timestamp'].min()
                relative_seconds = (current_data['timestamp'] - start_time).dt.total_seconds()
                ax.clear()
                ax.plot(relative_seconds, current_data['battery'], 
                       linewidth=1.5, label='배터리 전압', color='blue', alpha=0.8)
                ax.set_xlabel('시작점으로부터 경과시간 (초)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_title('배터리 전압 시계열 (상대시간)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_ylim(voltage_min - margin, voltage_max + margin)
                ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
                self.apply_grid_settings(ax)
        
        # 마우스 모드에 따른 설정 적용
        self.change_mouse_mode()
        
        # 그래프 새로고침 강제
        try:
            ax.relim()
            ax.autoscale_view()
            self.main_canvas.draw()
        except Exception as e:
            print(f"그래프 새로고침 오류: {e}")
    
    def get_current_data(self):
        """현재 사용할 데이터 반환 (필터링된 데이터 우선, 비교 모드 지원)"""
        if self.comparison_mode and self.multiple_data:
            # 비교 모드에서는 첫 번째 파일 데이터를 기본으로 반환
            first_filename = list(self.multiple_data.keys())[0]
            primary_data = self.multiple_data[first_filename]['data']
            return self.filtered_data if self.filtered_data is not None else primary_data
        else:
            # 단일 파일 모드
            return self.filtered_data if self.filtered_data is not None else self.data
    
    def get_all_comparison_data(self):
        """비교 모드에서 모든 파일의 데이터 반환"""
        if not self.comparison_mode or not self.multiple_data:
            return {}
        
        result = {}
        for filename, file_info in self.multiple_data.items():
            if filename in [os.path.basename(path) for path in self.selected_files]:
                result[filename] = file_info['data']
        
        return result
    
    def prepare_time_axis(self, data):
        """시간 축 데이터 준비"""
        time_option = self.time_display_combo.currentText()
        
        if time_option == '절대시간':
            return data['timestamp'], '시간'
        elif time_option == '상대시간(시작점 기준)':
            start_time = data['timestamp'].min()
            relative_seconds = (data['timestamp'] - start_time).dt.total_seconds()
            return relative_seconds, '시작점으로부터 경과시간 (초)'
        elif time_option == '경과시간(분)':
            start_time = data['timestamp'].min()
            elapsed_minutes = (data['timestamp'] - start_time).dt.total_seconds() / 60
            return elapsed_minutes, '경과시간 (분)'
        elif time_option == '경과시간(시간)':
            start_time = data['timestamp'].min()
            elapsed_hours = (data['timestamp'] - start_time).dt.total_seconds() / 3600
            return elapsed_hours, '경과시간 (시간)'
        else:
            return data['timestamp'], '시간'
    
    def convert_time_axis(self, timestamps, reference_data):
        """주어진 타임스탬프를 현재 시간 축 옵션에 맞게 변환"""
        time_option = self.time_display_combo.currentText()
        
        if time_option == '절대시간':
            return timestamps
        elif time_option == '상대시간(시작점 기준)':
            start_time = reference_data['timestamp'].min()
            return (timestamps - start_time).dt.total_seconds()
        elif time_option == '경과시간(분)':
            start_time = reference_data['timestamp'].min()
            return (timestamps - start_time).dt.total_seconds() / 60
        elif time_option == '경과시간(시간)':
            start_time = reference_data['timestamp'].min()
            return (timestamps - start_time).dt.total_seconds() / 3600
        else:
            return timestamps
    
    def convert_single_time(self, single_timestamp, reference_data):
        """단일 타임스탬프를 현재 시간 축 옵션에 맞게 변환"""
        time_option = self.time_display_combo.currentText()
        
        if time_option == '절대시간':
            return single_timestamp
        elif time_option == '상대시간(시작점 기준)':
            start_time = reference_data['timestamp'].min()
            return (single_timestamp - start_time).total_seconds()
        elif time_option == '경과시간(분)':
            start_time = reference_data['timestamp'].min()
            return (single_timestamp - start_time).total_seconds() / 60
        elif time_option == '경과시간(시간)':
            start_time = reference_data['timestamp'].min()
            return (single_timestamp - start_time).total_seconds() / 3600
        else:
            return single_timestamp
    
    def apply_grid_settings(self, ax):
        """격자 설정 적용"""
        if self.show_grid_check.isChecked():
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            
            if self.show_minor_grid_check.isChecked():
                ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.3)
                ax.minorticks_on()
        else:
            ax.grid(False)
    
    def plot_histogram(self):
        """히스토그램 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        current_data = self.get_current_data()
        if current_data is None or len(current_data) == 0:
            ax.text(0.5, 0.5, '표시할 데이터가 없습니다.\n필터 설정을 확인하세요.', 
                   transform=ax.transAxes, ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        battery_data = current_data['battery']
        
        # 히스토그램 그리기
        n, bins, patches = ax.hist(battery_data, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        
        ax.set_xlabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('빈도', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 분포', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.grid(True, alpha=0.3)
        
        # 통계 정보 추가
        mean_val = battery_data.mean()
        std_val = battery_data.std()
        ax.axvline(mean_val, color='red', linestyle='--', 
                   label=f'평균: {mean_val:.2f}V')
        ax.axvline(mean_val + std_val, color='orange', linestyle='--', 
                   label=f'+1σ: {mean_val + std_val:.2f}V')
        ax.axvline(mean_val - std_val, color='orange', linestyle='--', 
                   label=f'-1σ: {mean_val - std_val:.2f}V')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        
        # X축 범위를 데이터 범위에 맞게 설정
        voltage_min = battery_data.min()
        voltage_max = battery_data.max()
        voltage_range = voltage_max - voltage_min
        margin = max(voltage_range * 0.05, 0.1)
        ax.set_xlim(voltage_min - margin, voltage_max + margin)
        
        print(f"히스토그램 X축 범위: {voltage_min - margin:.3f}V ~ {voltage_max + margin:.3f}V")
    
    def plot_boxplot(self):
        """박스플롯 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        current_data = self.get_current_data()
        if current_data is None or len(current_data) == 0:
            ax.text(0.5, 0.5, '표시할 데이터가 없습니다.\n필터 설정을 확인하세요.', 
                   transform=ax.transAxes, ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        # 시간대별 박스플롯 (1시간 단위)
        data_copy = current_data.copy()
        data_copy['hour'] = data_copy['timestamp'].dt.hour
        hours = sorted(data_copy['hour'].unique())
        
        if len(hours) > 24:
            # 데이터가 많으면 4시간 단위로 그룹화
            data_copy['hour_group'] = (data_copy['hour'] // 4) * 4
            hours = sorted(data_copy['hour_group'].unique())
            hourly_data = [data_copy[data_copy['hour_group'] == h]['battery'].values 
                          for h in hours]
            labels = [f'{h:02d}-{h+3:02d}시' for h in hours]
        else:
            hourly_data = [data_copy[data_copy['hour'] == h]['battery'].values 
                          for h in hours]
            labels = [f'{h:02d}시' for h in hours]
        
        # 빈 데이터 제거
        valid_data = [(data, label) for data, label in zip(hourly_data, labels) if len(data) > 0]
        if valid_data:
            hourly_data, labels = zip(*valid_data)
            
            bp = ax.boxplot(hourly_data, labels=labels, patch_artist=True)
            
            # 박스 색상 설정
            for patch in bp['boxes']:
                patch.set_facecolor('lightblue')
                patch.set_alpha(0.7)
        
        ax.set_xlabel('시간', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('시간대별 배터리 전압 분포', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.grid(True, alpha=0.3)
        
        # Y축 범위를 데이터 범위에 맞게 설정
        voltage_min = current_data['battery'].min()
        voltage_max = current_data['battery'].max()
        voltage_range = voltage_max - voltage_min
        margin = max(voltage_range * 0.05, 0.1)
        ax.set_ylim(voltage_min - margin, voltage_max + margin)
        
        print(f"박스플롯 Y축 범위: {voltage_min - margin:.3f}V ~ {voltage_max + margin:.3f}V")
        
        # x축 라벨 회전
        plt.setp(ax.get_xticklabels(), rotation=45)
    
    def plot_scatter(self):
        """산점도 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        current_data = self.get_current_data()
        if current_data is None or len(current_data) == 0:
            ax.text(0.5, 0.5, '표시할 데이터가 없습니다.\n필터 설정을 확인하세요.', 
                   transform=ax.transAxes, ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        # 시간을 숫자로 변환 (시작 시간으로부터 경과 시간)
        time_numeric = (current_data['timestamp'] - current_data['timestamp'].min()).dt.total_seconds() / 3600  # 시간 단위
        
        # 컬러맵으로 시간 진행 표현
        scatter = ax.scatter(time_numeric, current_data['battery'], 
                           c=time_numeric, cmap='viridis', alpha=0.6, s=20)
        
        ax.set_xlabel('경과 시간 (시간)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 산점도 (시간 진행)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        
        # 컬러바 추가
        cbar = self.main_figure.colorbar(scatter, ax=ax)
        cbar.set_label('경과 시간 (시간)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        
        ax.grid(True, alpha=0.3)
        
        # Y축 범위를 데이터 범위에 맞게 설정
        voltage_min = current_data['battery'].min()
        voltage_max = current_data['battery'].max()
        voltage_range = voltage_max - voltage_min
        margin = max(voltage_range * 0.05, 0.1)
        ax.set_ylim(voltage_min - margin, voltage_max + margin)
        
        print(f"산점도 Y축 범위: {voltage_min - margin:.3f}V ~ {voltage_max + margin:.3f}V")
        
        # 트렌드 라인 추가 (옵션)
        if self.show_trends.isChecked():
            z = np.polyfit(time_numeric, current_data['battery'], 1)
            p = np.poly1d(z)
            ax.plot(time_numeric, p(time_numeric), "r--", alpha=0.8, 
                   label=f'트렌드 (기울기: {z[0]:.4f}V/h)')
            ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
    
    def update_detail_analysis(self):
        """상세 분석 탭 업데이트"""
        if self.data is None:
            return
        
        self.detail_figure.clear()
        
        # 2x2 서브플롯 생성 (figsize 제거)
        axes = self.detail_figure.subplots(2, 2)
        
        # 한글 폰트 설정 적용
        if self.korean_font:
            for ax in axes.flat:
                for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                            ax.get_xticklabels() + ax.get_yticklabels()):
                    item.set_fontfamily(self.korean_font)
        
        # 이동 평균
        self.plot_moving_average(axes[0, 0])
        
        # 변화율 분석
        self.plot_change_rate(axes[0, 1])
        
        # 이상치 분석
        self.plot_anomaly_analysis(axes[1, 0])
        
        # 주기성 분석
        self.plot_periodicity_analysis(axes[1, 1])
        
        self.detail_figure.tight_layout()
        self.detail_canvas.draw()
    
    def plot_moving_average(self, ax):
        """이동 평균 그래프"""
        if len(self.data) < 10:
            ax.text(0.5, 0.5, '데이터 부족 (최소 10개 포인트 필요)', 
                    transform=ax.transAxes, ha='center', va='center',
                    fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        # 여러 윈도우 크기의 이동 평균
        windows = [10, 30, 100]
        colors = ['red', 'green', 'purple']
        
        ax.plot(self.data['timestamp'], self.data['battery'], 
                color='lightblue', alpha=0.5, label='원본 데이터', linewidth=0.5)
        
        for window, color in zip(windows, colors):
            if len(self.data) > window:
                ma = self.data['battery'].rolling(window=window).mean()
                ax.plot(self.data['timestamp'], ma, 
                        color=color, label=f'{window}점 이동평균', linewidth=2)
        
        ax.set_title('이동 평균 분석', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_xlabel('시간', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        ax.grid(True, alpha=0.3)
        
        # x축 포맷 설정
        if len(self.data) > 100:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
    def plot_change_rate(self, ax):
        """변화율 그래프"""
        if len(self.data) < 2:
            ax.text(0.5, 0.5, '변화율 계산 불가 (최소 2개 포인트 필요)', 
                    transform=ax.transAxes, ha='center', va='center',
                    fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        change_rate = self.data['battery'].pct_change() * 100
        
        # 변화율 그래프
        ax.plot(self.data['timestamp'][1:], change_rate[1:], 
                color='orange', linewidth=1, alpha=0.8)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 평균 변화율 표시
        mean_change = change_rate.mean()
        ax.axhline(y=mean_change, color='red', linestyle='--', alpha=0.7,
                   label=f'평균 변화율: {mean_change:.3f}%')
        
        ax.set_title('배터리 전압 변화율', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_xlabel('시간', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('변화율 (%)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        ax.grid(True, alpha=0.3)
        
        # x축 포맷 설정
        if len(self.data) > 100:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
    def plot_anomaly_analysis(self, ax):
        """이상치 분석 그래프"""
        if 'anomalies' not in self.analysis_results:
            ax.text(0.5, 0.5, '이상치 분석 결과 없음\n분석을 다시 실행해주세요', 
                    transform=ax.transAxes, ha='center', va='center',
                    fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            ax.set_title('이상치 분석', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        anomalies = self.analysis_results['anomalies']
        
        if len(anomalies) == 0:
            ax.text(0.5, 0.5, '이상치가 발견되지 않았습니다\n데이터가 안정적입니다', 
                    transform=ax.transAxes, ha='center', va='center',
                    fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            ax.set_title('이상치 분석 - 정상', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        # 정상 데이터와 이상치 구분
        normal_data = self.data[~self.data.index.isin(anomalies.index)]
        
        # 정상 데이터 플롯
        ax.scatter(normal_data['timestamp'], normal_data['battery'], 
                   color='blue', alpha=0.5, s=10, label=f'정상 데이터 ({len(normal_data)}개)')
        
        # 이상치 플롯
        ax.scatter(anomalies['timestamp'], anomalies['battery'], 
                   color='red', s=50, alpha=0.8, marker='x', 
                   label=f'이상치 ({len(anomalies)}개)', linewidths=2)
        
        ax.set_title(f'이상치 분석 (총 {len(anomalies)}개 발견)', 
                     fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_xlabel('시간', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        ax.grid(True, alpha=0.3)
        
        # x축 포맷 설정
        if len(self.data) > 100:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
    def plot_periodicity_analysis(self, ax):
        """주기성 분석 그래프"""
        try:
            from scipy import signal
            
            # 리샘플링 (등간격) - 1초 간격으로 보간
            resampled = self.data.set_index('timestamp').resample('1S')['battery'].mean().interpolate()
            
            if len(resampled) < 10:
                ax.text(0.5, 0.5, '주기성 분석 불가\n데이터 부족 (최소 10개 포인트 필요)', 
                        transform=ax.transAxes, ha='center', va='center',
                        fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_title('주기성 분석', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                return
            
            # FFT를 이용한 주파수 분석
            frequencies, power = signal.periodogram(resampled.values, fs=1.0)
            
            # DC 성분 제거 (첫 번째 주파수 제외)
            frequencies = frequencies[1:]
            power = power[1:]
            
            if len(frequencies) > 0:
                # 파워 스펙트럼 플롯
                ax.semilogy(frequencies, power, color='purple', linewidth=1.5)
                
                # 주요 주파수 찾기
                peak_idx = np.argmax(power)
                dominant_freq = frequencies[peak_idx]
                dominant_period = 1 / dominant_freq if dominant_freq > 0 else float('inf')
                
                # 주요 주파수 표시
                ax.axvline(dominant_freq, color='red', linestyle='--', alpha=0.7,
                          label=f'주요 주파수: {dominant_freq:.4f} Hz\n주기: {dominant_period:.1f}초')
                
                ax.set_title('주파수 분석 (주기성 검출)', 
                            fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_xlabel('주파수 (Hz)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_ylabel('파워 스펙트럼', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, '주파수 데이터 없음', 
                        transform=ax.transAxes, ha='center', va='center',
                        fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                ax.set_title('주기성 분석', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
                
        except ImportError:
            ax.text(0.5, 0.5, 'scipy 모듈이 필요합니다\npip install scipy로 설치하세요', 
                    transform=ax.transAxes, ha='center', va='center',
                    fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            ax.set_title('주기성 분석 - 모듈 없음', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        except Exception as e:
            ax.text(0.5, 0.5, f'주기성 분석 오류:\n{str(e)}', 
                    transform=ax.transAxes, ha='center', va='center',
                    fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            ax.set_title('주기성 분석 - 오류', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
    
    def update_statistics(self):
        """OnBoard 로그 특화 통계 테이블 업데이트"""
        if self.data is None:
            return
        
        # OnBoard 로그인지 확인
        is_onboard = self.is_onboard_log()
        
        if is_onboard:
            stats = self.get_onboard_statistics()
        else:
            stats = self.analysis_results.get('statistics', {})
        
        # 테이블 설정
        self.stats_table.setRowCount(len(stats))
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(['분석 항목', '결과값', '도움말'])
        
        # 데이터 입력
        row = 0
        for key, value in stats.items():
            # 항목명
            self.stats_table.setItem(row, 0, QTableWidgetItem(str(key)))
            
            # 결과값
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(value)))
            
            # 도움말 버튼 (위젯으로 추가)
            help_widget = QWidget()
            help_layout = QHBoxLayout(help_widget)
            help_layout.setContentsMargins(2, 2, 2, 2)
            
            # 해당 항목의 도움말 찾기
            help_key = self.find_help_key_for_stat(key)
            if help_key:
                help_btn = HelpButton(self.help_texts[help_key])
                help_layout.addWidget(help_btn)
            else:
                help_layout.addWidget(QLabel(""))
            
            help_layout.addStretch()
            self.stats_table.setCellWidget(row, 2, help_widget)
            
            row += 1
        
        # 테이블 크기 조정
        self.stats_table.resizeColumnsToContents()
        self.stats_table.setColumnWidth(2, 50)  # 도움말 컬럼 폭 고정

    def get_onboard_statistics(self):
        """OnBoard 로그 전용 통계 생성"""
        if self.data is None:
            return {}
        
        stats = {}
        battery_data = self.data['battery']
        
        # 기본 전압 통계
        stats['평균 전압 (V)'] = f"{battery_data.mean():.3f}"
        stats['중앙값 전압 (V)'] = f"{battery_data.median():.3f}"
        stats['표준편차 (V)'] = f"{battery_data.std():.3f}"
        stats['최소 전압 (V)'] = f"{battery_data.min():.3f}"
        stats['최대 전압 (V)'] = f"{battery_data.max():.3f}"
        stats['전압 범위 (V)'] = f"{battery_data.max() - battery_data.min():.3f}"
        stats['변동계수 (%)'] = f"{(battery_data.std() / battery_data.mean()) * 100:.2f}"
        
        # OnBoard 특화 통계
        stats['데이터 포인트 수'] = f"{len(self.data):,}개"
        stats['측정 기간'] = f"{self.get_duration_str(self.data)}"
        stats['평균 측정 간격'] = f"{self.get_average_interval(self.data)}"
        
        # 백분위수
        stats['25% 백분위수 (V)'] = f"{battery_data.quantile(0.25):.3f}"
        stats['75% 백분위수 (V)'] = f"{battery_data.quantile(0.75):.3f}"
        stats['95% 백분위수 (V)'] = f"{battery_data.quantile(0.95):.3f}"
        
        # OnBoard 상태 통계
        if 'status' in self.data.columns:
            standby_ratio = (self.data['status'] == 'STANDBY').sum() / len(self.data) * 100
            stats['STANDBY 비율 (%)'] = f"{standby_ratio:.1f}"
        
        # LED 상태 통계
        if 'L1' in self.data.columns and 'L2' in self.data.columns:
            normal_led_ratio = ((self.data['L1'] == 'X') & (self.data['L2'] == 'X')).sum() / len(self.data) * 100
            stats['정상 LED 상태 (%)'] = f"{normal_led_ratio:.1f}"
        
        # 메모 통계
        if 'memo' in self.data.columns:
            try:
                memo_numeric = pd.to_numeric(self.data['memo'], errors='coerce').dropna()
                if len(memo_numeric) > 0:
                    stats['메모 평균값'] = f"{memo_numeric.mean():.1f}"
                    stats['메모 범위'] = f"{memo_numeric.min():.0f} ~ {memo_numeric.max():.0f}"
            except:
                pass
        
        # 방전률 계산
        if len(self.data) > 1:
            time_span_hours = (self.data['timestamp'].max() - self.data['timestamp'].min()).total_seconds() / 3600
            voltage_change = self.data['battery'].iloc[-1] - self.data['battery'].iloc[0]
            if time_span_hours > 0:
                discharge_rate = voltage_change / time_span_hours
                stats['평균 방전률 (V/h)'] = f"{discharge_rate:.4f}"
        
        return stats
    
    def find_help_key_for_stat(self, stat_name):
        """통계 항목명에 해당하는 도움말 키 찾기"""
        help_mapping = {
            '평균 전압': '평균 전압',
            '변동계수': '전압 안정성',
            '방전률': '방전률',
            'STANDBY 비율': 'STANDBY 비율',
            '정상 LED 상태': 'LED 상태 분석',
            '메모': '메모 값 분석',
            '측정 간격': '측정 간격'
        }
        
        for keyword, help_key in help_mapping.items():
            if keyword in stat_name:
                return help_key
        
        return None
    
    def get_duration_str(self, data):
        """측정 기간 문자열 반환"""
        duration = data['timestamp'].max() - data['timestamp'].min()
        
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0:
            parts.append(f"{minutes}분")
        
        return " ".join(parts) if parts else "1분 미만"
    
    def get_average_interval(self, data):
        """평균 측정 간격 계산"""
        if len(data) < 2:
            return "계산 불가"
        
        time_diffs = data['timestamp'].diff().dropna()
        avg_interval = time_diffs.mean()
        
        if avg_interval.total_seconds() < 60:
            return f"{avg_interval.total_seconds():.1f}초"
        elif avg_interval.total_seconds() < 3600:
            return f"{avg_interval.total_seconds()/60:.1f}분"
        else:
            return f"{avg_interval.total_seconds()/3600:.1f}시간"
    
    def apply_filters(self):
        """모든 필터 적용 (시간 범위 + 배터리 범위) - 성능 최적화"""
        if self.data is None:
            QMessageBox.warning(self, '오류', '분석할 데이터가 없습니다.')
            return
        
        # 진행 상태 표시
        self.statusBar().showMessage('필터를 적용하는 중...')
        
        try:
            filtered = self.data.copy()
            original_count = len(filtered)
            
            # 1. 시간 범위 필터 적용
            range_text = self.time_range_combo.currentText()
            
            if range_text != '전체':
                now = self.data['timestamp'].max()
                
                if range_text == '최근 1시간':
                    start_time = now - timedelta(hours=1)
                elif range_text == '최근 6시간':
                    start_time = now - timedelta(hours=6)
                elif range_text == '최근 24시간':
                    start_time = now - timedelta(hours=24)
                else:
                    start_time = None
                
                if start_time is not None:
                    filtered = filtered[filtered['timestamp'] >= start_time]
            
            time_filtered_count = len(filtered)
            
            # 2. 배터리 범위 필터 적용
            min_battery = self.battery_min_spin.value()
            max_battery = self.battery_max_spin.value()
            
            # 배터리 범위가 의미있는 경우에만 적용
            if min_battery > 0 or max_battery < 50:
                filtered = filtered[
                    (filtered['battery'] >= min_battery) & 
                    (filtered['battery'] <= max_battery)
                ]
            
            final_count = len(filtered)
            
            # 필터링된 데이터 저장
            self.filtered_data = filtered
            
            # 상태바에 상세 정보 표시
            filter_info = f'필터 적용 완료: {original_count:,} → '
            
            if range_text != '전체':
                filter_info += f'{time_filtered_count:,} (시간) → '
            
            filter_info += f'{final_count:,}개 (최종)'
            
            if range_text != '전체':
                filter_info += f' | 시간: {range_text}'
            
            if min_battery > 0 or max_battery < 50:
                filter_info += f' | 전압: {min_battery:.1f}V~{max_battery:.1f}V'
            
            # 필터링 결과가 없는 경우 경고
            if final_count == 0:
                QMessageBox.warning(self, '필터링 결과', 
                                  '필터 조건에 맞는 데이터가 없습니다.\n'
                                  '필터 설정을 확인해주세요.')
                self.statusBar().showMessage('필터링 결과 없음')
                return
            
            # 그래프 업데이트 (비동기적으로)
            if not hasattr(self, '_filter_update_timer'):
                self._filter_update_timer = QTimer()
                self._filter_update_timer.setSingleShot(True)
                self._filter_update_timer.timeout.connect(self._update_after_filter)
            
            self._filter_update_timer.stop()
            self._filter_update_timer.start(100)  # 100ms 후 업데이트
            
            self.statusBar().showMessage(filter_info, 5000)  # 5초간 표시
            print(f"필터링 완료: {original_count} → {final_count} 포인트")
            
        except Exception as e:
            print(f"필터 적용 오류: {e}")
            QMessageBox.critical(self, '오류', f'필터 적용 중 오류가 발생했습니다:\n{str(e)}')
            self.statusBar().showMessage('필터 적용 실패')
    
    def _update_after_filter(self):
        """필터 적용 후 그래프 업데이트"""
        try:
            # 현재 모드에 따라 적절한 업데이트 수행
            if self.comparison_mode and self.multiple_data:
                # 비교 모드에서는 메인 그래프만 업데이트
                self._update_comparison_main_only()
            else:
                # 단일 모드에서는 선택적 업데이트
                self._update_single_main_only()
                
                # 통계 정보도 업데이트 (가벼운 작업)
                if hasattr(self, 'update_statistics'):
                    self.update_statistics()
            
            # 완료 메시지
            final_count = len(self.filtered_data) if self.filtered_data is not None else 0
            self.statusBar().showMessage(f'필터 적용 및 그래프 업데이트 완료 - {final_count:,}개 데이터', 3000)
            
        except Exception as e:
            print(f"필터 후 업데이트 오류: {e}")
            self.statusBar().showMessage(f'그래프 업데이트 오류: {str(e)}', 3000)
    
    def on_canvas_press(self, event):
        """캔버스 마우스 눌림 이벤트"""
        if event.inaxes is None:
            return
        
        mode = self.mouse_mode_combo.currentText()
        
        # 마우스 가운데 버튼 (휠 클릭) 드래그
        if event.button == 2:  # 가운데 버튼
            self.middle_button_pressed = True
            self.last_mouse_pos = (event.xdata, event.ydata)
            self.original_xlim = event.inaxes.get_xlim()
            self.original_ylim = event.inaxes.get_ylim()
            return
        
        if mode == '드래그 이동' and event.button == 1:  # 왼쪽 버튼
            # 드래그 이동 모드
            self.is_dragging = True
            self.drag_start_x = event.xdata
            self.drag_start_y = event.ydata
            self.original_xlim = event.inaxes.get_xlim()
            self.original_ylim = event.inaxes.get_ylim()
            
        elif mode == '선택' and self.data is not None and event.button == 1:
            # 선택 모드 - 클릭한 지점의 데이터 표시
            self.on_canvas_click(event)
    
    def on_canvas_release(self, event):
        """캔버스 마우스 놓음 이벤트"""
        if event.button == 2:  # 가운데 버튼
            self.middle_button_pressed = False
            self.last_mouse_pos = None
            
        if self.is_dragging:
            self.is_dragging = False
            self.drag_start_x = None
            self.drag_start_y = None
            self.original_xlim = None
            self.original_ylim = None
    
    def on_canvas_motion(self, event):
        """캔버스 마우스 이동 이벤트"""
        # 커서 십자선 업데이트
        self.update_crosshair(event)
        
        if event.inaxes is None:
            return
        
        mode = self.mouse_mode_combo.currentText()
        
        # 마우스 가운데 버튼 드래그
        if self.middle_button_pressed and self.last_mouse_pos:
            if event.xdata and event.ydata:
                dx = self.last_mouse_pos[0] - event.xdata
                dy = self.last_mouse_pos[1] - event.ydata
                
                # 새로운 축 범위 계산
                new_xlim = (self.original_xlim[0] + dx, self.original_xlim[1] + dx)
                new_ylim = (self.original_ylim[0] + dy, self.original_ylim[1] + dy)
                
                # 축 범위 적용
                event.inaxes.set_xlim(new_xlim)
                event.inaxes.set_ylim(new_ylim)
                self.main_canvas.draw_idle()
        
        # 왼쪽 버튼 드래그 (드래그 이동 모드)
        elif self.is_dragging and mode == '드래그 이동':
            if self.drag_start_x is not None and self.drag_start_y is not None:
                dx = self.drag_start_x - event.xdata
                dy = self.drag_start_y - event.ydata
                
                # 새로운 축 범위 계산
                new_xlim = (self.original_xlim[0] + dx, self.original_xlim[1] + dx)
                new_ylim = (self.original_ylim[0] + dy, self.original_ylim[1] + dy)
                
                # 축 범위 적용
                event.inaxes.set_xlim(new_xlim)
                event.inaxes.set_ylim(new_ylim)
                self.main_canvas.draw_idle()
    
    def apply_grid_settings(self, ax):
        """격자 설정 적용 (개선된 버전)"""
        if self.show_grid_check.isChecked():
            # 주 격자
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5, which='major')
            
            if self.show_minor_grid_check.isChecked():
                # 부 격자
                ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.3)
                ax.minorticks_on()
            
            # 격자 스타일 개선
            ax.tick_params(which='major', length=6, width=1.2)
            ax.tick_params(which='minor', length=3, width=0.8)
        else:
            ax.grid(False)
            ax.minorticks_off()
    
    def setup_crosshair(self, ax):
        """커서 십자선 및 정보 표시 설정"""
        # 십자선 생성 (초기에는 보이지 않음)
        self.crosshair_lines = {
            'vline': ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, visible=False),
            'hline': ax.axhline(y=0, color='red', linestyle='--', alpha=0.7, visible=False)
        }
        
        # 커서 정보 텍스트 생성 (우상단에 표시)
        self.cursor_info_text = ax.text(0.98, 0.98, '', 
                                       transform=ax.transAxes, 
                                       fontsize=10,
                                       verticalalignment='top',
                                       horizontalalignment='right',
                                       bbox=dict(boxstyle='round,pad=0.3', 
                                               facecolor='white', 
                                               alpha=0.8,
                                               edgecolor='gray'),
                                       fontfamily=self.korean_font if self.korean_font else 'sans-serif',
                                       visible=False)
    
    def zoom_in(self):
        """확대"""
        for ax in self.main_figure.get_axes():
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            
            x_center = sum(xlim) / 2
            y_center = sum(ylim) / 2
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            ax.set_xlim(x_center - x_range*0.4, x_center + x_range*0.4)
            ax.set_ylim(y_center - y_range*0.4, y_center + y_range*0.4)
        
        self.main_canvas.draw()
    
    def zoom_out(self):
        """축소"""
        for ax in self.main_figure.get_axes():
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            
            x_center = sum(xlim) / 2
            y_center = sum(ylim) / 2
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            ax.set_xlim(x_center - x_range*0.75, x_center + x_range*0.75)
            ax.set_ylim(y_center - y_range*0.75, y_center + y_range*0.75)
        
        self.main_canvas.draw()
    
    def reset_zoom(self):
        """줌 리셋"""
        for ax in self.main_figure.get_axes():
            ax.relim()
            ax.autoscale()
        
        self.main_canvas.draw()
    
    def save_report(self):
        """분석 보고서 저장"""
        if self.data is None:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            '분석 보고서 저장',
            f'battery_analysis_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html',
            'HTML files (*.html);;PDF files (*.pdf);;All files (*.*)'
        )
        
        if file_path:
            try:
                if file_path.endswith('.html'):
                    self.save_html_report(file_path)
                elif file_path.endswith('.pdf'):
                    self.save_pdf_report(file_path)
                
                QMessageBox.information(self, '성공', f'보고서가 저장되었습니다:\n{file_path}')
                
            except Exception as e:
                QMessageBox.critical(self, '오류', f'보고서 저장 중 오류:\n{str(e)}')
    
    def save_html_report(self, file_path):
        """HTML 보고서 저장 (그래프 포함, 확장된 진단 정보)"""
        import base64
        from io import BytesIO
        
        stats = self.analysis_results.get('statistics', {})
        
        # 파일명 처리 - file_path가 None인 경우 대비
        if self.file_path:
            report_filename = os.path.basename(self.file_path)
        elif self.file_paths:
            if len(self.file_paths) == 1:
                report_filename = os.path.basename(self.file_paths[0])
            else:
                report_filename = f"{len(self.file_paths)}개 파일 비교 분석"
        else:
            report_filename = "배터리 로그 분석"
        
        # 모든 그래프를 이미지로 변환
        main_graph_img = self.figure_to_base64(self.main_figure)
        detail_graph_img = self.figure_to_base64(self.detail_figure)
        performance_graph_img = self.figure_to_base64(self.performance_figure)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>배터리 로그 분석 보고서</title>
    <style>
        body {{ 
            font-family: 'Malgun Gothic', Arial, sans-serif; 
            margin: 20px; 
            line-height: 1.6;
            background-color: #f9f9f9;
        }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px;
            text-align: center;
        }}
        .section {{ 
            background: white;
            margin: 30px 0; 
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stats-table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 15px 0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .stats-table th, .stats-table td {{ 
            border: 1px solid #e0e0e0; 
            padding: 15px; 
            text-align: left; 
        }}
        .stats-table th {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
        }}
        .stats-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .graph-container {{
            text-align: center;
            margin: 25px 0;
            padding: 20px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }}
        .graph-title {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #495057;
        }}
        .graph-img {{
            max-width: 100%;
            height: auto;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        h1 {{ color: white; margin: 0; font-size: 2.5em; }}
        h2 {{ 
            color: #495057; 
            border-bottom: 3px solid #667eea; 
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        .summary-card {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        .summary-card h3 {{
            margin: 0 0 15px 0;
            color: #667eea;
            font-size: 1.3em;
        }}
        .diagnostic-section {{
            background: linear-gradient(135deg, #ffefd5 0%, #ffebcd 100%);
            border-left: 5px solid #ff8c00;
        }}
        .performance-section {{
            background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
            border-left: 5px solid #28a745;
        }}
        .risk-section {{
            background: linear-gradient(135deg, #ffe6e6 0%, #ffcccc 100%);
            border-left: 5px solid #dc3545;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
            margin: 2px;
        }}
        .status-good {{ background-color: #d4edda; color: #155724; }}
        .status-warning {{ background-color: #fff3cd; color: #856404; }}
        .status-danger {{ background-color: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔋 배터리 로그 분석 보고서</h1>
        <p style="font-size: 1.2em; margin: 10px 0;"><strong>생성일시:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}</p>
        <p style="font-size: 1.1em;"><strong>분석 파일:</strong> {report_filename}</p>
        <p><strong>분석 프로그램:</strong> OnBoard 배터리 로그 분석기 v2.1</p>
    </div>
    
    <div class="section">
        <h2>📊 데이터 요약</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>📈 데이터 규모</h3>
                <p><strong>총 데이터 포인트:</strong> {len(self.data):,}개</p>
                <p><strong>측정 기간:</strong> {str(self.data['timestamp'].max() - self.data['timestamp'].min()).split('.')[0]}</p>
            </div>
            <div class="summary-card">
                <h3>⏰ 시간 정보</h3>
                <p><strong>시작:</strong> {self.data['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>종료:</strong> {self.data['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="summary-card">
                <h3>⚡ 전압 정보</h3>
                <p><strong>범위:</strong> {self.data['battery'].min():.3f}V ~ {self.data['battery'].max():.3f}V</p>
                <p><strong>평균:</strong> {self.data['battery'].mean():.3f}V</p>
                <p><strong>표준편차:</strong> {self.data['battery'].std():.3f}V</p>
            </div>
        </div>
    </div>
"""
        
        # 종합 진단 섹션
        if 'diagnostic' in self.analysis_results:
            diagnostic_info = self.analysis_results['diagnostic']
            html_content += f"""
    <div class="section diagnostic-section">
        <h2>🔬 종합 배터리 진단</h2>
        <table class="stats-table">
            <thead>
                <tr><th>진단 항목</th><th>결과</th></tr>
            </thead>
            <tbody>
"""
            for key, value in diagnostic_info.items():
                html_content += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # 성능 평가 섹션
        if 'performance' in self.analysis_results:
            performance_info = self.analysis_results['performance']
            html_content += f"""
    <div class="section performance-section">
        <h2>⚡ 성능 평가</h2>
        <table class="stats-table">
            <thead>
                <tr><th>성능 항목</th><th>평가 결과</th></tr>
            </thead>
            <tbody>
"""
            for key, value in performance_info.items():
                html_content += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # 위험 평가 섹션
        if 'risk_assessment' in self.analysis_results:
            risk_info = self.analysis_results['risk_assessment']
            html_content += f"""
    <div class="section risk-section">
        <h2>⚠️ 위험 평가</h2>
        <table class="stats-table">
            <thead>
                <tr><th>위험 요소</th><th>평가 결과</th></tr>
            </thead>
            <tbody>
"""
            for key, value in risk_info.items():
                # 위험도에 따른 뱃지 스타일 적용
                if '낮음' in str(value):
                    badge_class = 'status-good'
                elif '보통' in str(value):
                    badge_class = 'status-warning'
                else:
                    badge_class = 'status-danger'
                
                html_content += f'                <tr><td>{key}</td><td><span class="status-badge {badge_class}">{value}</span></td></tr>\n'
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # 그래프 섹션들
        html_content += f"""
    <div class="section">
        <h2>📈 메인 그래프</h2>
        <div class="graph-container">
            <div class="graph-title">배터리 전압 시계열 분석</div>
            <img src="data:image/png;base64,{main_graph_img}" alt="메인 그래프" class="graph-img">
        </div>
    </div>
    
    <div class="section">
        <h2>🔍 상세 분석 그래프</h2>
        <div class="graph-container">
            <div class="graph-title">이동평균, 변화율, 이상치, 주기성 분석</div>
            <img src="data:image/png;base64,{detail_graph_img}" alt="상세 분석 그래프" class="graph-img">
        </div>
    </div>
    
    <div class="section">
        <h2>⚡ 성능 지표 그래프</h2>
        <div class="graph-container">
            <div class="graph-title">전압 안정성, 용량 트렌드, 효율성, 건강도</div>
            <img src="data:image/png;base64,{performance_graph_img}" alt="성능 지표 그래프" class="graph-img">
        </div>
    </div>
    
    <div class="section">
        <h2>📋 상세 통계 정보</h2>
        <table class="stats-table">
            <thead>
                <tr><th>통계 항목</th><th>값</th></tr>
            </thead>
            <tbody>
"""
        
        for key, value in stats.items():
            html_content += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
        
        # 배터리 건강도
        if 'health' in self.analysis_results:
            health_info = self.analysis_results['health']
            html_content += """
            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>🏥 배터리 건강도 평가</h2>
        <table class="stats-table">
            <thead>
                <tr><th>평가 항목</th><th>결과</th></tr>
            </thead>
            <tbody>
"""
            for key, value in health_info.items():
                html_content += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
        
        # 이상치 정보
        if 'anomalies' in self.analysis_results:
            anomalies = self.analysis_results['anomalies']
            html_content += f"""
            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>⚠️ 이상치 분석</h2>
        <div class="summary-card">
            <h3>이상치 검출 결과</h3>
            <p><strong>총 이상치 개수:</strong> {len(anomalies)}개</p>
            <p><strong>전체 데이터 대비:</strong> {len(anomalies)/len(self.data)*100:.2f}%</p>
            <p><strong>데이터 품질:</strong> {"우수" if len(anomalies)/len(self.data) < 0.05 else "양호" if len(anomalies)/len(self.data) < 0.1 else "주의"}</p>
        </div>
    </div>
    
    <div class="section">
        <h2>📝 종합 분석 결과</h2>
        <div class="summary-card">
            <h3>주요 발견사항</h3>
            <ul>
                <li><strong>평균 배터리 전압:</strong> {self.data['battery'].mean():.3f}V</li>
                <li><strong>전압 변동 범위:</strong> {self.data['battery'].max() - self.data['battery'].min():.3f}V</li>
                <li><strong>데이터 안정성:</strong> {"높음" if self.data['battery'].std() < 0.1 else "보통" if self.data['battery'].std() < 0.2 else "낮음"}</li>
                <li><strong>이상치 비율:</strong> {len(anomalies)/len(self.data)*100:.2f}%</li>
                <li><strong>측정 품질:</strong> {"고품질" if len(self.data) > 1000 else "표준" if len(self.data) > 100 else "제한적"}</li>
            </ul>
        </div>
"""
        
        # 권장사항 추가
        html_content += """
        <div class="summary-card">
            <h3>권장사항</h3>
            <ul>
"""
        
        # 데이터 기반 권장사항 생성
        std_ratio = self.data['battery'].std() / self.data['battery'].mean()
        if std_ratio > 0.05:
            html_content += "<li>전압 변동이 큽니다. 배터리 상태를 점검하세요.</li>"
        
        if len(anomalies) / len(self.data) > 0.1:
            html_content += "<li>이상치가 많이 감지되었습니다. 시스템 점검이 필요합니다.</li>"
        
        html_content += """
                <li>정기적인 배터리 상태 모니터링을 권장합니다.</li>
                <li>이 보고서를 참고하여 예방적 유지보수를 계획하세요.</li>
            </ul>
        </div>
    </div>
    
    <footer style="margin-top: 50px; padding: 30px; border-top: 2px solid #667eea; text-align: center; color: #6c757d; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
        <p style="font-size: 1.1em;"><strong>이 보고서는 OnBoard  배터리 로그 분석기 v2.0에서 자동 생성되었습니다.</strong></p>
        <p>생성 시간: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        <p style="font-size: 0.9em; color: #868e96;">⚡ STM32L412 OnBoard 시스템 전용 분석 도구</p>
    </footer>
</body>
</html>
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def figure_to_base64(self, figure):
        """Figure를 base64 문자열로 변환"""
        from io import BytesIO
        import base64
        
        # Figure를 PNG로 저장
        buffer = BytesIO()
        figure.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                      facecolor='white', edgecolor='none')
        buffer.seek(0)
        
        # base64로 인코딩
        img_data = buffer.getvalue()
        img_base64 = base64.b64encode(img_data).decode()
        buffer.close()
        
        return img_base64
    
    def save_pdf_report(self, file_path):
        """PDF 보고서 저장 (개선된 버전)"""
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        
        with PdfPages(file_path) as pdf:
            # 표지 페이지
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis('off')
            
            # 제목 및 정보
            ax.text(0.5, 0.8, '배터리 로그 분석 보고서', 
                   fontsize=24, fontweight='bold', ha='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            
            ax.text(0.5, 0.7, f'분석 파일: {os.path.basename(self.file_path)}', 
                   fontsize=14, ha='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            
            ax.text(0.5, 0.65, f'생성일시: {datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")}', 
                   fontsize=12, ha='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            
            # 요약 정보
            summary_text = f"""
데이터 포인트: {len(self.data):,}개
시간 범위: {self.data['timestamp'].min()} ~ {self.data['timestamp'].max()}
평균 전압: {self.data['battery'].mean():.3f}V
전압 범위: {self.data['battery'].min():.3f}V ~ {self.data['battery'].max():.3f}V
"""
            ax.text(0.5, 0.4, summary_text, 
                   fontsize=12, ha='center', va='top',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            
            # 메인 그래프 페이지
            pdf.savefig(self.main_figure, bbox_inches='tight')
            
            # 상세 분석 그래프 페이지
            if hasattr(self, 'detail_figure'):
                pdf.savefig(self.detail_figure, bbox_inches='tight')
    
    def on_canvas_scroll(self, event):
        """마우스 휠 스크롤 이벤트"""
        if event.inaxes is None:
            return
        
        # 휠 스크롤로 확대/축소
        base_scale = 1.1
        if event.button == 'up':
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            return
        
        ax = event.inaxes
        
        # 마우스 위치를 중심으로 확대/축소
        x_center = event.xdata
        y_center = event.ydata
        
        if x_center is not None and y_center is not None:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            new_x_range = x_range * scale_factor
            new_y_range = y_range * scale_factor
            
            new_xlim = (x_center - new_x_range/2, x_center + new_x_range/2)
            new_ylim = (y_center - new_y_range/2, y_center + new_y_range/2)
            
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            self.main_canvas.draw_idle()
    
    def change_mouse_mode(self):
        """마우스 모드 변경"""
        mode = self.mouse_mode_combo.currentText()
        
        # 기존 SpanSelector 제거
        if self.span_selector:
            self.span_selector.set_active(False)
            self.span_selector = None
        
        if mode == '구간 선택' and self.data is not None:
            # 시간 범위 선택을 위한 SpanSelector 활성화
            ax = self.main_figure.gca()
            if ax:
                self.span_selector = SpanSelector(
                    ax, 
                    self.on_span_select,
                    'horizontal',
                    useblit=True,
                    props=dict(alpha=0.3, facecolor='yellow'),
                    interactive=True
                )
                self.statusBar().showMessage('드래그하여 시간 범위를 선택하세요.')
        
        elif mode == '드래그 이동':
            self.statusBar().showMessage('왼쪽 버튼 또는 가운데 버튼으로 드래그하여 그래프를 이동하세요.')
        else:
            self.statusBar().showMessage('클릭하여 데이터 포인트를 선택하세요.')
    
    def on_span_select(self, xmin, xmax):
        """시간 범위 선택 콜백 (timezone 오류 수정)"""
        current_data = self.get_current_data()
        if current_data is None:
            return
        
        try:
            # 시간 축 타입에 따른 변환
            time_option = self.time_display_combo.currentText()
            
            if time_option == '절대시간':
                # 선택된 시간 범위의 데이터 필터링
                start_time = mdates.num2date(xmin)
                end_time = mdates.num2date(xmax)
                
                # timezone 정보 제거
                if start_time.tzinfo is not None:
                    start_time = start_time.replace(tzinfo=None)
                if end_time.tzinfo is not None:
                    end_time = end_time.replace(tzinfo=None)
            else:
                # 상대시간인 경우 원래 타임스탬프로 변환
                start_time_ref = current_data['timestamp'].min()
                
                if time_option == '상대시간(시작점 기준)':
                    start_time = start_time_ref + timedelta(seconds=xmin)
                    end_time = start_time_ref + timedelta(seconds=xmax)
                elif time_option == '경과시간(분)':
                    start_time = start_time_ref + timedelta(minutes=xmin)
                    end_time = start_time_ref + timedelta(minutes=xmax)
                elif time_option == '경과시간(시간)':
                    start_time = start_time_ref + timedelta(hours=xmin)
                    end_time = start_time_ref + timedelta(hours=xmax)
                else:
                    return
            
            filtered_data = current_data[
                (current_data['timestamp'] >= start_time) & 
                (current_data['timestamp'] <= end_time)
            ]
            
            if len(filtered_data) > 0:
                # 선택된 구간 정보 저장
                self.current_selection = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'data': filtered_data
                }
                
                # 선택된 구간 정보 업데이트
                self.update_span_selection_info(filtered_data, start_time, end_time)
                self.statusBar().showMessage(
                    f'선택된 구간: {len(filtered_data)}개 포인트 '
                    f'({start_time.strftime("%H:%M:%S")} ~ {end_time.strftime("%H:%M:%S")})'
                )
                
                # 그래프 업데이트 (선택 구간 표시)
                self.update_main_graph()
        except Exception as e:
            print(f"구간 선택 오류: {e}")
            self.statusBar().showMessage(f'구간 선택 중 오류가 발생했습니다: {str(e)}')
    
    def update_span_selection_info(self, data, start_time, end_time):
        """구간 선택 정보 업데이트"""
        duration = end_time - start_time
        voltage_change = data['battery'].iloc[-1] - data['battery'].iloc[0]
        avg_voltage = data['battery'].mean()
        
        # OnBoard 로그 특화 정보
        onboard_info = ""
        if self.is_onboard_log():
            if 'status' in data.columns:
                standby_ratio = (data['status'] == 'STANDBY').sum() / len(data) * 100
                onboard_info += f"\n• STANDBY 비율: {standby_ratio:.1f}%"
            
            if 'L1' in data.columns and 'L2' in data.columns:
                normal_led = ((data['L1'] == 'X') & (data['L2'] == 'X')).sum() / len(data) * 100
                onboard_info += f"\n• 정상 LED 상태: {normal_led:.1f}%"
        
        info_text = f"""
선택된 구간 분석:
시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
구간 길이: {str(duration).split('.')[0]}

전압 정보:
• 시작 전압: {data['battery'].iloc[0]:.3f}V
• 종료 전압: {data['battery'].iloc[-1]:.3f}V
• 평균 전압: {avg_voltage:.3f}V
• 전압 변화: {voltage_change:+.3f}V
• 최소 전압: {data['battery'].min():.3f}V
• 최대 전압: {data['battery'].max():.3f}V
• 표준편차: {data['battery'].std():.3f}V

데이터 포인트: {len(data)}개{onboard_info}
"""
        self.selection_info.setText(info_text.strip())
    
    def update_selection_info(self, point):
        """선택된 포인트 정보 업데이트"""
        # OnBoard 로그 특화 정보
        onboard_info = ""
        if self.is_onboard_log():
            if 'status' in point:
                onboard_info += f"\n상태: {point['status']}"
            if 'L1' in point and 'L2' in point:
                onboard_info += f"\nLED: L1={point['L1']}, L2={point['L2']}"
            if 'memo' in point:
                onboard_info += f"\n메모: {point['memo']}"
        
        info_text = f"""
선택된 시점: {point['timestamp']}
배터리 전압: {point['battery']:.3f}V{onboard_info}

주변 데이터 분석:
• 5분 전 평균: {self.get_nearby_average(point['timestamp'], -5):.3f}V
• 5분 후 평균: {self.get_nearby_average(point['timestamp'], 5):.3f}V
• 변화율: {self.get_change_rate_at(point['timestamp']):.2f}%/분
"""
        self.selection_info.setText(info_text.strip())
    
    def get_nearby_average(self, timestamp, minutes_offset):
        """특정 시점 주변의 평균값 계산"""
        current_data = self.get_current_data()
        if current_data is None:
            return 0
        
        target_time = timestamp + timedelta(minutes=minutes_offset)
        nearby_data = current_data[
            abs(current_data['timestamp'] - target_time) <= timedelta(minutes=2)
        ]
        return nearby_data['battery'].mean() if len(nearby_data) > 0 else 0
    
    def get_change_rate_at(self, timestamp):
        """특정 시점의 변화율 계산"""
        current_data = self.get_current_data()
        if current_data is None:
            return 0
        
        idx = current_data[current_data['timestamp'] == timestamp].index
        if len(idx) > 0 and idx[0] > 0:
            current_val = current_data.loc[idx[0], 'battery']
            prev_val = current_data.loc[idx[0]-1, 'battery']
            return ((current_val - prev_val) / prev_val) * 100
        return 0
    
    def on_analysis_option_changed(self):
        """분석 옵션 변경 시 즉시 적용 (최적화 및 응답성 개선)"""
        if not hasattr(self, '_update_timer'):
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._delayed_update_graphs)
        
        # 기존 타이머 정지 (중복 업데이트 방지)
        self._update_timer.stop()
        
        # 데이터 유효성 검사
        if self.data is None and not self.multiple_data:
            return
        
        try:
            # 즉시 적용 가능한 변경사항 (격자 등)
            self._apply_immediate_changes()
            
            # 무거운 작업은 지연 실행 (50ms 후)
            self._update_timer.start(50)
            
        except Exception as e:
            print(f"분석 옵션 변경 오류: {e}")
            # 오류 시 상태바에 메시지 표시
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'옵션 변경 오류: {str(e)}', 3000)
    
    def _apply_immediate_changes(self):
        """즉시 적용 가능한 UI 변경사항"""
        try:
            # 격자 설정만 즉시 적용 (빠른 업데이트)
            if hasattr(self, 'main_figure') and self.main_figure.get_axes():
                for ax in self.main_figure.get_axes():
                    self.apply_grid_settings(ax)
                
                # 캔버스 빠른 새로고침
                if hasattr(self, 'main_canvas'):
                    self.main_canvas.draw_idle()
        except Exception as e:
            print(f"즉시 변경사항 적용 오류: {e}")
    
    def _delayed_update_graphs(self):
        """지연된 그래프 업데이트 (무거운 작업)"""
        try:
            # 현재 상태 확인
            if self.data is None and not self.multiple_data:
                return
            
            # 비교 모드와 단일 모드 구분하여 업데이트
            if self.comparison_mode and self.multiple_data:
                # 비교 모드: 메인 그래프만 업데이트 (성능 최적화)
                self._update_comparison_main_only()
            else:
                # 단일 모드: 메인 그래프만 업데이트
                self._update_single_main_only()
            
            # 상태바 업데이트
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage('분석 옵션이 적용되었습니다.', 2000)
                
        except Exception as e:
            print(f"지연 그래프 업데이트 오류: {e}")
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'그래프 업데이트 실패: {str(e)}', 3000)
    
    def _update_comparison_main_only(self):
        """비교 모드에서 메인 그래프만 업데이트 (최적화)"""
        try:
            self.main_figure.clear()
            self.create_comparison_time_series()
            if hasattr(self, 'main_canvas'):
                self.main_canvas.draw_idle()
        except Exception as e:
            print(f"비교 모드 메인 그래프 업데이트 오류: {e}")
    
    def _update_single_main_only(self):
        """단일 모드에서 메인 그래프만 업데이트 (최적화)"""
        try:
            self.main_figure.clear()
            
            # 현재 그래프 타입에 따라 분기
            graph_type = self.graph_type_combo.currentText()
            
            if graph_type == '시계열':
                self.plot_time_series()
            elif graph_type == '히스토그램':
                self.plot_histogram()
            elif graph_type == '박스플롯':
                self.plot_boxplot()
            elif graph_type == '산점도':
                self.plot_scatter()
            
            if hasattr(self, 'main_canvas'):
                self.main_canvas.draw_idle()
                
        except Exception as e:
            print(f"단일 모드 메인 그래프 업데이트 오류: {e}")
    
    def clear_selection(self):
        """선택 구간 초기화"""
        self.current_selection = None
        self.selection_info.clear()
        self.selection_info.setText("선택된 구간이 없습니다.\n구간 선택 모드에서 드래그하여 구간을 선택하세요.")
        self.statusBar().showMessage('선택 구간이 초기화되었습니다.')
        
        # 그래프에서 선택 표시 제거
        if hasattr(self, 'main_canvas'):
            # 전체 업데이트 대신 빠른 업데이트 사용
            if hasattr(self, '_delayed_update_graphs'):
                self._delayed_update_graphs()
            else:
                self.update_main_graph()
    
    def on_canvas_click(self, event):
        """캔버스 클릭 이벤트 처리 (데이터 포인트 선택)"""
        if event.inaxes is None or self.data is None:
            return
        
        try:
            current_data = self.get_current_data()
            if current_data is None or len(current_data) == 0:
                return
            
            time_option = self.time_display_combo.currentText()
            
            if time_option == '절대시간':
                # 클릭한 시간을 matplotlib의 날짜 형식에서 변환
                clicked_time = mdates.num2date(event.xdata)
                
                # timezone 정보 제거
                if clicked_time.tzinfo is not None:
                    clicked_time = clicked_time.replace(tzinfo=None)
                
                # 가장 가까운 데이터 포인트 찾기
                time_diffs = abs(current_data['timestamp'] - clicked_time)
                closest_idx = time_diffs.idxmin()
            else:
                # 상대시간인 경우 인덱스 기반으로 선택
                click_x = event.xdata
                start_time = current_data['timestamp'].min()
                
                if time_option == '상대시간(시작점 기준)':
                    target_time = start_time + timedelta(seconds=click_x)
                elif time_option == '경과시간(분)':
                    target_time = start_time + timedelta(minutes=click_x)
                elif time_option == '경과시간(시간)':
                    target_time = start_time + timedelta(hours=click_x)
                else:
                    return
                
                # 가장 가까운 데이터 포인트 찾기
                time_diffs = abs(current_data['timestamp'] - target_time)
                closest_idx = time_diffs.idxmin()
            
            # 선택된 포인트 정보 업데이트
            selected_point = current_data.loc[closest_idx]
            self.update_selection_info(selected_point)
            
            # 상태바에 정보 표시
            self.statusBar().showMessage(
                f'선택된 시점: {selected_point["timestamp"].strftime("%H:%M:%S")}, '
                f'전압: {selected_point["battery"]:.3f}V'
            )
            
        except Exception as e:
            print(f"클릭 이벤트 처리 오류: {e}")
            # 예외 발생 시 인덱스 기반으로 대체
            try:
                # 클릭 위치를 기반으로 대략적인 인덱스 계산
                if hasattr(event, 'xdata') and event.xdata is not None:
                    data_len = len(current_data)
                    approx_idx = min(int(event.xdata * data_len / data_len), data_len - 1)
                    selected_point = current_data.iloc[approx_idx]
                    self.update_selection_info(selected_point)
            except:
                self.statusBar().showMessage('데이터 포인트 선택 중 오류가 발생했습니다.')
    
    def update_crosshair(self, event):
        """마우스 위치에 따른 십자선 및 정보 표시 업데이트"""
        if (event.inaxes is None or 
            not hasattr(self, 'crosshair_lines') or 
            self.crosshair_lines is None):
            return
        
        # 커서 정보 표시가 비활성화된 경우
        if not hasattr(self, 'show_cursor_info_check') or not self.show_cursor_info_check.isChecked():
            # 십자선과 정보 텍스트 숨기기
            if self.crosshair_lines:
                self.crosshair_lines['vline'].set_visible(False)
                self.crosshair_lines['hline'].set_visible(False)
            if hasattr(self, 'cursor_info_text') and self.cursor_info_text:
                self.cursor_info_text.set_visible(False)
            return
        
        # 커서 정보 텍스트가 없는 경우 건너뛰기
        if not hasattr(self, 'cursor_info_text') or self.cursor_info_text is None:
            return
        
        try:
            # 십자선 및 정보 표시
            if event.xdata is not None and event.ydata is not None:
                # 십자선 위치 업데이트
                self.crosshair_lines['vline'].set_xdata([event.xdata])
                self.crosshair_lines['hline'].set_ydata([event.ydata])
                self.crosshair_lines['vline'].set_visible(True)
                self.crosshair_lines['hline'].set_visible(True)
                
                # 커서 정보 텍스트 업데이트
                info_text = self.get_cursor_info_text(event.xdata, event.ydata)
                self.cursor_info_text.set_text(info_text)
                self.cursor_info_text.set_visible(True)
                
                # 캔버스 업데이트 (blitting 사용 시 더 빠름)
                if hasattr(self.main_canvas, 'draw_idle'):
                    self.main_canvas.draw_idle()
            else:
                # 마우스가 그래프 영역을 벗어났을 때 십자선과 정보 숨기기
                self.crosshair_lines['vline'].set_visible(False)
                self.crosshair_lines['hline'].set_visible(False)
                self.cursor_info_text.set_visible(False)
                self.main_canvas.draw_idle()
        except Exception as e:
            # 십자선 업데이트 실패 시 무시 (성능상 중요하지 않음)
            pass
    
    def get_cursor_info_text(self, x_pos, y_pos):
        """커서 위치에 대한 정보 텍스트 생성"""
        try:
            current_data = self.get_current_data()
            if current_data is None or len(current_data) == 0:
                return f"전압: {y_pos:.3f}V"
            
            time_option = self.time_display_combo.currentText()
            
            # 시간 정보 변환
            if time_option == '절대시간':
                try:
                    # matplotlib 날짜 형식에서 실제 시간으로 변환
                    time_val = mdates.num2date(x_pos)
                    if time_val.tzinfo is not None:
                        time_val = time_val.replace(tzinfo=None)
                    time_str = time_val.strftime('%H:%M:%S')
                except:
                    time_str = f"X: {x_pos:.2f}"
            elif time_option == '상대시간(시작점 기준)':
                time_str = f"{x_pos:.1f}초"
            elif time_option == '경과시간(분)':
                time_str = f"{x_pos:.1f}분"
            elif time_option == '경과시간(시간)':
                time_str = f"{x_pos:.2f}시간"
            else:
                time_str = f"X: {x_pos:.2f}"
            
            # 가장 가까운 데이터 포인트 찾기
            closest_info = self.find_closest_data_point(x_pos, current_data)
            
            if closest_info:
                # 실제 데이터 포인트 정보 표시
                info_text = f"시간: {time_str}\n전압: {y_pos:.3f}V\n\n[가장 가까운 데이터]\n"
                info_text += f"시간: {closest_info['time_str']}\n"
                info_text += f"전압: {closest_info['voltage']:.3f}V"
                
                # OnBoard 로그인 경우 추가 정보
                if self.is_onboard_log() and closest_info['extra_info']:
                    info_text += f"\n상태: {closest_info['extra_info'].get('status', 'N/A')}"
                    if 'L1' in closest_info['extra_info'] and 'L2' in closest_info['extra_info']:
                        info_text += f"\nLED: {closest_info['extra_info']['L1']},{closest_info['extra_info']['L2']}"
                
                return info_text
            else:
                return f"시간: {time_str}\n전압: {y_pos:.3f}V"
                
        except Exception as e:
            # 오류 발생 시 기본 정보만 표시
            return f"전압: {y_pos:.3f}V"
    
    def find_closest_data_point(self, x_pos, data):
        """커서 위치에 가장 가까운 데이터 포인트 찾기"""
        try:
            time_option = self.time_display_combo.currentText()
            
            if time_option == '절대시간':
                try:
                    # matplotlib 날짜에서 실제 시간으로 변환
                    target_time = mdates.num2date(x_pos)
                    if target_time.tzinfo is not None:
                        target_time = target_time.replace(tzinfo=None)
                    
                    # 가장 가까운 시간 찾기
                    time_diffs = abs(data['timestamp'] - target_time)
                    closest_idx = time_diffs.idxmin()
                    
                except:
                    # 변환 실패 시 인덱스 기반
                    closest_idx = data.index[min(len(data)-1, max(0, int(x_pos)))]
            else:
                # 상대시간인 경우
                start_time = data['timestamp'].min()
                
                if time_option == '상대시간(시작점 기준)':
                    target_time = start_time + pd.Timedelta(seconds=x_pos)
                elif time_option == '경과시간(분)':
                    target_time = start_time + pd.Timedelta(minutes=x_pos)
                elif time_option == '경과시간(시간)':
                    target_time = start_time + pd.Timedelta(hours=x_pos)
                else:
                    return None
                
                # 가장 가까운 시간 찾기
                time_diffs = abs(data['timestamp'] - target_time)
                closest_idx = time_diffs.idxmin()
            
            # 가장 가까운 데이터 포인트 정보 반환
            closest_point = data.loc[closest_idx]
            
            result = {
                'time_str': closest_point['timestamp'].strftime('%H:%M:%S'),
                'voltage': closest_point['battery'],
                'extra_info': {}
            }
            
            # OnBoard 로그 추가 정보
            if self.is_onboard_log():
                for col in ['status', 'L1', 'L2', 'memo']:
                    if col in closest_point:
                        result['extra_info'][col] = closest_point[col]
            
            return result
            
        except Exception as e:
            print(f"가장 가까운 데이터 포인트 찾기 오류: {e}")
            return None
    
    def select_single_file(self):
        """단일 파일 선택 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '배터리 로그 파일 선택',
            '',
            'Log files (*.log *.txt *.csv);;All files (*.*)'
        )
        
        if file_path:
            # 기존 데이터 초기화
            self.multiple_data.clear()
            self.file_path = file_path  # 단일 파일 경로 설정
            self.file_paths = [file_path]
            self.selected_files = [file_path]
            self.comparison_mode = False
            self.comparison_mode_check.setChecked(False)
            
            # UI 업데이트
            self.file_info_label.setText(f'선택된 파일: {os.path.basename(file_path)}')
            self.analyze_btn.setEnabled(True)
            self.statusBar().showMessage(f'파일 선택됨: {os.path.basename(file_path)}')
            self.update_file_list_display()
    
    def select_multiple_files(self):
        """다중 파일 선택 다이얼로그"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            '배터리 로그 파일들 선택 (비교 분석용)',
            '',
            'Log files (*.log *.txt *.csv);;All files (*.*)'
        )
        
        if file_paths:
            self.file_paths = file_paths
            self.selected_files = file_paths.copy()
            self.comparison_mode = True
            self.comparison_mode_check.setChecked(True)
            
            # UI 업데이트
            file_count = len(file_paths)
            self.file_info_label.setText(f'선택된 파일: {file_count}개')
            self.analyze_btn.setEnabled(True)
            self.statusBar().showMessage(f'{file_count}개 파일 선택됨 - 비교 모드 활성화')
            self.update_file_list_display()
    
    def update_file_list_display(self):
        """파일 목록 표시 업데이트"""
        # 기존 위젯들 제거
        layout = self.file_list_widget.layout()
        for i in reversed(range(layout.count())):
            child = layout.takeAt(i).widget()
            if child:
                child.setParent(None)
        
        # 파일별 체크박스와 정보 추가
        for i, file_path in enumerate(self.file_paths):
            file_widget = QWidget()
            file_layout = QHBoxLayout(file_widget)
            file_layout.setContentsMargins(5, 2, 5, 2)
            
            # 체크박스
            checkbox = QCheckBox()
            checkbox.setChecked(file_path in self.selected_files)
            checkbox.toggled.connect(lambda checked, path=file_path: self.toggle_file_selection(path, checked))
            file_layout.addWidget(checkbox)
            
            # 파일명 라벨
            filename = os.path.basename(file_path)
            file_label = QLabel(filename)
            file_label.setToolTip(file_path)
            
            # 파일별 색상 표시 (최대 10개 파일)
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
                     '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']
            if i < len(colors):
                color = colors[i]
                file_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            
            file_layout.addWidget(file_label)
            file_layout.addStretch()
            
            # 제거 버튼
            remove_btn = QPushButton('×')
            remove_btn.setMaximumSize(20, 20)
            remove_btn.clicked.connect(lambda _, path=file_path: self.remove_file(path))
            file_layout.addWidget(remove_btn)
            
            layout.addWidget(file_widget)
        
        # 빈 공간 추가
        layout.addStretch()
    
    def toggle_file_selection(self, file_path, checked):
        """파일 선택/해제 토글"""
        if checked and file_path not in self.selected_files:
            self.selected_files.append(file_path)
        elif not checked and file_path in self.selected_files:
            self.selected_files.remove(file_path)
        
        # 분석 버튼 상태 업데이트
        self.analyze_btn.setEnabled(len(self.selected_files) > 0)
        
        # 상태바 업데이트
        selected_count = len(self.selected_files)
        total_count = len(self.file_paths)
        self.statusBar().showMessage(f'선택된 파일: {selected_count}/{total_count}개')
    
    def remove_file(self, file_path):
        """파일 목록에서 제거"""
        if file_path in self.file_paths:
            self.file_paths.remove(file_path)
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
        
        # 다중 데이터에서도 제거
        filename = os.path.basename(file_path)
        if filename in self.multiple_data:
            del self.multiple_data[filename]
        
        # UI 업데이트
        self.update_file_list_display()
        
        # 파일이 없으면 분석 버튼 비활성화
        if len(self.file_paths) == 0:
            self.analyze_btn.setEnabled(False)
            self.file_info_label.setText('선택된 파일: 없음')
            self.comparison_mode = False
            self.comparison_mode_check.setChecked(False)
        else:
            file_count = len(self.file_paths)
            self.file_info_label.setText(f'선택된 파일: {file_count}개')
    
    def toggle_comparison_mode(self, checked):
        """비교 모드 토글"""
        self.comparison_mode = checked
        
        if checked:
            # 비교 모드 활성화
            if len(self.file_paths) == 1:
                # 단일 파일인 경우 다중 파일 선택 권유
                reply = QMessageBox.question(
                    self, '비교 모드', 
                    '비교 모드를 사용하려면 여러 파일이 필요합니다.\n'
                    '추가 파일을 선택하시겠습니까?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.select_multiple_files()
                else:
                    self.comparison_mode_check.setChecked(False)
                    self.comparison_mode = False
                    return
            
            # 그래프 타입을 시계열로 고정하고 비활성화
            self.graph_type_combo.setCurrentText('시계열')
            self.graph_type_combo.setEnabled(False)
        else:
            # 비교 모드 비활성화
            self.graph_type_combo.setEnabled(True)
        
        # 데이터가 있으면 그래프 업데이트
        if self.data is not None or self.multiple_data:
            self.update_all_graphs()
    
    def auto_adjust_battery_range(self):
        """데이터에 따른 배터리 범위 자동 조정"""
        if self.data is None or len(self.data) == 0:
            return
        
        min_voltage = self.data['battery'].min()
        max_voltage = self.data['battery'].max()
        voltage_range = max_voltage - min_voltage
        
        # 여유분을 두고 범위 설정
        range_margin = voltage_range * 0.1  # 10% 여유분
        
        adjusted_min = max(0, min_voltage - range_margin)
        adjusted_max = max_voltage + range_margin
        
        # 스핀박스 값 업데이트
        self.battery_min_spin.setValue(adjusted_min)
        self.battery_max_spin.setValue(adjusted_max)
        
        # OnBoard 로그인지 확인하여 메시지 표시
        is_onboard = 'source' in self.data.columns and self.data['source'].iloc[0] == 'onboard_monitor'
        if is_onboard:
            self.statusBar().showMessage(
                f'OnBoard 모니터 로그 감지 - 전압 범위: {min_voltage:.2f}V ~ {max_voltage:.2f}V'
            )
        else:
            self.statusBar().showMessage(
                f'일반 배터리 로그 - 전압 범위: {min_voltage:.2f}V ~ {max_voltage:.2f}V'
            )
    
    def update_data_info_multiple(self):
        """다중 파일 데이터 정보 업데이트"""
        if not self.multiple_data:
            return
        
        info_text = "=== 다중 파일 비교 분석 ===\n\n"
        
        total_points = 0
        earliest_time = None
        latest_time = None
        
        for filename, file_info in self.multiple_data.items():
            data = file_info['data']
            total_points += len(data)
            
            file_earliest = data['timestamp'].min()
            file_latest = data['timestamp'].max()
            
            if earliest_time is None or file_earliest < earliest_time:
                earliest_time = file_earliest
            if latest_time is None or file_latest > latest_time:
                latest_time = file_latest
            
            info_text += f"📄 {filename}\n"
            info_text += f"   데이터 포인트: {len(data):,}개\n"
            info_text += f"   전압 범위: {data['battery'].min():.2f}V ~ {data['battery'].max():.2f}V\n"
            info_text += f"   평균 전압: {data['battery'].mean():.2f}V\n"
            info_text += f"   시간 범위: {file_earliest} ~ {file_latest}\n\n"
        
        info_text += f"📊 전체 요약:\n"
        info_text += f"   총 파일 수: {len(self.multiple_data)}개\n"
        info_text += f"   총 데이터 포인트: {total_points:,}개\n"
        info_text += f"   전체 시간 범위: {earliest_time} ~ {latest_time}\n"
        
        self.data_info_text.setText(info_text)
    
    def update_all_graphs_comparison(self):
        """비교 모드 그래프 업데이트"""
        if not self.multiple_data:
            return
        
        # 비교 모드에서는 그래프 타입을 시계열로 고정
        self.graph_type_combo.setCurrentText('시계열')
        self.graph_type_combo.setEnabled(False)  # 비교 모드에서는 비활성화
        
        # 기존 그래프 지우기 - 정의된 figure들만 사용
        self.main_figure.clear()
        self.detail_figure.clear()
        self.performance_figure.clear()
        
        # 비교 그래프 생성
        self.create_comparison_time_series()
        self.create_comparison_detail_analysis()
        self.create_comparison_performance()
        
        # 캔버스 새로고침
        self.main_canvas.draw()
        self.detail_canvas.draw()
        self.performance_canvas.draw()
    
    def create_comparison_time_series(self):
        """비교 모드 시계열 그래프"""
        ax = self.main_figure.add_subplot(111)
        
        # 파일별 색상 지정
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
                 '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']
        
        time_option = self.time_display_combo.currentText()
        
        for i, (filename, file_info) in enumerate(self.multiple_data.items()):
            # 선택된 파일만 표시
            if filename not in [os.path.basename(path) for path in self.selected_files]:
                continue
                
            data = file_info['data']
            color = colors[i % len(colors)]
            
            # 시간 축 변환
            if time_option == '절대시간':
                x_data = data['timestamp']
                x_label = '시간'
            elif time_option == '상대시간(시작점 기준)':
                start_time = data['timestamp'].min()
                x_data = (data['timestamp'] - start_time).dt.total_seconds()
                x_label = '상대시간 (초)'
            elif time_option == '경과시간(분)':
                start_time = data['timestamp'].min()
                x_data = (data['timestamp'] - start_time).dt.total_seconds() / 60
                x_label = '경과시간 (분)'
            elif time_option == '경과시간(시간)':
                start_time = data['timestamp'].min()
                x_data = (data['timestamp'] - start_time).dt.total_seconds() / 3600
                x_label = '경과시간 (시간)'
            else:
                x_data = data['timestamp']
                x_label = '시간'
            
            # 플롯 그리기
            ax.plot(x_data, data['battery'], color=color, alpha=0.7, 
                   linewidth=1.5, label=filename)
        
        ax.set_xlabel(x_label, fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 비교 - 시계열', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        ax.grid(True, alpha=0.3)
        
        # 시간 축 포맷팅
        if time_option == '절대시간':
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.tick_params(axis='x', rotation=45)
        
        self.main_figure.tight_layout()
    
    def create_comparison_detail_analysis(self):
        """비교 모드 상세 분석 (히스토그램 + 박스플롯)"""
        # 2x1 서브플롯으로 히스토그램과 박스플롯을 함께 표시
        axes = self.detail_figure.subplots(2, 1)
        
        # 히스토그램
        self.create_comparison_histogram_in_subplot(axes[0])
        
        # 박스플롯
        self.create_comparison_box_plot_in_subplot(axes[1])
        
        self.detail_figure.tight_layout()
    
    def create_comparison_histogram_in_subplot(self, ax):
        """비교 모드 히스토그램 (서브플롯용)"""
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
                 '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']
        
        # 선택된 파일들의 전압 데이터 수집
        selected_data = {}
        all_voltages = []
        
        for i, (filename, file_info) in enumerate(self.multiple_data.items()):
            if filename in [os.path.basename(path) for path in self.selected_files]:
                selected_data[filename] = {
                    'data': file_info['data'],
                    'color': colors[i % len(colors)]
                }
                all_voltages.extend(file_info['data']['battery'].tolist())
        
        if not all_voltages:
            ax.text(0.5, 0.5, '선택된 파일이 없습니다', 
                   transform=ax.transAxes, ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        # 전체 범위 기준으로 bins 설정
        bins = np.linspace(min(all_voltages), max(all_voltages), 30)
        
        for filename, file_data in selected_data.items():
            data = file_data['data']
            color = file_data['color']
            
            ax.hist(data['battery'], bins=bins, alpha=0.6, color=color, 
                   label=filename, edgecolor='black', linewidth=0.5)
        
        ax.set_xlabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('빈도', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 분포 비교', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        ax.grid(True, alpha=0.3)
    
    def create_comparison_box_plot_in_subplot(self, ax):
        """비교 모드 박스플롯 (서브플롯용)"""
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
                 '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']
        
        voltages_list = []
        labels = []
        color_list = []
        
        for i, (filename, file_info) in enumerate(self.multiple_data.items()):
            if filename in [os.path.basename(path) for path in self.selected_files]:
                voltages_list.append(file_info['data']['battery'].values)
                labels.append(filename)
                color_list.append(colors[i % len(colors)])
        
        if not voltages_list:
            ax.text(0.5, 0.5, '선택된 파일이 없습니다', 
                   transform=ax.transAxes, ha='center', va='center',
                   fontfamily=self.korean_font if self.korean_font else 'sans-serif')
            return
        
        bp = ax.boxplot(voltages_list, labels=labels, patch_artist=True)
        
        # 색상 적용
        for i, patch in enumerate(bp['boxes']):
            if i < len(color_list):
                patch.set_facecolor(color_list[i])
                patch.set_alpha(0.7)
        
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 분포 비교 (박스플롯)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
    
    def create_comparison_performance(self):
        """비교 모드 성능 지표 (통계 테이블)"""
        ax = self.performance_figure.add_subplot(111)
        ax.axis('off')
        
        stats_text = "=== 다중 파일 통계 비교 ===\n\n"
        
        # 테이블 헤더
        stats_text += f"{'파일명':<20} {'평균(V)':<8} {'표준편차':<8} {'최소값':<8} {'최대값':<8} {'범위(V)':<8} {'데이터수':<8}\n"
        stats_text += "-" * 85 + "\n"
        
        for filename, file_info in self.multiple_data.items():
            if filename in [os.path.basename(path) for path in self.selected_files]:
                data = file_info['data']
                
                # 파일명 축약 (20자 제한)
                short_name = filename[:17] + "..." if len(filename) > 20 else filename
                
                stats_text += f"{short_name:<20} "
                stats_text += f"{data['battery'].mean():<8.3f} "
                stats_text += f"{data['battery'].std():<8.3f} "
                stats_text += f"{data['battery'].min():<8.3f} "
                stats_text += f"{data['battery'].max():<8.3f} "
                stats_text += f"{data['battery'].max() - data['battery'].min():<8.3f} "
                stats_text += f"{len(data):<8,}\n"
        
        # 전체 요약
        if len(self.selected_files) > 1:
            stats_text += "\n" + "=" * 85 + "\n"
            stats_text += "전체 요약:\n"
            
            all_selected_data = []
            total_points = 0
            
            for filename, file_info in self.multiple_data.items():
                if filename in [os.path.basename(path) for path in self.selected_files]:
                    all_selected_data.extend(file_info['data']['battery'].tolist())
                    total_points += len(file_info['data'])
            
            if all_selected_data:
                import numpy as np
                all_data = np.array(all_selected_data)
                stats_text += f"• 전체 평균: {all_data.mean():.3f}V\n"
                stats_text += f"• 전체 표준편차: {all_data.std():.3f}V\n"
                stats_text += f"• 전체 범위: {all_data.min():.3f}V ~ {all_data.max():.3f}V\n"
                stats_text += f"• 총 데이터 포인트: {total_points:,}개\n"
                stats_text += f"• 선택된 파일 수: {len(self.selected_files)}개\n"
        
        # 한글 폰트 명시적 설정
        font_props = {
            'fontfamily': self.korean_font if self.korean_font else 'DejaVu Sans',
            'fontsize': 10
        }
        
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, 
               verticalalignment='top', **font_props)
        
        self.performance_figure.tight_layout()
    
    def create_comparison_histogram(self):
        """기존 히스토그램 메서드 - 더 이상 사용하지 않음"""
        # 호환성을 위해 유지하지만 detail_analysis로 통합됨
        pass
    
    def create_comparison_box_plot(self):
        """기존 박스플롯 메서드 - 더 이상 사용하지 않음"""
        # 호환성을 위해 유지하지만 detail_analysis로 통합됨
        pass
    
    def create_comparison_statistics(self):
        """기존 통계 메서드 - 더 이상 사용하지 않음"""
        # 호환성을 위해 유지하지만 performance로 통합됨
        pass
    
    def update_statistics_comparison(self):
        """비교 모드 통계 업데이트"""
        if not self.multiple_data:
            return
        
        # 왼쪽 패널의 다양한 위젯들 업데이트는 기존 단일 파일 모드와 동일하게 처리
        # 첫 번째 파일의 데이터를 기준으로 표시
        first_filename = list(self.multiple_data.keys())[0]
        first_data = self.multiple_data[first_filename]['data']
        
        # 기존 통계 업데이트 메서드 호출
        self.update_statistics()
    
    def on_graph_option_changed(self):
        """그래프 옵션 변경 시 최적화된 업데이트"""
        # on_analysis_option_changed와 동일한 최적화 적용
        if not hasattr(self, '_graph_update_timer'):
            self._graph_update_timer = QTimer()
            self._graph_update_timer.setSingleShot(True)
            self._graph_update_timer.timeout.connect(self._delayed_update_graphs)
        
        # 기존 타이머 정지 (중복 업데이트 방지)
        self._graph_update_timer.stop()
        
        # 데이터 유효성 검사
        if self.data is None and not self.multiple_data:
            return
        
        try:
            # 즉시 적용 가능한 변경사항 (격자, 커서 등)
            self._apply_immediate_changes()
            
            # 무거운 작업은 지연 실행 (100ms 후 - 그래프 변경은 약간 더 지연)
            self._graph_update_timer.start(100)
            
        except Exception as e:
            print(f"그래프 옵션 변경 오류: {e}")
            # 오류 시 상태바에 메시지 표시
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'그래프 옵션 변경 오류: {str(e)}', 3000)

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 현대적인 스타일
    
    # 애플리케이션 아이콘 설정 (선택사항)
    # app.setWindowIcon(QIcon('icon.png'))
    
    analyzer = BatteryLogAnalyzer()
    analyzer.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 