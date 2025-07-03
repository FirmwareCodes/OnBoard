# OnBoard OLED Monitor v1.1

STM32 OnBoard LED Timer의 OLED 화면을 실시간으로 모니터링하고 원격 제어할 수 있는 Python 기반 PC 도구입니다.

## 새로운 기능 (v1.1)

### 🔄 실제 펌웨어 통신
- **실시간 화면 데이터**: 펌웨어에서 실제 OLED 화면 데이터 수신
- **상태 정보 파싱**: 배터리, 타이머, LED 상태 등 실시간 정보 표시
- **자동/수동 모드**: 테스트 데이터와 실제 데이터 자동 전환
- **전용 UART 태스크**: FreeRTOS UartTask로 안정적인 통신 처리

### 🎛️ 원격 제어
- **타이머 제어**: 시작/정지/설정을 PC에서 원격 제어
- **시스템 리셋**: 펌웨어 상태 초기화
- **연결 테스트**: PING/PONG으로 통신 품질 확인
- **응답 시간 측정**: 네트워크 지연 시간 모니터링

### 📊 향상된 모니터링
- **데이터 소스 표시**: 실시간 데이터 vs 테스트 데이터 구분
- **통신 상태 모니터링**: 연결 품질 및 오류 상태 실시간 표시
- **성능 통계**: FPS, 캡처 시간, 응답 시간 등

## 주요 기능

### 실시간 모니터링
- OLED 화면 실시간 표시 (128x64 해상도)
- 1x~8x 확대 지원
- 100ms 간격 업데이트 (10 FPS)
- 자동 저장 기능

### 디바이스 상태 모니터링
- 배터리 잔량 (%)
- 타이머 시간 (MM:SS)
- 시스템 상태 (STANDBY/RUNNING/SETTING/COOLING)
- LED 연결 상태 (L1, L2)

### 파일 관리
- PNG 형식 화면 캡처
- 자동 파일명 생성 (타임스탬프)
- JSON 형식 세션 기록
- 자동 디렉토리 생성

## 설치 및 실행

### 요구사항
```bash
# 필수 패키지 설치
pip install -r requirements.txt
```

### 실행 방법

#### Windows
```cmd
# 배치 파일 실행
run_monitor.bat

# 또는 직접 실행
python oled_monitor.py
```

#### Linux/macOS
```bash
# 셸 스크립트 실행
chmod +x run_monitor.sh
./run_monitor.sh

# 또는 직접 실행
python3 oled_monitor.py
```

## 사용법

### 1. 연결 설정
1. 적절한 시리얼 포트 선택 (예: COM3, /dev/ttyUSB0)
2. 보드레이트 설정 (기본: 115200)
3. '연결' 버튼 클릭

### 2. 모니터링 시작
1. '모니터링 시작' 클릭
2. 펌웨어 모니터링 모드 자동 활성화
3. 실시간 화면 및 상태 정보 표시

### 3. 원격 제어
- **타이머 시작**: START_TIMER 명령 전송
- **타이머 정지**: STOP_TIMER 명령 전송
- **타이머 설정**: SET_TIMER:MM:SS 형식으로 전송
- **시스템 리셋**: RESET 명령으로 펌웨어 초기화
- **연결 테스트**: PING/PONG으로 통신 상태 확인

## 통신 프로토콜

### 지원 명령어
```
GET_SCREEN      # 화면 데이터 요청
GET_STATUS      # 상태 정보 요청
START_MONITOR   # 자동 모니터링 시작
STOP_MONITOR    # 자동 모니터링 중지
START_TIMER     # 타이머 시작
STOP_TIMER      # 타이머 정지
SET_TIMER:MM:SS # 타이머 설정
RESET           # 시스템 리셋
PING            # 연결 테스트
```

### 데이터 형식
```
# 화면 데이터
SCREEN_START
SIZE:128x64
[1024 bytes 이진 데이터]
SCREEN_END

# 상태 정보
STATUS:BAT:75%,TIMER:05:30,STATUS:RUNNING,L1:1,L2:0
```

## 파일 구조
```
Python/OLED_Monitor/
├── oled_monitor.py      # 메인 GUI 애플리케이션
├── serial_parser.py     # 시리얼 데이터 파싱
├── utils.py            # 유틸리티 함수들
├── requirements.txt    # 필수 패키지 목록
├── README.md          # 이 파일
├── __init__.py        # Python 패키지 초기화
├── run_monitor.bat    # Windows 실행 스크립트
└── run_monitor.sh     # Linux/macOS 실행 스크립트
```

## 성능 특성
- **화면 업데이트**: 100ms (10 FPS)
- **상태 업데이트**: 1초 간격
- **UART 전송 시간**: 화면 데이터 약 100ms
- **메모리 사용량**: 약 50MB (GUI 포함)
- **응답 시간**: 일반적으로 10-50ms
- **태스크 우선순위**: UartTask > AdcTask > ButtonTask > OneSecondTask > DisplayTask

## 트러블슈팅

### 연결 문제
- 시리얼 포트가 올바른지 확인
- 다른 프로그램이 포트를 사용 중인지 확인
- 보드레이트가 115200인지 확인

### 데이터 수신 문제
- 펌웨어가 올바르게 플래시되었는지 확인
- UART 케이블 연결 상태 확인
- '연결 테스트' 버튼으로 통신 상태 확인

### 성능 문제
- 모니터링 중지 후 다시 시작
- 자동 저장 기능 비활성화
- 화면 확대 비율 낮추기

## 업데이트 내역

### v1.1 (2024-01-01)
- ✅ 실제 펌웨어와의 양방향 통신 구현
- ✅ 원격 제어 기능 추가 (타이머 시작/정지/설정)
- ✅ 실시간 데이터 파싱 및 표시
- ✅ 모니터링 모드 자동 제어
- ✅ 연결 테스트 및 성능 모니터링
- ✅ 향상된 UI 및 사용자 경험

### v1.0 (2023-12-31)
- 기본 GUI 구현
- 테스트 데이터 생성
- 화면 캡처 기능
- 파일 저장 기능

## 라이선스
MIT License - 자세한 내용은 LICENSE 파일 참조

## 기여
버그 리포트나 기능 제안은 GitHub Issues를 통해 제출해 주세요.

---
**OnBoard LED Timer Project Team**  
**v1.1 - 2024년 1월 1일**

## 구현 세부사항

### 펌웨어 측 (STM32)

#### FreeRTOS 태스크 구조
- **OneSecondTask**: 시스템 상태 LED 토글 (1초 주기)
- **AdcTask**: ADC 읽기 및 PWM 제어 (20ms 주기)  
- **DisplayTask**: OLED 화면 업데이트 (50ms 주기)
- **ButtonTask**: 버튼 입력 처리 (10ms 주기)
- **UartTask**: UART 통신 및 명령어 처리 (20ms 주기) ⭐ 신규

#### UartTask 기능
1. **명령어 수신 및 처리**: 인터럽트 기반 UART 수신
2. **자동 모니터링**: 100ms 주기 화면 데이터 전송
3. **상태 정보 전송**: 1초 주기 상태 업데이트
4. **원격 제어**: 타이머 시작/정지/설정 처리
5. **오류 처리**: 잘못된 명령어 및 타임아웃 처리

#### 메모리 구조
- **UART_State_t**: 256B 수신버퍼 + 1200B 송신버퍼
- **명령어 버퍼**: 128B (개행 단위 파싱)
- **스택 크기**: 2KB (다른 태스크의 4배)

### PC측 (Python)

1. **serial_parser.py**: 시리얼 데이터 파싱
2. **oled_monitor.py**: GUI 모니터링 도구
3. **utils.py**: 유틸리티 함수들 