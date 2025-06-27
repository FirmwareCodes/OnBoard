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
#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64

// 영역 정의
// 좌측 상단 - 타이머 상태 영역
#define TIMER_STATUS_X      2
#define TIMER_STATUS_Y      2
#define TIMER_STATUS_WIDTH  40
#define TIMER_STATUS_HEIGHT 16

// 우측 상단 - 타이머 설정값 영역
#define TIMER_VALUE_X       86
#define TIMER_VALUE_Y       2
#define TIMER_VALUE_WIDTH   40
#define TIMER_VALUE_HEIGHT  16

// 중앙 - 배터리 원형 프로그래스 영역
#define BATTERY_CENTER_X    64
#define BATTERY_CENTER_Y    40
#define BATTERY_OUTER_RADIUS 22
#define BATTERY_INNER_RADIUS 18
#define BATTERY_PROGRESS_WIDTH 3

// 배터리 퍼센티지 텍스트 위치
#define BATTERY_PERCENT_X   BATTERY_CENTER_X
#define BATTERY_PERCENT_Y   BATTERY_CENTER_Y

// 색상 정의 (흑백 OLED용)
#define COLOR_WHITE    WHITE
#define COLOR_BLACK    BLACK

// 아이콘 크기 정의
#define ICON_SIZE_SMALL  8
#define ICON_SIZE_MEDIUM 12
#define ICON_SIZE_LARGE  16

// UI 상태 구조체
typedef struct {
    uint8_t battery_percent;    // 배터리 잔량 (0-100%)
    uint8_t timer_hours;        // 설정된 타이머 시간
    uint8_t timer_minutes;      // 설정된 타이머 분
    uint8_t is_timer_running;   // 타이머 실행 상태 (0: 정지, 1: 실행)
    uint8_t is_connected;       // 연결 상태 (필요시 사용)
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

// 기본 UI 함수 선언
void UI_Init(void);
void UI_Clear(void);
void UI_DrawTimerStatus(uint8_t is_running);
void UI_DrawTimerValue(uint8_t hours, uint8_t minutes);
void UI_DrawBatteryProgress(uint8_t percent);
void UI_DrawBatteryPercentage(uint8_t percent);
void UI_DrawFullScreen(UI_Status_t* status);
void UI_DrawCircularProgress(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color);

// 보조 UI 함수 선언
void UI_DrawIcon8x8(uint16_t x, uint16_t y, const unsigned char* icon_data, uint16_t color);
void UI_DrawDigit(uint16_t x, uint16_t y, uint8_t digit, uint16_t color);
void UI_DrawNumber(uint16_t x, uint16_t y, uint16_t number, uint16_t color);
void UI_DrawPercent(uint16_t x, uint16_t y, uint16_t color);
void UI_DrawColon(uint16_t x, uint16_t y, uint16_t color);

// 예제 및 테스트 함수 선언
void UI_SystemInit(void);
void UI_UpdateBattery(uint8_t percent);
void UI_UpdateTimerSetting(uint8_t hours, uint8_t minutes);
void UI_ToggleTimerStatus(void);
UI_Status_t* UI_GetCurrentStatus(void);
void UI_DemoTest(void);
void UI_ShowLowBatteryWarning(void);
void UI_ShowTimerComplete(void);
void UI_FadeOut(void);
void UI_UpdateLoop(void);

// 새로운 함수 선언
void UI_DrawTimerValueWithBlink(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter);

#endif 