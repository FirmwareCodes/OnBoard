/*****************************************************************************
 * | File      	:   UI_Layout.h
 * | Author      :   OnBoard LED Light Timer
 * | Function    :   1.3inch OLED UI Layout Design
 * | Info        :   128x64 display with battery status, timer settings, and progress
 *----------------
 * |	This version:   V1.0
 * | Date        :   2024-01-01
 * | Info        :   Initial UI layout design
 ******************************************************************************/
#ifndef __UI_LAYOUT_H
#define __UI_LAYOUT_H

#include "GUI_Paint.h"
#include "../../Fonts/fonts.h"

// 화면 크기 정의
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

// 성능 및 업데이트 주기 설정
#define UI_UPDATE_INTERVAL_MS 50                                            // 메인 UI 업데이트 주기 (20fps)
#define PROGRESS_UPDATE_INTERVAL_MS 250                                     // 프로그래스바 업데이트 주기 (5fps)
#define BLINK_INTERVAL_MS 250                                              // 깜빡임 주기 (1초)
#define BLINK_COUNTER_THRESHOLD (BLINK_INTERVAL_MS / UI_UPDATE_INTERVAL_MS) // 깜빡임 카운터 임계값

// 메인 영역 분할
#define LEFT_AREA_WIDTH 81  // 좌측 배터리 영역
#define RIGHT_AREA_WIDTH 32 // 우측 정보 영역
#define AREA_HEIGHT 64

// 좌측 영역 - 배터리 프로그래스바 (96x64)
#define BATTERY_AREA_X 0
#define BATTERY_AREA_Y 0
#define BATTERY_AREA_WIDTH 81
#define BATTERY_AREA_HEIGHT 64

// 배터리 원형 프로그래스 (좌측 영역 중앙)
#define BATTERY_CENTER_X 37     // 96/2 = 48
#define BATTERY_CENTER_Y 32     // 64/2 = 32
#define BATTERY_OUTER_RADIUS 30 // 더 큰 반지름
#define BATTERY_INNER_RADIUS 20
#define BATTERY_PROGRESS_WIDTH 6 // 더 두꺼운 프로그래스바

// 배터리 퍼센티지 텍스트 위치 (중앙)
#define BATTERY_PERCENT_X BATTERY_CENTER_X
#define BATTERY_PERCENT_Y BATTERY_CENTER_Y + 2

// 타이머 실행 표시기 위치 (좌측 상단)
#define TIMER_INDICATOR_X 8     // 좌측 상단
#define TIMER_INDICATOR_Y 8     // 좌측 상단
#define TIMER_INDICATOR_RADIUS 3 // 작은 원형 표시기

// 우측 영역 - 정보 표시 (32x64)
#define INFO_AREA_X 88
#define INFO_AREA_Y 0
#define INFO_AREA_WIDTH 32
#define INFO_AREA_HEIGHT 64

// 우측 영역 4등분 (각 16픽셀 높이)
#define INFO_SECTION_HEIGHT 16

// 1구역: 타이머 시간 (분:초)
#define INFO_TIMER_X 86 // 96 + 2 (여백)
#define INFO_TIMER_Y 3  // 첫 번째 구역
#define INFO_TIMER_WIDTH 28
#define INFO_TIMER_HEIGHT 12

// 2-3구역: 상태 아이콘 (32픽셀 높이로 큰 아이콘)
#define INFO_STATUS_X 115     // 중앙 정렬
#define INFO_STATUS_Y 21      // 두 번째 구역 시작
#define INFO_STATUS_WIDTH 16  // 16x16 아이콘
#define INFO_STATUS_HEIGHT 32 // 2구역 합친 높이

// 4구역: L1, L2 연결 상태 (원형)
#define INFO_L1_X 96     // 중앙에서 좌측
#define INFO_L1_Y 54     // 네 번째 구역
#define INFO_L1_RADIUS 5 // 원형 반지름

#define INFO_L2_X 113    // 중앙에서 우측
#define INFO_L2_Y 54     // 네 번째 구역
#define INFO_L2_RADIUS 5 // 원형 반지름

// 색상 정의 (흑백 OLED용)
#define COLOR_WHITE WHITE
#define COLOR_BLACK BLACK

// 아이콘 크기 정의
#define ICON_SIZE_SMALL 8
#define ICON_SIZE_MEDIUM 12
#define ICON_SIZE_LARGE 16

// 타이머 상태 열거형
typedef enum
{
    TIMER_STATUS_STANDBY = 0, // 대기
    TIMER_STATUS_RUNNING = 1, // 실행 중
    TIMER_STATUS_SETTING = 2, // 설정 중
    TIMER_STATUS_COOLING = 3  // 쿨링 중
} Timer_Status_t;

// LED 연결 상태 열거형
typedef enum
{
    LED_DISCONNECTED = 0, // 연결 안됨
    LED_CONNECTED = 1     // 연결됨
} LED_Connection_t;

// UI 상태 구조체
typedef struct
{
    uint8_t battery_percent;       // 배터리 잔량 (0-100%)
    uint8_t timer_minutes;         // 설정된 타이머 분
    uint8_t timer_seconds;         // 설정된 타이머 초
    Timer_Status_t timer_status;   // 타이머 상태
    LED_Connection_t l1_connected; // L1 연결 상태
    LED_Connection_t l2_connected; // L2 연결 상태
    uint8_t cooling_seconds;       // 쿨링 남은 시간 (초)

    // 성능 최적화를 위한 업데이트 제어
    uint32_t progress_update_counter; // 프로그래스바 업데이트 카운터
    uint32_t blink_counter;           // 깜빡임 카운터
    uint8_t force_full_update;        // 전체 화면 강제 업데이트 플래그
    uint8_t timer_indicator_blink;    // 타이머 실행 표시기 깜빡임 상태
} UI_Status_t;

// 타이머 아이콘 비트맵 (8x8)
extern const unsigned char timer_icon_8x8[];

// 배터리 아이콘 비트맵 (8x8)
extern const unsigned char battery_icon_8x8[];

// 재생/정지 아이콘 비트맵 (8x8)
extern const unsigned char play_icon_8x8[];
extern const unsigned char pause_icon_8x8[];

// 조명 아이콘 비트맵 (8x8)
extern const unsigned char light_icon_8x8[];

// 상태 아이콘 비트맵 (8x8)
extern const unsigned char standby_icon_8x8[]; // 대기 상태
extern const unsigned char running_icon_8x8[]; // 실행 상태
extern const unsigned char setting_icon_8x8[]; // 설정 상태
extern const unsigned char cooling_icon_8x8[]; // 쿨링 상태

// 상태 아이콘 비트맵 (16x16) - 큰 아이콘
extern const unsigned char standby_icon_16x16[]; // 대기 상태
extern const unsigned char running_icon_16x16[]; // 실행 상태
extern const unsigned char setting_icon_16x16[]; // 설정 상태
extern const unsigned char cooling_icon_16x16[]; // 쿨링 상태

// 상태 아이콘 비트맵 (19x19) - 더 큰 아이콘
extern const unsigned char standby_icon_19x19[]; // 대기 상태
extern const unsigned char running_icon_19x19[]; // 실행 상태
extern const unsigned char setting_icon_19x19[]; // 설정 상태
extern const unsigned char cooling_icon_19x19[]; // 쿨링 상태

// LED 연결 아이콘 비트맵 (8x8)
extern const unsigned char l1_connected_icon_8x8[];
extern const unsigned char l1_disconnected_icon_8x8[];
extern const unsigned char l2_connected_icon_8x8[];
extern const unsigned char l2_disconnected_icon_8x8[];

// 기본 UI 함수 선언
void UI_Init(void);
void UI_Clear(void);
void UI_DrawFullScreen(UI_Status_t *status);
void UI_DrawFullScreenOptimized(UI_Status_t *status); // 최적화된 업데이트 함수

// 좌측 영역 - 배터리 관련 함수
void UI_DrawBatteryArea(uint8_t percent);
void UI_DrawBatteryProgress(uint8_t percent);
void UI_DrawBatteryPercentage(uint8_t percent);
void UI_DrawTimerIndicator(uint8_t show); // 타이머 실행 표시기 그리기

// 우측 영역 - 정보 표시 함수
void UI_DrawInfoArea(UI_Status_t *status);
void UI_DrawTimerTime(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter);
void UI_DrawTimerStatus(Timer_Status_t status);
void UI_DrawLEDStatus(LED_Connection_t l1_status, LED_Connection_t l2_status);
void UI_DrawCoolingTime(uint8_t seconds);

// 원형 프로그래스바 함수
void UI_DrawCircularProgress(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color);

// 보조 UI 함수 선언
void UI_DrawIcon8x8(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color);
void UI_DrawIcon16x16(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color);
void UI_DrawIcon19x19(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color);
void UI_DrawDigit(uint16_t x, uint16_t y, uint8_t digit, uint16_t color);
void UI_DrawDigitLarge(uint16_t x, uint16_t y, uint8_t digit, uint16_t color, float font_scale);
void UI_DrawTwoDigitsLarge(uint16_t x, uint16_t y, uint8_t value);
void UI_DrawNumber(uint16_t x, uint16_t y, uint16_t number, uint16_t color);
void UI_DrawPercent(uint16_t x, uint16_t y, uint16_t color);
void UI_DrawColon(uint16_t x, uint16_t y, uint16_t color);
void UI_DrawCircle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color, uint8_t filled);
void UI_DrawCircularProgressOptimized(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color, uint8_t should_update);

// 예제 및 테스트 함수 선언
void UI_SystemInit(void);
void UI_UpdateBattery(uint8_t percent);
void UI_UpdateTimerSetting(uint8_t hours, uint8_t minutes);
void UI_ToggleTimerStatus(void);
UI_Status_t *UI_GetCurrentStatus(void);
void UI_DemoTest(void);
void UI_ShowLowBatteryWarning(void);
void UI_ShowTimerComplete(void);
void UI_FadeOut(void);
void UI_UpdateLoop(void);

// 새로운 함수 선언
void UI_DrawTimerValueWithBlink(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter);

#endif