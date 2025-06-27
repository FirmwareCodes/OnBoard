/*****************************************************************************
 * | File      	:   UI_Display.c
 * | Author      :   OnBoard LED Light Timer
 * | Function    :   UI Display functions for 1.3inch OLED
 * | Info        :   New Layout: Left 96x64 Battery Area + Right 32x64 Info Area
 *----------------
 * |	This version:   V2.0
 * | Date        :   2024-01-01
 * | Info        :   Redesigned UI implementation
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
extern const unsigned char light_icon_8x8[];
extern const unsigned char standby_icon_8x8[];
extern const unsigned char running_icon_8x8[];
extern const unsigned char setting_icon_8x8[];
extern const unsigned char cooling_icon_8x8[];
extern const unsigned char standby_icon_16x16[];
extern const unsigned char running_icon_16x16[];
extern const unsigned char setting_icon_16x16[];
extern const unsigned char cooling_icon_16x16[];
extern const unsigned char standby_icon_19x19[];
extern const unsigned char running_icon_19x19[];
extern const unsigned char setting_icon_19x19[];
extern const unsigned char cooling_icon_19x19[];
extern const unsigned char l1_connected_icon_8x8[];
extern const unsigned char l1_disconnected_icon_8x8[];
extern const unsigned char l2_connected_icon_8x8[];
extern const unsigned char l2_disconnected_icon_8x8[];
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
void UI_DrawIcon8x8(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color)
{
    for (int row = 0; row < 8; row++)
    {
        unsigned char byte_data = icon_data[row];
        for (int col = 0; col < 8; col++)
        {
            if (byte_data & (0x80 >> col))
            {
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
    if (digit > 9)
        return;

    for (int row = 0; row < 7; row++)
    {
        unsigned char byte_data = digit_5x7[digit][row];
        for (int col = 0; col < 6; col++)
        {
            if (byte_data & (0x20 >> col))
            {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 큰 숫자 그리기 (5x7 폰트를 2배 확대)
 */
void UI_DrawDigitLarge(uint16_t x, uint16_t y, uint8_t digit, uint16_t color)
{
    if (digit > 9)
        return;

    for (int row = 0; row < 7; row++)
    {
        unsigned char byte_data = digit_5x7[digit][row];
        for (int col = 0; col < 6; col++)
        {
            if (byte_data & (0x20 >> col))
            {
                // 2x2 픽셀로 확대
                Paint_SetPixel(x + col * 2, y + row * 2, color);
                Paint_SetPixel(x + col * 2 + 1, y + row * 2, color);
                Paint_SetPixel(x + col * 2, y + row * 2 + 1, color);
                Paint_SetPixel(x + col * 2 + 1, y + row * 2 + 1, color);
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
    for (int i = 0; num_str[i] != '\0'; i++)
    {
        if (num_str[i] >= '0' && num_str[i] <= '9')
        {
            UI_DrawDigit(x + offset_x, y, num_str[i] - '0', color);
            offset_x += 6; // 5픽셀 폰트 + 1픽셀 간격
        }
    }
}

/**
 * @brief 퍼센트 기호 그리기
 */
void UI_DrawPercent(uint16_t x, uint16_t y, uint16_t color)
{
    for (int row = 0; row < 7; row++)
    {
        unsigned char byte_data = percent_5x7[row];
        for (int col = 0; col < 5; col++)
        {
            if (byte_data & (0x10 >> col))
            {
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
    for (int row = 0; row < 7; row++)
    {
        unsigned char byte_data = colon_3x7[row];
        for (int col = 0; col < 3; col++)
        {
            if (byte_data & (0x04 >> col))
            {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 16x16 비트맵 아이콘 그리기
 */
void UI_DrawIcon16x16(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color)
{
    for (int row = 0; row < 16; row++)
    {
        uint16_t word_data = (icon_data[row * 2] << 8) | icon_data[row * 2 + 1];
        for (int col = 0; col < 16; col++)
        {
            if (word_data & (0x8000 >> col))
            {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 19x19 비트맵 아이콘 그리기
 */
void UI_DrawIcon19x19(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color)
{
    for (int row = 0; row < 19; row++)
    {
        // 19비트 데이터를 3바이트로 처리 (24비트 중 19비트 사용)
        uint32_t data = (icon_data[row * 3] << 16) | (icon_data[row * 3 + 1] << 8) | icon_data[row * 3 + 2];

        for (int col = 0; col < 19; col++)
        {
            if (data & (0x800000 >> col))
            { // 최상위 비트부터 19비트 확인
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

/**
 * @brief 원형 그리기 (채움/빈 원형)
 */
void UI_DrawCircle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color, uint8_t filled)
{
    if (filled)
    {
        // 채워진 원형
        Paint_DrawCircle(x, y, radius, color, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    }
    else
    {
        // 빈 원형 (테두리만)
        Paint_DrawCircle(x, y, radius, color, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    }
}

/**
 * @brief 원형 프로그래스바 그리기 (개선된 버전 - 빈 공간 완전 제거)
 * @param center_x: 중심 X 좌표
 * @param center_y: 중심 Y 좌표
 * @param radius: 반지름
 * @param progress: 진행률 (0-100)
 * @param color: 색상
 */
void UI_DrawCircularProgress(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color)
{
    // 외곽 원 그리기 (더 두꺼운 테두리 - 빈 픽셀 완전 제거)
    // for (int r = 0; r < 3; r++)
    // {
    //     // 원 둘레를 조밀하게 그리기
    //     for (int angle = 0; angle < 360; angle++)
    //     {
    //         float radian = angle * M_PI / 180.0f;
    //         int x = center_x + (radius - r) * cos(radian);
    //         int y = center_y + (radius - r) * sin(radian);

    //         // 주변 픽셀도 채워서 빈 공간 완전 제거
    //         Paint_SetPixel(x, y, color);
    //         Paint_SetPixel(x + 1, y, color);
    //         Paint_SetPixel(x, y + 1, color);
    //         Paint_SetPixel(x - 1, y, color);
    //         Paint_SetPixel(x, y - 1, color);
    //     }
    // }

    Paint_DrawCircle(center_x, center_y, radius-2, color, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    Paint_DrawCircle(center_x, center_y, radius-7, color, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

    // 진행률에 따른 호 그리기 (시계 12시 방향부터 시작)
    float angle_per_percent = 360.0f / 100.0f;
    float target_angle = progress * angle_per_percent;

    // 매우 조밀하게 그리기 (0.25도 간격)
    for (float angle = 0; angle < target_angle; angle += 0.25f)
    {
        float radian = (angle - 90) * M_PI / 180.0f; // -90도로 12시 방향 시작

        // 더 두꺼운 프로그래스바 (두께 8픽셀) - 매우 조밀하게
        for (int thickness = 0; thickness < 4; thickness++)
        {
            int x = center_x + (radius - 3 - thickness) * cos(radian);
            int y = center_y + (radius - 3 - thickness) * sin(radian);

            // 9방향 픽셀 모두 채우기
            for (int dx = -1; dx <= 1; dx++)
            {
                for (int dy = -1; dy <= 1; dy++)
                {
                    Paint_SetPixel(x + dx, y + dy, color);
                }
            }
        }
    }
}

/**
 * @brief 좌측 배터리 영역 그리기 (96x64)
 * @param percent: 배터리 퍼센티지 (0-100)
 */
void UI_DrawBatteryArea(uint8_t percent)
{
    // 영역 경계선 그리기 (선택사항)
    Paint_DrawLine(LEFT_AREA_WIDTH, 0, LEFT_AREA_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);

    // 배터리 프로그래스바 그리기
    UI_DrawBatteryProgress(percent);

    // 배터리 퍼센티지 그리기
    UI_DrawBatteryPercentage(percent);
}

/**
 * @brief 배터리 원형 프로그래스바 그리기
 * @param percent: 배터리 퍼센티지 (0-100)
 */
void UI_DrawBatteryProgress(uint8_t percent)
{
    // 원형 프로그래스바 그리기 (더 큰 크기)
    UI_DrawCircularProgress(BATTERY_CENTER_X, BATTERY_CENTER_Y, BATTERY_OUTER_RADIUS, percent, COLOR_WHITE);
}

/**
 * @brief 배터리 퍼센티지 숫자 표시 (더 큰 크기)
 * @param percent: 배터리 퍼센티지 (0-100)
 */
void UI_DrawBatteryPercentage(uint8_t percent)
{
    uint16_t base_x = BATTERY_PERCENT_X - 18; // 더 큰 폰트를 위한 중앙 정렬 조정
    uint16_t base_y = BATTERY_PERCENT_Y - 7;  // 더 큰 폰트를 위한 중앙 정렬 조정

    // 100% 처리 (3자리 숫자)
    if (percent == 100)
    {
        UI_DrawDigitLarge(base_x, base_y, 1, COLOR_WHITE);
        UI_DrawDigitLarge(base_x + 11, base_y, 0, COLOR_WHITE);
        UI_DrawDigitLarge(base_x + 24, base_y, 0, COLOR_WHITE);
    }
    // 10-99% 처리 (2자리 숫자)
    else if (percent >= 10)
    {
        UI_DrawDigitLarge(base_x + 5, base_y, percent / 10, COLOR_WHITE);
        UI_DrawDigitLarge(base_x + 19, base_y, percent % 10, COLOR_WHITE);
    }
    // 0-9% 처리 (1자리 숫자)
    else
    {
        UI_DrawDigitLarge(base_x + 12, base_y, percent, COLOR_WHITE);
    }
}

/**
 * @brief 우측 정보 영역 그리기 (32x64, 4등분)
 * @param status: UI 상태 구조체
 */
void UI_DrawInfoArea(UI_Status_t *status)
{
    static uint32_t blink_counter = 0;
    blink_counter++;

    // 1구역: 타이머 시간 표시 (분:초)
    UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                     (status->timer_status == TIMER_STATUS_SETTING), blink_counter);

    // 2-3구역: 타이머 상태 아이콘 표시 (19x19 큰 아이콘, 중앙 정렬)
    UI_DrawTimerStatus(status->timer_status);

    // 4구역: LED 연결 상태 표시 (원형)
    UI_DrawLEDStatus(status->l1_connected, status->l2_connected);
}

/**
 * @brief 타이머 시간 표시 (1구역 - 분:초)
 * @param minutes: 분
 * @param seconds: 초
 * @param should_blink: 깜빡임 여부
 * @param blink_counter: 깜빡임 카운터
 */
void UI_DrawTimerTime(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter)
{
    uint16_t x_pos = INFO_TIMER_X;
    uint16_t y_pos = INFO_TIMER_Y;

    // 깜빡임 효과: 30프레임마다 토글 (약 1.5초 주기)
    uint8_t show_text = 1;
    if (should_blink && ((blink_counter / 30) % 2 == 0))
    {
        show_text = 0; // 숨김
    }

    if (show_text)
    {
        // 분 표시 (1자리, 공간 절약)
        UI_DrawDigit(x_pos, y_pos, minutes, COLOR_WHITE);

        // 콜론 그리기
        UI_DrawColon(x_pos + 6, y_pos, COLOR_WHITE);

        // 초 표시 (2자리)
        if (seconds >= 10)
        {
            UI_DrawDigit(x_pos + 10, y_pos, seconds / 10, COLOR_WHITE);
            UI_DrawDigit(x_pos + 16, y_pos, seconds % 10, COLOR_WHITE);
        }
        else
        {
            UI_DrawDigit(x_pos + 10, y_pos, 0, COLOR_WHITE);
            UI_DrawDigit(x_pos + 16, y_pos, seconds, COLOR_WHITE);
        }
    }
}

/**
 * @brief 타이머 상태 아이콘 표시 (2-3구역 - 19x19 큰 아이콘, 중앙 정렬)
 * @param status: 타이머 상태
 */
void UI_DrawTimerStatus(Timer_Status_t status)
{
    // 우측 영역 중앙 정렬 계산 (32픽셀 폭에서 19픽셀 아이콘 중앙)
    uint16_t center_x = INFO_AREA_X + (INFO_AREA_WIDTH / 2) - (19 / 2);      // 약 106
    uint16_t center_y = INFO_STATUS_Y + (INFO_STATUS_HEIGHT / 2) - (19 / 2); // 약 25

    switch (status)
    {
    case TIMER_STATUS_STANDBY:
        UI_DrawIcon19x19(center_x, center_y, standby_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_RUNNING:
        UI_DrawIcon19x19(center_x, center_y, running_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_SETTING:
        UI_DrawIcon19x19(center_x, center_y, setting_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_COOLING:
        UI_DrawIcon19x19(center_x, center_y, cooling_icon_19x19, COLOR_WHITE);
        break;
    }
}

/**
 * @brief LED 연결 상태 표시 (4구역 - 원형)
 * @param l1_status: L1 연결 상태
 * @param l2_status: L2 연결 상태
 */
void UI_DrawLEDStatus(LED_Connection_t l1_status, LED_Connection_t l2_status)
{
    // L1 상태 표시 (원형)
    if (l1_status == LED_CONNECTED)
    {
        // 연결됨: 채워진 원형
        UI_DrawCircle(INFO_L1_X, INFO_L1_Y, INFO_L1_RADIUS, COLOR_WHITE, 1);
    }
    else
    {
        // 연결 안됨: 빈 원형
        UI_DrawCircle(INFO_L1_X, INFO_L1_Y, INFO_L1_RADIUS, COLOR_WHITE, 0);
    }

    // L2 상태 표시 (원형)
    if (l2_status == LED_CONNECTED)
    {
        // 연결됨: 채워진 원형
        UI_DrawCircle(INFO_L2_X, INFO_L2_Y, INFO_L2_RADIUS, COLOR_WHITE, 1);
    }
    else
    {
        // 연결 안됨: 빈 원형
        UI_DrawCircle(INFO_L2_X, INFO_L2_Y, INFO_L2_RADIUS, COLOR_WHITE, 0);
    }
}

/**
 * @brief 쿨링 시간 표시 (사용 안함 - 상태 아이콘으로 대체)
 */
void UI_DrawCoolingTime(uint8_t seconds)
{
    // 쿨링 시간은 상태 아이콘으로 표시하므로 별도 표시 안함
    UNUSED(seconds);
}

/**
 * @brief 전체 화면 그리기 (새로운 레이아웃)
 * @param status: UI 상태 구조체
 */
void UI_DrawFullScreen(UI_Status_t *status)
{
    // 화면 클리어
    UI_Clear();

    // 좌측 영역: 배터리 (96x64)
    UI_DrawBatteryArea(status->battery_percent);

    // 우측 영역: 정보 (32x64)
    UI_DrawInfoArea(status);

    // 화면 테두리(삭제 금지)
    Paint_DrawRectangle(1, 1, 128, 64, WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

    // 화면 업데이트
    OLED_1in3_C_Display(BlackImage);
}