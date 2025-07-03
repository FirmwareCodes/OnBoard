# OnBoard LED Timer - UART 통신 프로토콜

## 개요

STM32 OnBoard LED Timer 펌웨어와 PC측 모니터링 도구 간의 UART 통신 프로토콜을 정의합니다.

## 하드웨어 설정

- **UART**: USART1 (PA9/PA10)
- **보드레이트**: 115200 bps
- **데이터 비트**: 8
- **패리티**: None
- **스톱 비트**: 1
- **플로우 컨트롤**: None

## 지원 명령어

### 1. 화면 데이터 요청
```
명령어: GET_SCREEN
응답: SCREEN_START
      SIZE:128x64
      [1024 bytes 이진 데이터]
      SCREEN_END
```

### 2. 상태 정보 요청
```
명령어: GET_STATUS
응답: STATUS:BAT:75%,TIMER:05:30,STATUS:RUNNING,L1:1,L2:0
```

### 3. 모니터링 모드 제어
```
명령어: START_MONITOR
응답: OK:Monitoring started

명령어: STOP_MONITOR
응답: OK:Monitoring stopped
```

### 4. 타이머 설정
```
명령어: SET_TIMER:05:30
응답: OK:Timer set
```

### 5. 타이머 제어
```
명령어: START_TIMER
응답: OK:Timer started

명령어: STOP_TIMER
응답: OK:Timer stopped
```

### 6. 시스템 리셋
```
명령어: RESET
응답: OK:System reset
```

### 7. 연결 테스트
```
명령어: PING
응답: PONG
```

## 데이터 형식

### 화면 데이터
- **크기**: 1024 bytes (128x64 픽셀 ÷ 8)
- **형식**: OLED SH1106 컨트롤러 형식
- **비트 순서**: MSB first
- **페이지**: 8 pages (각 8픽셀 높이)

### 상태 정보
- **BAT**: 배터리 잔량 (0-100%)
- **TIMER**: 타이머 시간 (MM:SS)
- **STATUS**: 타이머 상태 (STANDBY/RUNNING/SETTING/COOLING)
- **L1/L2**: LED 연결 상태 (0=연결안됨, 1=연결됨)

## 오류 처리

```
ERROR:No screen data available
ERROR:Invalid time range
ERROR:Invalid time format
ERROR:Unknown command
ERROR:Command too long
```

## 구현 세부사항

### 펌웨어 측 (STM32)

1. **main.c**에 추가된 함수들:
   - `UI_SendScreenDataOverUART()`: 화면 데이터 전송
   - `UI_SendStatusOverUART()`: 상태 정보 전송
   - `UI_ProcessUARTCommand()`: 명령어 처리
   - `HAL_UART_RxCpltCallback()`: UART 인터럽트 콜백

2. **전역 변수**:
   - `current_ui_status`: 현재 UI 상태
   - `uart_rx_buffer[]`: UART 수신 버퍼
   - `uart_tx_buffer[]`: UART 송신 버퍼

### PC측 (Python)

1. **serial_parser.py**: 시리얼 데이터 파싱
2. **oled_monitor.py**: GUI 모니터링 도구
3. **utils.py**: 유틸리티 함수들

## 성능 특성

- **화면 업데이트 주기**: 100ms (10 FPS)
- **상태 정보 업데이트**: 1초
- **UART 송신 시간**: 화면 데이터 약 100ms
- **메모리 사용량**: 약 1.5KB (버퍼 포함)

## 사용 예제

### 기본 모니터링 세션
```
PC -> STM32: GET_STATUS
STM32 -> PC: STATUS:BAT:75%,TIMER:05:30,STATUS:RUNNING,L1:1,L2:0

PC -> STM32: GET_SCREEN
STM32 -> PC: SCREEN_START
             SIZE:128x64
             [1024 bytes 데이터]
             SCREEN_END
```

### 원격 제어
```
PC -> STM32: SET_TIMER:10:00
STM32 -> PC: OK:Timer set

PC -> STM32: START_TIMER
STM32 -> PC: OK:Timer started

PC -> STM32: GET_STATUS
STM32 -> PC: STATUS:BAT:75%,TIMER:09:59,STATUS:RUNNING,L1:1,L2:0
```

## 향후 확장

- [ ] 이진 프로토콜로 성능 최적화
- [ ] 실시간 스트리밍 모드
- [ ] 압축 알고리즘 적용
- [ ] 체크섬 검증 추가
- [ ] 무선 통신 지원

---

**작성일**: 2024-01-01  
**버전**: v1.0  
**담당자**: OnBoard LED Timer Project Team 