/*****************************************************************************
* | File      	:   UI_Display.c
* | Author      :   OnBoard LED Light Timer
* | Function    :   UI Display functions for 1.3inch OLED
* | Info        :   Main UI rendering functions
*----------------
* |	This version:   V1.0
* | Date        :   2024-01-01
* | Info        :   UI implementation
******************************************************************************/

#include "../../Inc/OLED/UI_Layout.h"
#include "../../Inc/OLED/OLED_1in3_c.h"
#include <math.h>
#include <stdio.h>

// 외부 아이콘 데이터 선언
extern const unsigned char timer_icon_8x8[];
extern const unsigned char battery_icon_8x8[];
extern const unsigned char play_icon_8x8[];
extern const unsigned char pause_icon_8x8[];
extern const unsigned char digit_5x7[10][7];
extern const unsigned char percent_5x7[7];
extern const unsigned char colon_3x7[7];

/**
 * @brief UI 초기화 (메인에서 이미 초기화 완료된 상태에서 호출)
 */
void UI_Init(void)
{
    // 메인에서 이미 OLED와 Paint 초기화가 완료된 상태
    // 추가적인 UI 관련 설정만 수행
    
    // 초기 화면 클리어
    Paint_Clear(BLACK);
    OLED_1in3_C_Display(BlackImage);
}

/**
 * @brief 화면 클리어
 */
void UI_Clear(void)
{
    Paint_Clear(BLACK);
}

/**
 * @brief 8x8 비트맵 아이콘 그리기
 */
void UI_DrawIcon8x8(uint16_t x, uint16_t y, const unsigned char* icon_data, uint16_t color)
{
    for(int row = 0; row < 8; row++) {
        unsigned char byte_data = icon_data[row];
        for(int col = 0; col < 8; col++) {
            if(byte_data & (0x80 >> col)) {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 숫자 그리기 (5x7 폰트 사용)
 */
void UI_DrawDigit(uint16_t x, uint16_t y, uint8_t digit, uint16_t color)
{
    if(digit > 9) return;
    
    for(int row = 0; row < 7; row++) {
        unsigned char byte_data = digit_5x7[digit][row];
        for(int col = 0; col < 6; col++) {
            if(byte_data & (0x20 >> col)) {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 숫자 문자열 그리기
 */
void UI_DrawNumber(uint16_t x, uint16_t y, uint16_t number, uint16_t color)
{
    char num_str[4];
    sprintf(num_str, "%d", number);
    
    uint16_t offset_x = 0;
    for(int i = 0; num_str[i] != '\0'; i++) {
        if(num_str[i] >= '0' && num_str[i] <= '9') {
            UI_DrawDigit(x + offset_x, y, num_str[i] - '0', color);
            offset_x += 6;  // 5픽셀 폰트 + 1픽셀 간격
        }
    }
}

/**
 * @brief 퍼센트 기호 그리기
 */
void UI_DrawPercent(uint16_t x, uint16_t y, uint16_t color)
{
    for(int row = 0; row < 7; row++) {
        unsigned char byte_data = percent_5x7[row];
        for(int col = 0; col < 5; col++) {
            if(byte_data & (0x10 >> col)) {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 콜론 그리기
 */
void UI_DrawColon(uint16_t x, uint16_t y, uint16_t color)
{
    for(int row = 0; row < 7; row++) {
        unsigned char byte_data = colon_3x7[row];
        for(int col = 0; col < 3; col++) {
            if(byte_data & (0x04 >> col)) {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 원형 프로그래스바 그리기
 * @param center_x: 중심 X 좌표
 * @param center_y: 중심 Y 좌표  
 * @param radius: 반지름
 * @param progress: 진행률 (0-100)
 * @param color: 색상
 */
void UI_DrawCircularProgress(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color)
{
    // 외곽 원 그리기 (더 두꺼운 테두리)
    Paint_DrawCircle(center_x, center_y, radius, color, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    Paint_DrawCircle(center_x, center_y, radius-1, color, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    
    // 진행률에 따른 호 그리기 (시계 12시 방향부터 시작)
    float angle_per_percent = 360.0f / 100.0f;
    float target_angle = progress * angle_per_percent;
    
    for(int angle = 0; angle < (int)target_angle; angle += 1) {
        float radian = (angle - 90) * M_PI / 180.0f;  // -90도로 12시 방향 시작
        
        // 더 두꺼운 프로그래스바 (두께 5픽셀)
        for(int thickness = 0; thickness < 5; thickness++) {
            int x = center_x + (radius - 2 - thickness) * cos(radian);
            int y = center_y + (radius - 2 - thickness) * sin(radian);
            Paint_SetPixel(x, y, color);
        }
    }
}

/**
 * @brief 좌측 상단 타이머 상태 표시
 * @param is_running: 타이머 실행 상태 (0: 정지, 1: 실행)
 */
void UI_DrawTimerStatus(uint8_t is_running)
{
    // 타이머 아이콘 그리기
    UI_DrawIcon8x8(TIMER_STATUS_X, TIMER_STATUS_Y, timer_icon_8x8, COLOR_WHITE);
    
    // 재생/일시정지 아이콘 그리기
    if(is_running) {
        UI_DrawIcon8x8(TIMER_STATUS_X + 10, TIMER_STATUS_Y, pause_icon_8x8, COLOR_WHITE);
    } else {
        UI_DrawIcon8x8(TIMER_STATUS_X + 10, TIMER_STATUS_Y, play_icon_8x8, COLOR_WHITE);
    }
}

/**
 * @brief 우측 상단 타이머 설정값 표시
 * @param hours: 시간
 * @param minutes: 분
 */
void UI_DrawTimerValue(uint8_t hours, uint8_t minutes)
{
    uint16_t x_pos = TIMER_VALUE_X;
    uint16_t y_pos = TIMER_VALUE_Y;
    
    // 시간 표시 (2자리)
    if(hours >= 10) {
        UI_DrawDigit(x_pos, y_pos, hours / 10, COLOR_WHITE);
        UI_DrawDigit(x_pos + 6, y_pos, hours % 10, COLOR_WHITE);
    } else {
        UI_DrawDigit(x_pos, y_pos, 0, COLOR_WHITE);
        UI_DrawDigit(x_pos + 6, y_pos, hours, COLOR_WHITE);
    }
    
    // 콜론 그리기
    UI_DrawColon(x_pos + 12, y_pos, COLOR_WHITE);
    
    // 분 표시 (2자리)
    if(minutes >= 10) {
        UI_DrawDigit(x_pos + 16, y_pos, minutes / 10, COLOR_WHITE);
        UI_DrawDigit(x_pos + 22, y_pos, minutes % 10, COLOR_WHITE);
    } else {
        UI_DrawDigit(x_pos + 16, y_pos, 0, COLOR_WHITE);
        UI_DrawDigit(x_pos + 22, y_pos, minutes, COLOR_WHITE);
    }
}

/**
 * @brief 중앙 배터리 프로그래스 표시
 * @param percent: 배터리 퍼센티지 (0-100)
 */
void UI_DrawBatteryProgress(uint8_t percent)
{
    // 원형 프로그래스바 그리기
    UI_DrawCircularProgress(BATTERY_CENTER_X, BATTERY_CENTER_Y, BATTERY_OUTER_RADIUS, percent, COLOR_WHITE);
}

/**
 * @brief 배터리 퍼센티지 숫자 표시 (더 큰 크기)
 * @param percent: 배터리 퍼센티지 (0-100)
 */
void UI_DrawBatteryPercentage(uint8_t percent)
{
    uint16_t base_x = BATTERY_PERCENT_X - 15; // 중앙 정렬을 위한 오프셋 (더 큰 폰트용)
    uint16_t base_y = BATTERY_PERCENT_Y - 5;  // 중앙 정렬을 위한 오프셋
    
    // 100% 처리
    if(percent == 100) {
        UI_DrawDigit(base_x, base_y, 1, COLOR_WHITE);
        UI_DrawDigit(base_x + 8, base_y, 0, COLOR_WHITE);
        UI_DrawDigit(base_x + 16, base_y, 0, COLOR_WHITE);
        UI_DrawPercent(base_x + 24, base_y, COLOR_WHITE);
    }
    // 10-99% 처리
    else if(percent >= 10) {
        UI_DrawDigit(base_x + 4, base_y, percent / 10, COLOR_WHITE);
        UI_DrawDigit(base_x + 12, base_y, percent % 10, COLOR_WHITE);
        UI_DrawPercent(base_x + 20, base_y, COLOR_WHITE);
    }
    // 0-9% 처리
    else {
        UI_DrawDigit(base_x + 8, base_y, percent, COLOR_WHITE);
        UI_DrawPercent(base_x + 16, base_y, COLOR_WHITE);
    }
}

/**
 * @brief 전체 화면 그리기
 * @param status: UI 상태 구조체
 */
void UI_DrawFullScreen(UI_Status_t* status)
{
    // 화면 클리어
    UI_Clear();
    
    // 좌측 상단: 타이머 상태
    UI_DrawTimerStatus(status->is_timer_running);
    
    // 우측 상단: 타이머 설정값
    UI_DrawTimerValue(status->timer_hours, status->timer_minutes);
    
    // 중앙: 배터리 프로그래스
    UI_DrawBatteryProgress(status->battery_percent);
    
    // 중앙: 배터리 퍼센티지
    UI_DrawBatteryPercentage(status->battery_percent);
    
    // 화면 업데이트
    OLED_1in3_C_Display(BlackImage);
} 