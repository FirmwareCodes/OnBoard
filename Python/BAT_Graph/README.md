# 배터리 로그 분석기 v1.0
## Battery Log Analyzer

OnBoard OLED Monitor 시스템의 배터리 로그를 분석하는 전용 프로그램입니다.

![프로그램 스크린샷](./screenshot.png)

## 주요 기능

### 📁 다양한 로그 형식 지원
- **OnBoard OLED Monitor 로그**: `status_log_YYYYMMDDHHMMSS.txt` 형식
- **CSV 파일**: timestamp, battery 컬럼 포함
- **JSON 파일**: 시계열 데이터 형태
- **일반 텍스트 로그**: 자유 형식

### 📊 실시간 그래프 시각화
- **시계열 그래프**: 시간에 따른 배터리 전압 변화
- **히스토그램**: 전압 분포 분석
- **박스플롯**: 시간대별 전압 분포
- **산점도**: 전압 패턴 시각화

### 🔍 상세 분석 기능
- **이동 평균**: 10점, 30점, 100점 이동평균
- **변화율 분석**: 전압 변화율 추적
- **이상치 감지**: IQR, Z-score, Isolation Forest 방법
- **주기성 분석**: FFT를 이용한 주파수 분석

### 🏥 배터리 건강도 평가
- **전압 레벨 건강도**: 평균 전압 기반 평가
- **안정성 건강도**: 변동성 기반 평가
- **방전 패턴 건강도**: 방전 기울기 분석
- **종합 건강도**: 가중 평균 점수 및 등급

### 🎯 OnBoard 모니터 특화 분석
- **상태 패턴 분석**: STANDBY, ACTIVE 등 상태 분포
- **LED 상태 분석**: L1, L2 LED 패턴 추적
- **메모 값 분석**: 숫자 메모 필드 트렌드 분석
- **타이머 분석**: 타이머 활성도 및 패턴

### 📈 예측 기능
- **방전 시간 예측**: 선형 회귀 기반 예측
- **신뢰도 계산**: R² 값 기반 예측 신뢰도
- **트렌드 분석**: 상승/하락/안정 트렌드 분류

### 📋 보고서 생성
- **HTML 보고서**: 웹 브라우저에서 볼 수 있는 상세 보고서
- **PDF 보고서**: 인쇄 가능한 그래프 보고서
- **통계 테이블**: 주요 통계 정보 요약

## 시스템 요구사항

### 필수 요구사항
- **Python 3.8 이상**
- **Windows 10 이상** (Linux 버전 미지원)
- **메모리**: 최소 4GB RAM
- **저장공간**: 최소 500MB 여유 공간

### 필수 패키지
```
PyQt5==5.15.10
pandas==2.2.2
numpy==1.26.4
matplotlib==3.8.4
seaborn==0.13.2
scipy==1.13.1
pyserial==3.5
scikit-learn==1.5.1
```

## 설치 및 실행

### 방법 1: 배치 파일 실행 (권장)
1. `start_analyzer.bat` 파일을 더블클릭
2. 자동으로 필요한 패키지 확인 및 설치
3. 프로그램 자동 실행

### 방법 2: 수동 설치
```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 프로그램 실행
python run_analyzer.py
```

### 방법 3: 직접 실행
```bash
python battery_log_analyzer.py
```

## 사용법

### 1. 프로그램 시작
- `start_analyzer.bat` 실행 또는 `python run_analyzer.py` 명령어

### 2. 로그 파일 선택
- 상단 툴바의 **"📁 로그 파일 선택"** 버튼 클릭
- OnBoard OLED Monitor 로그 파일 선택 (`.txt`, `.log`, `.csv` 등)

### 3. 분석 실행
- **"🔍 분석 시작"** 버튼 클릭
- 자동으로 파일 형식 감지 및 파싱
- 분석 결과 표시

### 4. 결과 확인
- **메인 그래프**: 시계열, 히스토그램, 박스플롯, 산점도
- **상세 분석**: 이동평균, 변화율, 이상치, 주기성
- **통계 정보**: 주요 통계값 및 OnBoard 특화 분석

### 5. 필터링 및 구간 선택
- 왼쪽 패널에서 시간 범위 및 전압 범위 필터 적용
- 그래프에서 특정 지점 클릭하여 상세 정보 확인
- 확대/축소 기능으로 세부 분석

### 6. 보고서 저장
- **"💾 보고서 저장"** 버튼 클릭
- HTML 또는 PDF 형식으로 분석 결과 저장

## OnBoard OLED Monitor 로그 형식

### 지원하는 로그 형식
```
================================================================================
OnBoard OLED Monitor 상태 로그 - 2025년 07월 10일
================================================================================
시간			배터리	타이머		상태		L1	L2	비고
--------------------------------------------------------------------------------
13:49:03		25.22V	00:00		STANDBY		X	X	3724
13:49:05		25.21V	00:00		STANDBY		X	X	3722
...
```

### 파일명 규칙
- `status_log_YYYYMMDDHHMMSS.txt`
- 예: `status_log_20250710134805.txt`

### 데이터 필드
- **시간**: HH:MM:SS 형식
- **배터리**: 전압값 (V 단위)
- **타이머**: MM:SS 형식
- **상태**: STANDBY, ACTIVE, CHARGING 등
- **L1, L2**: LED 상태 (X, O)
- **비고**: 숫자 메모 값

## 특화 기능

### OnBoard 모니터 전용 분석
1. **상태 분석**: 각 상태별 시간 분포 및 전압 패턴
2. **LED 패턴**: L1, L2 LED 상태 변화 추적
3. **메모 트렌드**: 숫자 메모값의 변화 패턴 분석
4. **전압 범위**: 20V~25V 범위에 최적화된 건강도 평가

### 고급 분석 옵션
- **이상치 감지**: 3가지 방법 (IQR, Z-score, Isolation Forest)
- **트렌드 라인**: 선형 회귀 기반 트렌드 표시
- **주기성 감지**: FFT 기반 주기적 패턴 발견
- **구간별 분석**: 시간대별 상세 통계

## 문제 해결

### 자주 발생하는 오류

#### 1. PyQt5 설치 오류
```bash
# Windows에서 Visual C++ 재배포 패키지 필요
pip install --upgrade pip
pip install PyQt5
```

#### 2. 파일 인코딩 오류
- 로그 파일을 UTF-8 인코딩으로 저장
- 또는 cp949 (한글 Windows) 인코딩 사용

#### 3. 메모리 부족 오류
- 큰 로그 파일의 경우 시간 범위 필터 사용
- 불필요한 프로그램 종료 후 재시도

#### 4. 그래프 표시 오류
```bash
# matplotlib 캐시 초기화
python -c "import matplotlib; matplotlib.font_manager._rebuild()"
```

### 지원되는 파일 크기
- **권장**: 10MB 이하
- **최대**: 100MB (메모리에 따라)
- **대용량 파일**: 시간 필터를 사용하여 구간별 분석

## 테스트 데이터

### 테스트 데이터 생성
```bash
# 런처에서 테스트 데이터 생성
python run_analyzer.py -t

# 또는 직접 생성
python battery_log_parser.py
```

### 생성되는 파일
- `test_battery_log.csv`: 일반 배터리 테스트 데이터
- `test_battery_log.log`: OnBoard 스타일 테스트 로그

## 개발 정보

### 프로젝트 구조
```
BAT_Graph/
├── battery_log_analyzer.py    # 메인 UI 애플리케이션
├── battery_log_parser.py      # 로그 파일 파싱 모듈
├── battery_analytics.py       # 분석 엔진
├── serial_parser.py          # 시리얼 데이터 파서
├── run_analyzer.py           # 실행 런처
├── start_analyzer.bat        # Windows 배치 파일
├── requirements.txt          # 패키지 의존성
└── README.md                # 사용법 (이 파일)
```

### 기술 스택
- **GUI**: PyQt5
- **데이터 처리**: pandas, numpy
- **시각화**: matplotlib, seaborn
- **분석**: scipy, scikit-learn
- **통신**: pyserial (시리얼 통신용)

### 버전 정보
- **현재 버전**: v1.0
- **호환성**: Python 3.8+, Windows 10+
- **업데이트**: 2025년 7월

## 라이선스

이 프로그램은 OnBoard OLED Monitor 시스템 전용으로 개발되었습니다.

## 지원 및 문의

### 기술 지원
- **개발자**: OnBoard 팀
- **이메일**: support@onboard.com
- **문서**: 이 README 파일

### 버그 리포트
버그 발견 시 다음 정보와 함께 문의:
1. 오류 메시지 전문
2. 사용한 로그 파일 샘플
3. Python 버전 및 OS 정보
4. 재현 단계

---

**© 2025 OnBoard Team. All rights reserved.** 