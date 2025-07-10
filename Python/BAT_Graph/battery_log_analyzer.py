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
                             QSpinBox, QDoubleSpinBox, QCheckBox, QSlider, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon
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
        plt.rcParams['axes.unicode_minus'] = False
        print(f"한글 폰트 설정: {korean_font}")
    else:
        # 기본 설정
        plt.rcParams['axes.unicode_minus'] = False
        print("한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")
    
    return korean_font

class BatteryLogAnalyzer(QMainWindow):
    """배터리 로그 분석 메인 UI"""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.analytics = BatteryAnalytics()
        self.parser = BatteryLogParser()
        
        # 분석 결과 저장
        self.analysis_results = {}
        self.current_selection = None
        
        # 드래그 관련 변수
        self.is_dragging = False
        self.drag_start_x = None
        self.drag_start_y = None
        self.original_xlim = None
        self.original_ylim = None
        
        # 시간 범위 선택을 위한 SpanSelector
        self.span_selector = None
        
        # 한글 폰트 설정
        self.korean_font = setup_korean_font()
        
        self.init_ui()
        self.setup_matplotlib_style()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle('배터리 로그 분석기 v1.1 - 드래그 지원')
        self.setGeometry(100, 100, 1400, 900)
        
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
        splitter.setSizes([350, 1050])
        
        # 상태바
        self.statusBar().showMessage('파일을 선택하여 분석을 시작하세요.')
        
    def create_toolbar(self, layout):
        """툴바 생성"""
        toolbar_layout = QHBoxLayout()
        
        # 파일 선택 버튼
        self.file_btn = QPushButton('📁 로그 파일 선택')
        self.file_btn.clicked.connect(self.select_file)
        self.file_btn.setMinimumHeight(40)
        toolbar_layout.addWidget(self.file_btn)
        
        # 파일 정보 라벨
        self.file_info_label = QLabel('선택된 파일: 없음')
        toolbar_layout.addWidget(self.file_info_label)
        
        toolbar_layout.addStretch()
        
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
        self.time_range_combo.currentTextChanged.connect(self.apply_time_filter)
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
        
        # 필터 적용 버튼
        filter_btn = QPushButton('필터 적용')
        filter_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(filter_btn, 2, 0, 1, 2)
        
        layout.addWidget(filter_group)
        
        # 분석 옵션
        analysis_group = QGroupBox('분석 옵션')
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.show_statistics = QCheckBox('통계 정보 표시')
        self.show_statistics.setChecked(True)
        analysis_layout.addWidget(self.show_statistics)
        
        self.show_anomalies = QCheckBox('이상치 감지')
        self.show_anomalies.setChecked(True)
        analysis_layout.addWidget(self.show_anomalies)
        
        self.show_trends = QCheckBox('트렌드 라인')
        self.show_trends.setChecked(False)
        analysis_layout.addWidget(self.show_trends)
        
        layout.addWidget(analysis_group)
        
        # 선택 구간 분석
        selection_group = QGroupBox('선택 구간 분석')
        selection_layout = QVBoxLayout(selection_group)
        
        self.selection_info = QTextEdit()
        self.selection_info.setMaximumHeight(200)
        self.selection_info.setReadOnly(True)
        selection_layout.addWidget(self.selection_info)
        
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
        
        return panel
    
    def create_main_graph_tab(self):
        """메인 그래프 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 그래프 컨트롤
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel('그래프 타입:'))
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(['시계열', '히스토그램', '박스플롯', '산점도'])
        self.graph_type_combo.currentTextChanged.connect(self.update_main_graph)
        control_layout.addWidget(self.graph_type_combo)
        
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
    
    def create_detail_analysis_tab(self):
        """상세 분석 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 상세 분석 그래프
        self.detail_figure = Figure(figsize=(12, 10))
        self.detail_canvas = FigureCanvas(self.detail_figure)
        layout.addWidget(self.detail_canvas)
        
        return widget
    
    def create_statistics_tab(self):
        """통계 정보 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 통계 테이블
        self.stats_table = QTableWidget()
        layout.addWidget(self.stats_table)
        
        return widget
    
    def setup_matplotlib_style(self):
        """Matplotlib 스타일 설정"""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 한글 폰트 재설정
        if self.korean_font:
            plt.rcParams['font.family'] = self.korean_font
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 300
    
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
        """분석 시작"""
        try:
            # 파일 파싱
            self.statusBar().showMessage('파일을 파싱하는 중...')
            self.data = self.parser.parse_log_file(self.file_path)
            
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
            
        except Exception as e:
            QMessageBox.critical(self, '오류', f'분석 중 오류가 발생했습니다:\n{str(e)}')
            self.statusBar().showMessage('분석 실패')
    
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
    
    def update_data_info(self):
        """데이터 정보 업데이트"""
        if self.data is None:
            return
        
        info_text = f"""
파일: {os.path.basename(self.file_path)}
데이터 포인트: {len(self.data):,}개
시간 범위: {self.data['timestamp'].min()} ~ {self.data['timestamp'].max()}
배터리 전압 범위: {self.data['battery'].min():.2f}V ~ {self.data['battery'].max():.2f}V
평균 배터리 전압: {self.data['battery'].mean():.2f}V
"""
        self.data_info_text.setText(info_text.strip())
    
    def update_all_graphs(self):
        """모든 그래프 업데이트"""
        self.update_main_graph()
        self.update_detail_analysis()
    
    def update_main_graph(self):
        """메인 그래프 업데이트"""
        if self.data is None:
            return
        
        self.main_figure.clear()
        
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
        
        # 배터리 전압 시계열
        ax.plot(self.data['timestamp'], self.data['battery'], 
                linewidth=1.5, label='배터리 전압', color='blue', alpha=0.8)
        
        # 이상치 표시
        if self.show_anomalies.isChecked() and 'anomalies' in self.analysis_results:
            anomalies = self.analysis_results['anomalies']
            if len(anomalies) > 0:
                ax.scatter(anomalies['timestamp'], anomalies['battery'],
                          color='red', s=50, alpha=0.7, label=f'이상치 ({len(anomalies)}개)', zorder=5)
        
        # 트렌드 라인
        if self.show_trends.isChecked():
            z = np.polyfit(range(len(self.data)), self.data['battery'], 1)
            p = np.poly1d(z)
            slope_per_hour = z[0] * (len(self.data) / ((self.data['timestamp'].max() - self.data['timestamp'].min()).total_seconds() / 3600))
            ax.plot(self.data['timestamp'], p(range(len(self.data))),
                    "r--", alpha=0.8, label=f'트렌드 ({slope_per_hour:.4f}V/h)')
        
        # 평균선 표시
        mean_voltage = self.data['battery'].mean()
        ax.axhline(y=mean_voltage, color='green', linestyle=':', alpha=0.7,
                   label=f'평균: {mean_voltage:.3f}V')
        
        ax.set_xlabel('시간', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 시계열', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
        ax.grid(True, alpha=0.3)
        
        # 날짜 포맷 설정
        if len(self.data) > 100:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        self.main_figure.autofmt_xdate()
        
        # 마우스 모드에 따른 설정 적용
        self.change_mouse_mode()
    
    def plot_histogram(self):
        """히스토그램 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        ax.hist(self.data['battery'], bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        ax.set_xlabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('빈도', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 분포', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.grid(True, alpha=0.3)
        
        # 통계 정보 추가
        mean_val = self.data['battery'].mean()
        std_val = self.data['battery'].std()
        ax.axvline(mean_val, color='red', linestyle='--', 
                   label=f'평균: {mean_val:.2f}V')
        ax.axvline(mean_val + std_val, color='orange', linestyle='--', 
                   label=f'+1σ: {mean_val + std_val:.2f}V')
        ax.axvline(mean_val - std_val, color='orange', linestyle='--', 
                   label=f'-1σ: {mean_val - std_val:.2f}V')
        ax.legend(prop={'family': self.korean_font if self.korean_font else 'sans-serif'})
    
    def plot_boxplot(self):
        """박스플롯 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        # 시간대별 박스플롯 (1시간 단위)
        self.data['hour'] = self.data['timestamp'].dt.hour
        hours = sorted(self.data['hour'].unique())
        
        if len(hours) > 24:
            # 데이터가 많으면 4시간 단위로 그룹화
            self.data['hour_group'] = (self.data['hour'] // 4) * 4
            hours = sorted(self.data['hour_group'].unique())
            hourly_data = [self.data[self.data['hour_group'] == h]['battery'].values 
                          for h in hours]
            labels = [f'{h:02d}-{h+3:02d}시' for h in hours]
        else:
            hourly_data = [self.data[self.data['hour'] == h]['battery'].values 
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
        
        # x축 라벨 회전
        plt.setp(ax.get_xticklabels(), rotation=45)
    
    def plot_scatter(self):
        """산점도 그리기"""
        ax = self.main_figure.add_subplot(111)
        
        # 시간을 숫자로 변환 (시작 시간으로부터 경과 시간)
        time_numeric = (self.data['timestamp'] - self.data['timestamp'].min()).dt.total_seconds() / 3600  # 시간 단위
        
        # 컬러맵으로 시간 진행 표현
        scatter = ax.scatter(time_numeric, self.data['battery'], 
                           c=time_numeric, cmap='viridis', alpha=0.6, s=20)
        
        ax.set_xlabel('경과 시간 (시간)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_ylabel('배터리 전압 (V)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        ax.set_title('배터리 전압 산점도 (시간 진행)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        
        # 컬러바 추가
        cbar = self.main_figure.colorbar(scatter, ax=ax)
        cbar.set_label('경과 시간 (시간)', fontfamily=self.korean_font if self.korean_font else 'sans-serif')
        
        ax.grid(True, alpha=0.3)
        
        # 트렌드 라인 추가 (옵션)
        if self.show_trends.isChecked():
            z = np.polyfit(time_numeric, self.data['battery'], 1)
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
        """통계 테이블 업데이트"""
        if self.data is None or not self.analysis_results:
            return
        
        stats = self.analysis_results.get('statistics', {})
        
        # 테이블 설정
        self.stats_table.setRowCount(len(stats))
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(['항목', '값'])
        
        # 데이터 입력
        for i, (key, value) in enumerate(stats.items()):
            self.stats_table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        # 테이블 크기 조정
        self.stats_table.resizeColumnsToContents()
    
    def apply_time_filter(self):
        """시간 필터 적용"""
        if self.data is None:
            return
        
        range_text = self.time_range_combo.currentText()
        
        if range_text == '전체':
            self.filtered_data = self.data.copy()
        else:
            now = self.data['timestamp'].max()
            
            if range_text == '최근 1시간':
                start_time = now - timedelta(hours=1)
            elif range_text == '최근 6시간':
                start_time = now - timedelta(hours=6)
            elif range_text == '최근 24시간':
                start_time = now - timedelta(hours=24)
            else:
                return
            
            self.filtered_data = self.data[self.data['timestamp'] >= start_time].copy()
        
        self.update_all_graphs()
    
    def apply_filters(self):
        """모든 필터 적용"""
        if self.data is None:
            return
        
        filtered = self.data.copy()
        
        # 배터리 범위 필터
        min_battery = self.battery_min_spin.value()
        max_battery = self.battery_max_spin.value()
        
        filtered = filtered[
            (filtered['battery'] >= min_battery) & 
            (filtered['battery'] <= max_battery)
        ]
        
        self.filtered_data = filtered
        self.update_all_graphs()
        
        self.statusBar().showMessage(f'필터 적용됨 - {len(filtered)}개 데이터 포인트')
    
    def on_canvas_press(self, event):
        """캔버스 마우스 눌림 이벤트"""
        if event.inaxes is None:
            return
        
        mode = self.mouse_mode_combo.currentText()
        
        if mode == '드래그 이동':
            # 드래그 이동 모드
            self.is_dragging = True
            self.drag_start_x = event.xdata
            self.drag_start_y = event.ydata
            self.original_xlim = event.inaxes.get_xlim()
            self.original_ylim = event.inaxes.get_ylim()
            
        elif mode == '선택' and self.data is not None:
            # 선택 모드 - 클릭한 지점의 데이터 표시
            self.on_canvas_click(event)
    
    def on_canvas_release(self, event):
        """캔버스 마우스 놓음 이벤트"""
        if self.is_dragging:
            self.is_dragging = False
            self.drag_start_x = None
            self.drag_start_y = None
            self.original_xlim = None
            self.original_ylim = None
    
    def on_canvas_click(self, event):
        """캔버스 클릭 이벤트 (기존 코드 유지)"""
        if event.inaxes and self.data is not None:
            # 클릭 지점 근처의 데이터 찾기
            if hasattr(event, 'xdata') and event.xdata:
                # 시간 기반 선택
                clicked_time = mdates.num2date(event.xdata)
                
                # 가장 가까운 데이터 포인트 찾기
                time_diff = abs(self.data['timestamp'] - clicked_time)
                nearest_idx = time_diff.idxmin()
                nearest_point = self.data.loc[nearest_idx]
                
                # 선택 정보 업데이트
                self.update_selection_info(nearest_point)
    
    def on_canvas_motion(self, event):
        """캔버스 마우스 이동 이벤트"""
        if event.inaxes is None:
            return
        
        mode = self.mouse_mode_combo.currentText()
        
        if self.is_dragging and mode == '드래그 이동':
            # 드래그 이동 처리
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
                
        elif mode == '선택' and self.data is not None:
            # 마우스 위치의 정보를 상태바에 표시
            if hasattr(event, 'xdata') and hasattr(event, 'ydata'):
                if event.xdata and event.ydata:
                    try:
                        time_str = mdates.num2date(event.xdata).strftime("%H:%M:%S")
                        self.statusBar().showMessage(
                            f'시간: {time_str}, 전압: {event.ydata:.3f}V'
                        )
                    except:
                        pass
    
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
            self.statusBar().showMessage('드래그하여 그래프를 이동하세요.')
        else:
            self.statusBar().showMessage('클릭하여 데이터 포인트를 선택하세요.')
    
    def on_span_select(self, xmin, xmax):
        """시간 범위 선택 콜백"""
        if self.data is None:
            return
        
        # 선택된 시간 범위의 데이터 필터링
        start_time = mdates.num2date(xmin)
        end_time = mdates.num2date(xmax)
        
        filtered_data = self.data[
            (self.data['timestamp'] >= start_time) & 
            (self.data['timestamp'] <= end_time)
        ]
        
        if len(filtered_data) > 0:
            # 선택된 구간 정보 업데이트
            self.update_span_selection_info(filtered_data, start_time, end_time)
            self.statusBar().showMessage(
                f'선택된 구간: {len(filtered_data)}개 포인트 '
                f'({start_time.strftime("%H:%M:%S")} ~ {end_time.strftime("%H:%M:%S")})'
            )
    
    def update_span_selection_info(self, data, start_time, end_time):
        """구간 선택 정보 업데이트"""
        duration = end_time - start_time
        voltage_change = data['battery'].iloc[-1] - data['battery'].iloc[0]
        avg_voltage = data['battery'].mean()
        
        info_text = f"""
선택된 구간 분석:
시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
구간 길이: {str(duration).split('.')[0]}

전압 정보:
- 시작 전압: {data['battery'].iloc[0]:.3f}V
- 종료 전압: {data['battery'].iloc[-1]:.3f}V
- 평균 전압: {avg_voltage:.3f}V
- 전압 변화: {voltage_change:+.3f}V
- 최소 전압: {data['battery'].min():.3f}V
- 최대 전압: {data['battery'].max():.3f}V

데이터 포인트: {len(data)}개
"""
        self.selection_info.setText(info_text.strip())
    
    def update_selection_info(self, point):
        """선택된 포인트 정보 업데이트"""
        info_text = f"""
선택된 시점: {point['timestamp']}
배터리 전압: {point['battery']:.3f}V

주변 데이터 분석:
- 5분 전 평균: {self.get_nearby_average(point['timestamp'], -5):.3f}V
- 5분 후 평균: {self.get_nearby_average(point['timestamp'], 5):.3f}V
- 변화율: {self.get_change_rate_at(point['timestamp']):.2f}%/분
"""
        self.selection_info.setText(info_text.strip())
    
    def get_nearby_average(self, timestamp, minutes_offset):
        """특정 시점 주변의 평균값 계산"""
        target_time = timestamp + timedelta(minutes=minutes_offset)
        nearby_data = self.data[
            abs(self.data['timestamp'] - target_time) <= timedelta(minutes=2)
        ]
        return nearby_data['battery'].mean() if len(nearby_data) > 0 else 0
    
    def get_change_rate_at(self, timestamp):
        """특정 시점의 변화율 계산"""
        idx = self.data[self.data['timestamp'] == timestamp].index
        if len(idx) > 0 and idx[0] > 0:
            current_val = self.data.loc[idx[0], 'battery']
            prev_val = self.data.loc[idx[0]-1, 'battery']
            return ((current_val - prev_val) / prev_val) * 100
        return 0
    
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
        """HTML 보고서 저장 (그래프 포함)"""
        import base64
        from io import BytesIO
        
        stats = self.analysis_results.get('statistics', {})
        
        # 메인 그래프를 이미지로 변환
        main_graph_img = self.figure_to_base64(self.main_figure)
        
        # 상세 분석 그래프를 이미지로 변환
        detail_graph_img = self.figure_to_base64(self.detail_figure)
        
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
        }}
        .header {{ 
            background-color: #f0f8ff; 
            padding: 20px; 
            border-radius: 8px; 
            border-left: 4px solid #4CAF50;
            margin-bottom: 20px;
        }}
        .section {{ 
            margin: 30px 0; 
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .stats-table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 10px 0;
        }}
        .stats-table th, .stats-table td {{ 
            border: 1px solid #ddd; 
            padding: 12px; 
            text-align: left; 
        }}
        .stats-table th {{ 
            background-color: #f2f2f2; 
            font-weight: bold;
        }}
        .stats-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .graph-container {{
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #eee;
            border-radius: 5px;
            background-color: #fafafa;
        }}
        .graph-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        .graph-img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔋 배터리 로그 분석 보고서</h1>
        <p><strong>생성일시:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}</p>
        <p><strong>분석 파일:</strong> {os.path.basename(self.file_path)}</p>
        <p><strong>분석 프로그램:</strong> 배터리 로그 분석기 v1.1</p>
    </div>
    
    <div class="section">
        <h2>📊 데이터 요약</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>데이터 규모</h3>
                <p><strong>총 데이터 포인트:</strong> {len(self.data):,}개</p>
            </div>
            <div class="summary-card">
                <h3>시간 범위</h3>
                <p><strong>시작:</strong> {self.data['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>종료:</strong> {self.data['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>총 기간:</strong> {str(self.data['timestamp'].max() - self.data['timestamp'].min()).split('.')[0]}</p>
            </div>
            <div class="summary-card">
                <h3>전압 정보</h3>
                <p><strong>범위:</strong> {self.data['battery'].min():.3f}V ~ {self.data['battery'].max():.3f}V</p>
                <p><strong>평균:</strong> {self.data['battery'].mean():.3f}V</p>
                <p><strong>표준편차:</strong> {self.data['battery'].std():.3f}V</p>
            </div>
        </div>
    </div>
    
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
        <h2>📋 상세 통계 정보</h2>
        <table class="stats-table">
            <thead>
                <tr><th>항목</th><th>값</th></tr>
            </thead>
            <tbody>
"""
        
        for key, value in stats.items():
            html_content += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
        
        # 추가 분석 정보
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
        </div>
    </div>
    
    <div class="section">
        <h2>📝 분석 요약</h2>
        <div class="summary-card">
            <h3>주요 발견사항</h3>
            <ul>
                <li>평균 배터리 전압: {self.data['battery'].mean():.3f}V</li>
                <li>전압 변동 범위: {self.data['battery'].max() - self.data['battery'].min():.3f}V</li>
                <li>데이터 안정성: {"높음" if self.data['battery'].std() < 0.1 else "보통" if self.data['battery'].std() < 0.2 else "낮음"}</li>
                <li>이상치 비율: {len(anomalies)/len(self.data)*100:.2f}%</li>
            </ul>
        </div>
"""
        
        html_content += """
    </div>
    
    <footer style="margin-top: 40px; padding: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
        <p>이 보고서는 OnBoard 배터리 로그 분석기 v1.1에서 자동 생성되었습니다.</p>
        <p>생성 시간: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
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