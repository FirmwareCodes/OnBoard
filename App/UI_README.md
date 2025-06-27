# OnBoard LED 타이머 OLED UI 시스템

## 개요
이 UI 시스템은 1.3인치 OLED 디스플레이(128x64 픽셀, 흑백)를 위한 휴대용 LED 조명 타이머 인터페이스입니다.

## 화면 구성

### 레이아웃
```
┌─────────────────────────────────────────┐ 128px
│ [Timer]  [▶/⏸]           [02:30] │
│                                         │ 
│                                         │
│             ●●●●●●●●●●                  │
│           ●●           ●●                │
│          ●●    85%     ●●               │ 64px
│           ●●           ●●                │
│             ●●●●●●●●●●                  │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

### 영역별 설명
1. **좌측 상단**: 타이머 상태 (시계 아이콘 + 재생/일시정지 아이콘)
2. **우측 상단**: 설정된 타이머 시간 (HH:MM 형식)
3. **중앙**: 원형 프로그래스바로 배터리 잔량 표시 + 퍼센티지 숫자

## 파일 구조

```
App/Common/
├── Inc/OLED/
│   └── UI_Layout.h          # UI 레이아웃 정의 및 함수 선언
├── Src/OLED/
│   ├── UI_Icons.c           # 아이콘 비트맵 데이터
│   ├── UI_Display.c         # 메인 UI 렌더링 함수들
│   └── UI_Example.c         # 사용 예제 및 테스트 코드
└── UI_README.md             # 이 파일
```

## 주요 기능

### 1. 원형 프로그래스바
- 배터리 잔량을 0-100% 범위로 시각적 표시
- 12시 방향부터 시계방향으로 진행
- 두께감 있는 프로그래스 바

### 2. 아이콘 시스템
- 8x8 픽셀 비트맵 아이콘
- 타이머, 재생, 일시정지 아이콘 포함
- 확장 가능한 아이콘 시스템

### 3. 숫자 표시
- 5x7 픽셀 커스텀 폰트
- 배터리 퍼센트 및 타이머 시간 표시
- 퍼센트 기호(%) 및 콜론(:) 포함

## 사용법

### 1. 초기화
```c
#include "App/Common/Inc/OLED/UI_Layout.h"

// 시스템 초기화
UI_SystemInit();
```

### 2. 상태 업데이트
```c
// 배터리 레벨 업데이트 (0-100%)
UI_UpdateBattery(75);

// 타이머 설정 업데이트 (시, 분)
UI_UpdateTimerSetting(2, 30);  // 2시간 30분

// 타이머 상태 토글
UI_ToggleTimerStatus();
```

### 3. 전체 화면 그리기
```c
UI_Status_t status = {
    .battery_percent = 85,
    .timer_hours = 2,
    .timer_minutes = 30,
    .is_timer_running = 1,
    .is_connected = 1
};

UI_DrawFullScreen(&status);
```

### 4. 특수 효과
```c
// 배터리 부족 경고
UI_ShowLowBatteryWarning();

// 타이머 완료 알림
UI_ShowTimerComplete();

// 절전 모드 페이드아웃
UI_FadeOut();
```

## API 레퍼런스

### 주요 함수들

#### 초기화 및 기본 함수
- `void UI_Init(void)` - UI 시스템 초기화
- `void UI_Clear(void)` - 화면 클리어
- `void UI_DrawFullScreen(UI_Status_t* status)` - 전체 화면 렌더링

#### 개별 구성요소 그리기
- `void UI_DrawTimerStatus(uint8_t is_running)` - 타이머 상태 표시
- `void UI_DrawTimerValue(uint8_t hours, uint8_t minutes)` - 타이머 값 표시
- `void UI_DrawBatteryProgress(uint8_t percent)` - 배터리 프로그래스바
- `void UI_DrawBatteryPercentage(uint8_t percent)` - 배터리 퍼센트 숫자

#### 보조 함수들
- `void UI_DrawIcon8x8(uint16_t x, uint16_t y, const unsigned char* icon_data, uint16_t color)` - 8x8 아이콘 그리기
- `void UI_DrawDigit(uint16_t x, uint16_t y, uint8_t digit, uint16_t color)` - 숫자 그리기
- `void UI_DrawCircularProgress(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color)` - 원형 프로그래스바

### 데이터 구조체

```c
typedef struct {
    uint8_t battery_percent;    // 배터리 잔량 (0-100%)
    uint8_t timer_hours;        // 설정된 타이머 시간 (0-23)
    uint8_t timer_minutes;      // 설정된 타이머 분 (0-59)
    uint8_t is_timer_running;   // 타이머 실행 상태 (0: 정지, 1: 실행)
    uint8_t is_connected;       // 연결 상태 (필요시 사용)
} UI_Status_t;
```

## 테스트 및 데모

### 데모 실행
```c
// 전체 기능 데모 테스트
UI_DemoTest();
```

### 개별 테스트
```c
// 배터리 레벨 변화 테스트
for(int i = 100; i >= 0; i -= 10) {
    UI_UpdateBattery(i);
    HAL_Delay(500);
}

// 타이머 상태 토글 테스트
for(int i = 0; i < 5; i++) {
    UI_ToggleTimerStatus();
    HAL_Delay(800);
}
```

## 커스터마이징

### 아이콘 추가
1. `UI_Icons.c`에 새로운 8x8 비트맵 배열 추가
2. `UI_Layout.h`에 extern 선언 추가
3. 필요한 곳에서 `UI_DrawIcon8x8()` 함수로 사용

### 레이아웃 수정
`UI_Layout.h` 파일의 위치 정의 상수들을 수정:
```c
#define TIMER_STATUS_X      2
#define TIMER_STATUS_Y      2
#define BATTERY_CENTER_X    64
#define BATTERY_CENTER_Y    40
// 기타 위치 상수들...
```

### 색상 변경
흑백 OLED이지만 그레이스케일 효과를 위해 색상 상수 사용:
```c
#define COLOR_WHITE    WHITE
#define COLOR_BLACK    BLACK
```

## 성능 최적화

- 전체 화면 업데이트 대신 필요한 부분만 업데이트
- 배터리 상태가 자주 변하지 않으면 캐싱 사용
- 애니메이션 효과는 배터리 소모를 고려하여 제한적으로 사용

## 주의사항

1. **메모리 사용량**: 128x64 픽셀 버퍼 사용
2. **성능**: 원형 프로그래스바 그리기는 연산 집약적
3. **배터리**: 화면 업데이트 빈도 조절 필요
4. **폰트**: 작은 화면에 최적화된 5x7 픽셀 폰트 사용

## 확장 가능성

- 더 큰 아이콘 지원 (16x16)
- 애니메이션 효과 추가
- 다국어 지원
- 사용자 설정 화면 추가
- 그래프 표시 기능 