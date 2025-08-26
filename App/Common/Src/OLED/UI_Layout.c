/*****************************************************************************
 * | File      	:   UI_Display.c
 * | Author      :   Choi GeonHyeong
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

// 외부 변수 선언 (freertos.c에서 정의된 UI 상태)
extern UI_Status_t current_status;

extern const unsigned char standby_icon_19x19[];
extern const unsigned char running_icon_19x19[];
extern const unsigned char setting_icon_19x19[];
extern const unsigned char cooling_icon_19x19[];
extern const unsigned char warning_icon_19x19[];

extern const unsigned char percent_12x12[];
extern const unsigned char exclamation_12x12[];

extern const unsigned char digit_5x7[10][7];
extern const unsigned char colon_3x7[7];

extern bool is_half_second_tick;

// 최적화를 위한 전역 변수
static float sin_table[720] = {0}; // 0.5도 간격으로 360도 * 2
static float cos_table[720] = {0};
static uint8_t lookup_table_initialized = 0;

/**
 * @brief 삼각함수 룩업 테이블 초기화
 */
static void init_trig_lookup_table(void)
{
    if (lookup_table_initialized)
        return;

    for (int i = 0; i < 720; i++)
    {
        float angle = (i * 0.5f - 90.0f) * M_PI / 180.0f; // -90도부터 시작 (12시 방향)
        sin_table[i] = sin(angle);
        cos_table[i] = cos(angle);
    }
    lookup_table_initialized = 1;
}

/**
 * @brief UI 초기화
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
void UI_DrawDigitLarge(uint16_t x, uint16_t y, uint8_t digit, uint16_t color, float font_scale)
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
                Paint_SetPixel(x + col * font_scale, y + row * font_scale, color);
                Paint_SetPixel(x + col * font_scale + 1, y + row * font_scale, color);
                Paint_SetPixel(x + col * font_scale, y + row * font_scale + 1, color);
                Paint_SetPixel(x + col * font_scale + 1, y + row * font_scale + 1, color);
            }
        }
    }
}

/**
 * @brief 큰 숫자 2자리 그리기
 */
void UI_DrawTwoDigitsLarge(uint16_t x, uint16_t y, uint8_t value)
{
    // 10의 자리 숫자 그리기
    uint8_t tens = value / 10;
    uint8_t ones = value % 10;

    UI_DrawDigitLarge(x, y, tens, COLOR_WHITE, 2);
    UI_DrawDigitLarge(x + 12, y, ones, COLOR_WHITE, 2); // 12픽셀 간격 (2배 확대된 6픽셀 폰트)
}

/**
 * @brief 숫자 문자열 그리기
 */
void UI_DrawNumber(uint16_t x, uint16_t y, uint16_t number, uint16_t color)
{
    char num_str[5];
    sprintf(num_str, "%d", (uint8_t)number);

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
 * @brief 12x16 비트맵 아이콘 그리기
 */
void UI_DrawIcon12x16(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color)
{
    for (int row = 0; row < 12; row++)
    {
        uint16_t data = (icon_data[row * 2] << 8) | icon_data[row * 2 + 1];

        for (int col = 0; col < 16; col++)
        {
            if (data & (0x8000 >> col))
            {
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
 * @brief 최적화된 원형 호 그리기 (룩업 테이블 기반)
 * @param center_x: 중심 X 좌표
 * @param center_y: 중심 Y 좌표
 * @param radius: 반지름
 * @param start_angle: 시작 각도 (도)
 * @param end_angle: 끝 각도 (도)
 * @param color: 색상
 * @param thickness: 두께
 */
static void draw_optimized_arc(uint16_t center_x, uint16_t center_y, uint16_t radius,
                               float start_angle, float end_angle, uint16_t color, int thickness)
{
    // 각도를 인덱스로 변환 (0.5도 간격)
    int start_index = (int)(start_angle * 2.0f);
    int end_index = (int)(end_angle * 2.0f);
    if (end_index > 720)
        end_index = 720;

    // 각 두께별로 한 번에 처리
    for (int t = 0; t < thickness; t++)
    {
        int current_radius = radius - t;
        if (current_radius < 5)
            continue;

        int prev_x = -999, prev_y = -999; // 이전 픽셀 좌표 (초기값은 유효하지 않은 값)

        // 0.5도 간격으로 호 그리기
        for (int i = start_index; i < end_index; i += 1)
        {
            int x = center_x + (int)(current_radius * cos_table[i]);
            int y = center_y + (int)(current_radius * sin_table[i]);

            // 메인 픽셀
            Paint_SetPixel(x, y, color);

            // 이전 픽셀과의 간격이 1보다 크면 중간 픽셀 채우기 (최적화)
            if (prev_x != -999 && prev_y != -999)
            {
                int dx = x - prev_x;
                int dy = y - prev_y;

                // 간격이 클 때만 중간 픽셀 채우기
                if (abs(dx) > 1 || abs(dy) > 1)
                {
                    int mid_x = prev_x + dx / 2;
                    int mid_y = prev_y + dy / 2;
                    Paint_SetPixel(mid_x, mid_y, color);

                    if (abs(dx) > 2 || abs(dy) > 2)
                    {
                        Paint_SetPixel(prev_x + dx / 3, prev_y + dy / 3, color);
                        Paint_SetPixel(prev_x + (dx * 2) / 3, prev_y + (dy * 2) / 3, color);
                    }
                }
            }

            prev_x = x;
            prev_y = y;
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
 * @param should_update: 업데이트 여부
 */
void UI_DrawCircularProgressOptimized(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color, uint8_t should_update)
{
    if (!should_update)
    {
        return; // 업데이트가 필요하지 않으면 스킵
    }

    // 룩업 테이블 초기화 (최초 1회만)
    init_trig_lookup_table();

    // 기존 프로그래스바 영역 클리어
    Paint_DrawCircle(center_x, center_y, radius, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    const int inner_radius = radius - 10;
    const int progress_start_radius = radius - 1;

    // 진행률이 0이면 테두리만 그리고 종료
    if (progress == 0)
        return;

    // 진행률에 따른 각도 계산 (0도부터 시계방향)
    float progress_angle = (progress * 360.0f) / 100.0f;

    // 최적화된 프로그래스바 그리기 - 단일 함수로 통합
    int progress_thickness = progress_start_radius - inner_radius; // 실제 두께 계산
    if (progress_thickness > 10)
        progress_thickness = 10; // 최대 두께 제한

    draw_optimized_arc(center_x, center_y, progress_start_radius, 0, progress_angle, color, progress_thickness);

    // 시작점과 끝점에 둥근 캡 추가
    if (progress > 3) // 최소 진행률이 있을 때만
    {
        // 시작점 캡 (12시 방향) - 3x3에서 2x2로 축소
        int start_x = center_x;
        int start_y = center_y - (radius - 4);

        Paint_SetPixel(start_x, start_y, color);
        Paint_SetPixel(start_x + 1, start_y, color);
        Paint_SetPixel(start_x, start_y + 1, color);
        Paint_SetPixel(start_x + 1, start_y + 1, color);

        // 끝점 캡 - 3x3에서 2x2로 축소
        if (progress > 8)
        {
            float end_angle_rad = (progress_angle - 90) * M_PI / 180.0f;
            int end_x = center_x + (int)((radius - 4) * cos(end_angle_rad));
            int end_y = center_y + (int)((radius - 4) * sin(end_angle_rad));

            Paint_SetPixel(end_x, end_y, color);
            Paint_SetPixel(end_x + 1, end_y, color);
            Paint_SetPixel(end_x, end_y + 1, color);
            Paint_SetPixel(end_x + 1, end_y + 1, color);
        }
    }
}

/**
 * @brief 타이머 실행 표시기 그리기 (좌측 상단 원형)
 * @param show: 표시 여부 (1: 표시, 0: 숨김)
 */
void UI_DrawTimerIndicator(uint8_t show)
{
    // 표시기 영역 클리어
    Paint_DrawRectangle(TIMER_INDICATOR_X - TIMER_INDICATOR_RADIUS - 1,
                        TIMER_INDICATOR_Y - TIMER_INDICATOR_RADIUS - 1,
                        TIMER_INDICATOR_X + TIMER_INDICATOR_RADIUS + 1,
                        TIMER_INDICATOR_Y + TIMER_INDICATOR_RADIUS + 1,
                        COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    if (show)
    {
        // 채워진 원형 표시기 그리기
        UI_DrawCircle(TIMER_INDICATOR_X, TIMER_INDICATOR_Y, TIMER_INDICATOR_RADIUS, COLOR_WHITE, 1);
    }
}

/**
 * @brief 좌측 배터리 영역 그리기 (96x64)
 * @param voltage: 배터리 전압 (V)
 * @param status: UI 상태 구조체 (애니메이션 처리용)
 */
void UI_DrawBatteryArea(float voltage, UI_Status_t *status)
{
    // 현재 전압 확인 (애니메이션 중이면 애니메이션 전압 사용)
    float current_voltage = status->init_animation_active ? status->animation_voltage : voltage;

    // LOW BAT 상태일 때는 배터리 영역의 다른 요소들을 그리지 않음
    if (current_voltage <= CRITICAL_BATTERY_VOLTAGE && !status->init_animation_active)
    {
        // 배터리 영역 전체 완전히 클리어 (좌측 96x64 영역)
        Paint_DrawRectangle(0, 0, LEFT_AREA_WIDTH, SCREEN_HEIGHT, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

        // LOW BAT 알람 표시 (빠른 깜빡임 - 0.5초 주기) - 시스템 틱 기반으로 정확한 주기 보장
        uint32_t current_tick = xTaskGetTickCount();
        uint32_t half_second_ticks = 500 / portTICK_PERIOD_MS;        // 0.5초를 틱으로 변환
        uint8_t blink_state = (current_tick / half_second_ticks) % 2; // 0.5초 주기로 깜빡임
        draw_low_battery_alarm(BATTERY_CENTER_X, BATTERY_CENTER_Y, BATTERY_OUTER_RADIUS, blink_state);

        return; // LOW BAT 상태에서는 다른 요소들 그리지 않음
    }

    // 전압 기반 프로그래스바 그리기
    if ((uint16_t)(current_voltage * 10) != (uint16_t)(status->last_battery_voltage * 10))
    {
        // 정상 상태로 복귀 시 배터리 영역 완전 클리어
        if (current_voltage > CRITICAL_BATTERY_VOLTAGE)
        {
            Paint_DrawRectangle(0, 0, LEFT_AREA_WIDTH, SCREEN_HEIGHT, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
        }

        if (status->timer_status == TIMER_STATUS_RUNNING)
        {
            UI_DrawTimerIndicator(is_half_second_tick);
        }
        else
        {
            UI_DrawTimerIndicator(0);
        }

        status->last_battery_voltage = current_voltage;
        UI_DrawVoltageProgress(voltage, status);
        UI_DrawBatteryVoltage(current_voltage);
    }
}

/**
 * @brief LOW BAT 알람 표시 - 네모 배터리 형태
 * @param center_x: 중심 X 좌표
 * @param center_y: 중심 Y 좌표
 * @param radius: 반지름
 * @param blink_state: 깜빡임 상태 (0: 꺼짐, 1: 켜짐)
 */
void draw_low_battery_alarm(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t blink_state)
{
    UNUSED(blink_state);
    UNUSED(radius);

    // 배터리 영역 전체 클리어 (좌측 96x64 영역) - 잔상 완전 제거
    Paint_DrawRectangle(0, 0, LEFT_AREA_WIDTH, SCREEN_HEIGHT, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // 큰 네모 배터리 그리기
    uint16_t battery_width = 55;                              // 배터리 본체 너비
    uint16_t battery_height = 35;                             // 배터리 본체 높이
    uint16_t battery_x = center_x - battery_width / 2;        // 배터리 X 시작점
    uint16_t battery_y = (center_y - battery_height / 2) - 5; // 배터리 Y 시작점

    // 배터리 양극 단자 크기
    uint16_t terminal_width = 4;
    uint16_t terminal_height = 12;
    uint16_t terminal_x = battery_x + battery_width;
    uint16_t terminal_y = battery_y + (battery_height - terminal_height) / 2;

    // 배터리 본체 테두리 (단일 테두리로 단순화)
    Paint_DrawRectangle(battery_x, battery_y,
                        battery_x + battery_width, battery_y + battery_height,
                        COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

    // 배터리 내부 클리어
    Paint_DrawRectangle(battery_x + 1, battery_y + 1,
                        battery_x + battery_width - 1, battery_y + battery_height - 1,
                        COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // 배터리 양극 단자 그리기
    Paint_DrawRectangle(terminal_x, terminal_y,
                        terminal_x + terminal_width, terminal_y + terminal_height,
                        COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // LOW BAT 텍스트 (배터리 내부에)
    const char *low_text = "LOW";
    const char *low_text2 = "BATTERY";
    uint16_t text_x = battery_x + 14;  // 배터리 내부 중앙 정렬
    uint16_t text_x2 = battery_x + 3;  // 배터리 내부 중앙 정렬
    uint16_t text_y1 = battery_y + 6;  // 첫 번째 줄 (위쪽)
    uint16_t text_y2 = battery_y + 18; // 두 번째 줄 (아래쪽)

    Paint_DrawString_EN(text_x, text_y1, low_text, &Font12, COLOR_WHITE, COLOR_BLACK);
    Paint_DrawString_EN(text_x2, text_y2, low_text2, &Font12, COLOR_WHITE, COLOR_BLACK);

    // "Please Charge" 메시지 (배터리 아래)
    const char *charge_text1 = "Please Charge";
    uint16_t charge_x1 = 5;  // 중앙 정렬 (Please)
    uint16_t charge_y1 = 53; // 배터리 바로 아래

    Paint_DrawString_EN(charge_x1, charge_y1, charge_text1, &Font8, COLOR_WHITE, COLOR_BLACK);
}

/**
 * @brief 전압 기반 원형 프로그래스바 그리기
 * @param voltage: 배터리 전압 (19.0V ~ 24.7V)
 * @param status: UI 상태 구조체 (애니메이션 처리용)
 */
void UI_DrawVoltageProgress(float voltage, UI_Status_t *status)
{
    // 전압을 퍼센트로 변환 (19.0V = 0%, 24.7V = 100%)
    const float MIN_VOLTAGE = 18.6f; // 프로그래스바 최소 전압
    const float MAX_VOLTAGE = 24.0f; // 프로그래스바 최대 전압

    // 애니메이션 중이면 애니메이션 전압 사용, 아니면 실제 전압 사용
    float current_voltage = status->init_animation_active ? status->animation_voltage : voltage;
    // 점진적 변화를 위한 퍼센트 계산
    float voltage_percent;
    if (status->init_animation_active)
    {
        // 애니메이션 중에는 애니메이션 전압 기반 계산
        voltage_percent = ((current_voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)) * 100.0f;
    }
    else
    {
        // 폴백: 현재 실측 퍼센트 사용
        voltage_percent = status->battery_percentage;
    }

    // 범위 제한
    if (voltage_percent < 0.0f)
        voltage_percent = 0.0f;
    if (voltage_percent > 100.0f)
        voltage_percent = 100.0f;

    uint8_t progress = (uint8_t)voltage_percent;

    // 프로그래스바 상승에 둔감함 추가
    if ((voltage_percent - status->last_battery_percentage) > 2)
    {
        status->last_battery_percentage = voltage_percent;
    }
    else if (voltage_percent < status->last_battery_percentage)
    {
        status->last_battery_percentage = voltage_percent;
    }
    else if (!status->init_animation_active && voltage_percent != 100)
    {
        progress = status->last_battery_percentage;
    }

    // 경고 전압 이하일 때 경고, 그 외에는 흰색
    uint16_t progress_color = (current_voltage < WARNING_BATTERY_VOLTAGE) ? COLOR_WHITE : COLOR_WHITE;

    // 원형 프로그래스바 그리기
    UI_DrawCircularProgressOptimized(BATTERY_CENTER_X, BATTERY_CENTER_Y, BATTERY_OUTER_RADIUS, progress, progress_color, 1);

    // Paint_DrawLine(56, 21, 68, 15, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    // Paint_DrawLine(55, 20, 68, 14, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    Paint_DrawLine(55, 20, 65, 10, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    Paint_DrawLine(55, 21, 65, 11, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    Paint_DrawLine(56, 21, 66, 11, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    Paint_DrawLine(56, 22, 66, 12, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);

    Paint_DrawLine(57, 22, 67, 12, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    Paint_DrawLine(57, 23, 67, 13, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);

    Paint_DrawLine(54, 19, 64, 9, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    Paint_DrawLine(54, 20, 64, 10, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);

    // 배터리 경고 표시
    if (current_voltage <= (WARNING_BATTERY_VOLTAGE + 0.4f))
    {
        // 네모 배터리 그리기
        uint16_t battery_width = 7;  // 배터리 본체 너비
        uint16_t battery_height = 9; // 배터리 본체 높이
        uint16_t battery_x = 68;     // 배터리 X 시작점
        uint16_t battery_y = 4;      // 배터리 Y 시작점

        // 배터리 양극 단자 크기
        uint16_t terminal_width = 3;
        uint16_t terminal_height = 2;
        uint16_t terminal_x = (battery_x + battery_width / 2) - 1;
        uint16_t terminal_y = battery_y - terminal_height;

        // 배터리 본체 테두리 (단일 테두리로 단순화)
        Paint_DrawRectangle(battery_x, battery_y,
                            battery_x + battery_width, battery_y + battery_height,
                            COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

        // 배터리 양극 단자 그리기
        Paint_DrawRectangle(terminal_x, terminal_y,
                            terminal_x + terminal_width, terminal_y + terminal_height,
                            COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);

        if (current_voltage >= WARNING_BATTERY_VOLTAGE)
        {
            // 배터리 잔량 표기
            Paint_DrawRectangle(battery_x + 2, battery_y + battery_height - 3,
                                battery_x + battery_width - 2, battery_y + battery_height - 1, COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
        }
    }
}

/**
 * @brief 배터리 전압 표시 (항상 전압만 표시)
 * @param voltage: 배터리 전압 (V)
 */
void UI_DrawBatteryVoltage(float voltage)
{
    uint16_t base_x = BATTERY_PERCENT_X - 20; // 중앙 정렬 조정
    uint16_t base_y = BATTERY_PERCENT_Y - 12; // 중앙 정렬 조정

    // 전압 표시 (XX.X V 형식)
    uint16_t voltage_int = (uint16_t)voltage;
    uint16_t voltage_frac = (uint16_t)((voltage - voltage_int) * 10);

    // 전압 표시 영역 클리어 (XX.X 형식에 맞게)
    uint16_t clear_x = base_x + 2;
    Paint_DrawRectangle(clear_x + 2, base_y - 2, clear_x + 35, base_y + 16, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // 전압 값 표시 (XX.X 형식)
    if (voltage_int >= 10)
    {
        // 2자리 정수 + 소수점 1자리
        UI_DrawDigitLarge(clear_x + 2, base_y, voltage_int / 10, COLOR_WHITE, 1.5);
        UI_DrawDigitLarge(clear_x + 12, base_y, voltage_int % 10, COLOR_WHITE, 1.5);
        // 소수점 그리기
        Paint_SetPixel(clear_x + 23, base_y + 10, COLOR_WHITE);
        Paint_SetPixel(clear_x + 24, base_y + 10, COLOR_WHITE);
        Paint_SetPixel(clear_x + 23, base_y + 11, COLOR_WHITE);
        Paint_SetPixel(clear_x + 24, base_y + 11, COLOR_WHITE);
        UI_DrawDigitLarge(clear_x + 26, base_y, voltage_frac, COLOR_WHITE, 1.5);
    }
    else
    {
        // 1자리 정수 + 소수점 1자리 (9.X V 등)
        UI_DrawDigitLarge(clear_x + 7, base_y, voltage_int, COLOR_WHITE, 1.5);
        // 소수점 그리기
        Paint_SetPixel(clear_x + 17, base_y + 10, COLOR_WHITE);
        Paint_SetPixel(clear_x + 18, base_y + 10, COLOR_WHITE);
        Paint_SetPixel(clear_x + 17, base_y + 11, COLOR_WHITE);
        Paint_SetPixel(clear_x + 18, base_y + 11, COLOR_WHITE);
        UI_DrawDigitLarge(clear_x + 21, base_y, voltage_frac, COLOR_WHITE, 1.5);
    }

    // 전압 표시 아이콘 (V) 그리기
    UI_DrawIcon12x16(base_x + 13, base_y + 16, voltage_v_12x16, COLOR_WHITE);
}

/**
 * @brief 우측 정보 영역 그리기 (32x64, 4등분)
 * @param status: UI 상태 구조체
 */
void UI_DrawInfoArea(UI_Status_t *status)
{
    // 1구역: 타이머 시간 표시 (분:초)
    UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                     (status->timer_status == TIMER_STATUS_SETTING), status->blink_counter);

    // 2-3구역: 타이머 상태 아이콘 표시 (19x19 큰 아이콘, 중앙 정렬)
    UI_DrawTimerStatus(status->timer_status);

    // 4구역: LED 연결 상태 표시 (원형)
    UI_DrawLEDStatus(status->timer_status, status->l1_connected, status->l2_connected);
}

/**
 * @brief 타이머 시간 표시 (1구역 - 분:초, 항상 2자리)
 * @param minutes: 분
 * @param seconds: 초
 * @param should_blink: 깜빡임 여부
 * @param blink_counter: 깜빡임 카운터 (사용하지 않음, 호환성 유지)
 */
void UI_DrawTimerTime(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter)
{
    UNUSED(blink_counter); // 더 이상 사용하지 않음

    uint16_t x_pos = INFO_TIMER_X;
    uint16_t y_pos = INFO_TIMER_Y;

    // 깜빡임 효과: 시스템 틱 기반 1초 주기 (정확한 시간 기반)
    uint8_t show_text = 1;
    if (should_blink)
    {
        uint32_t current_tick = xTaskGetTickCount();
        uint32_t one_second_ticks = 500 / portTICK_PERIOD_MS; // 1초를 틱으로 변환
        show_text = (current_tick / one_second_ticks) % 3;    // 1초마다 토글
    }

    if (show_text)
    {
        char time_str[8]; // "00:00" + null terminator
        sprintf(time_str, "%02d:%02d", minutes, seconds);
        Paint_DrawString_EN(x_pos, y_pos, time_str, &Font12, COLOR_WHITE, COLOR_BLACK);
    }
    else
    {
        // 깜빡임을 위해 해당 영역 클리어
        Paint_DrawRectangle(x_pos, y_pos, x_pos + 35, y_pos + 12, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    }
}

/**
 * @brief 타이머 상태 아이콘 표시 (2-3구역 - 토글 스위치 또는 아이콘)
 * @param status: 타이머 상태
 */
void UI_DrawTimerStatus(Timer_Status_t status)
{
    // 현재 시간 가져오기
    uint32_t current_time = HAL_GetTick();

    // 전역 current_status의 토글 스위치 사용
    UI_DrawTimerToggleStatus(status, &current_status.timer_toggle_switch, current_time);
}

/**
 * @brief LED 연결 상태 표시 (4구역 - 원형)
 * @param l1_status: L1 연결 상태
 * @param l2_status: L2 연결 상태
 */
void UI_DrawLEDStatus(Timer_Status_t status, LED_Connection_t l1_status, LED_Connection_t l2_status)
{
    Paint_DrawRectangle(INFO_L1_X - INFO_L1_RADIUS, INFO_L1_Y - INFO_L1_RADIUS, INFO_L2_X + INFO_L2_RADIUS, INFO_L2_Y + INFO_L2_RADIUS, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // L1 상태 표시 (원형)
    if (l1_status == LED_CONNECTED_2 || l1_status == LED_CONNECTED_4)
    {
        // 연결됨: 채워진 원형
        UI_DrawCircle(INFO_L1_X, INFO_L1_Y, INFO_L1_RADIUS, COLOR_WHITE, 1);

        if (status == TIMER_STATUS_RUNNING)
        {
            if (l1_status == LED_CONNECTED_2)
            {
                Paint_DrawLine(INFO_L1_X - 2, INFO_L1_Y, INFO_L1_X - 2, INFO_L1_Y, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L1_X + 2, INFO_L1_Y, INFO_L1_X + 2, INFO_L1_Y, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
            }
            else
            {
                Paint_DrawLine(INFO_L1_X - 2, INFO_L1_Y - 2, INFO_L1_X - 2, INFO_L1_Y - 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L1_X + 2, INFO_L1_Y - 2, INFO_L1_X + 2, INFO_L1_Y - 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L1_X - 2, INFO_L1_Y + 2, INFO_L1_X - 2, INFO_L1_Y + 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L1_X + 2, INFO_L1_Y + 2, INFO_L1_X + 2, INFO_L1_Y + 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
            }
        }
    }
    else
    {
        // 연결 안됨: 빈 원형
        UI_DrawCircle(INFO_L1_X, INFO_L1_Y, INFO_L1_RADIUS, COLOR_WHITE, 0);
    }

    // L2 상태 표시 (원형)
    if (l2_status == LED_CONNECTED_2 || l2_status == LED_CONNECTED_4)
    {
        // 연결됨: 채워진 원형
        UI_DrawCircle(INFO_L2_X, INFO_L2_Y, INFO_L2_RADIUS, COLOR_WHITE, 1);

        if (status == TIMER_STATUS_RUNNING)
        {
            // Dubug 용 인식을 점으로 표시
            if (l2_status == LED_CONNECTED_2)
            {
                Paint_DrawLine(INFO_L2_X - 2, INFO_L2_Y, INFO_L2_X - 2, INFO_L2_Y, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L2_X + 2, INFO_L2_Y, INFO_L2_X + 2, INFO_L2_Y, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
            }
            else
            {
                Paint_DrawLine(INFO_L2_X - 2, INFO_L2_Y - 2, INFO_L2_X - 2, INFO_L2_Y - 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L2_X + 2, INFO_L2_Y - 2, INFO_L2_X + 2, INFO_L2_Y - 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L2_X - 2, INFO_L2_Y + 2, INFO_L2_X - 2, INFO_L2_Y + 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
                Paint_DrawLine(INFO_L2_X + 2, INFO_L2_Y + 2, INFO_L2_X + 2, INFO_L2_Y + 2, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
            }
        }
    }
    else
    {
        // 연결 안됨: 빈 원형
        UI_DrawCircle(INFO_L2_X, INFO_L2_Y, INFO_L2_RADIUS, COLOR_WHITE, 0);
    }
}

/**
 * @brief 초기 애니메이션 업데이트 (0V에서 현재 전압까지 단계적으로 채움)
 * @param status: UI 상태 구조체
 * @return 애니메이션 완료 여부 (1: 완료, 0: 진행 중)
 */
uint8_t UI_UpdateInitAnimation(UI_Status_t *status)
{
    // 애니메이션이 비활성이면 바로 완료 반환
    if (!status->init_animation_active)
    {
        return 1;
    }

    // 애니메이션 속도 제어 (10프레임마다 업데이트 = 500ms마다)
    if (status->animation_counter % 1 != 0)
    {
        status->animation_counter++;
        return 0; // 아직 진행 중
    }

    float dif_voltage = status->battery_voltage - status->animation_voltage;
    // 현재 목표 전압까지 0.2V씩 증가

    const float ANIMATION_STEP = dif_voltage > 2 ? dif_voltage > 4 ? 0.3f : 0.2f : 0.1f;

    status->animation_voltage += ANIMATION_STEP;

    // 목표 전압에 도달했거나 초과했으면 애니메이션 완료
    if (status->animation_voltage >= status->battery_voltage)
    {
        status->animation_voltage = status->battery_voltage;
        status->init_animation_active = 0; // 애니메이션 비활성화
        status->animation_counter++;
        return 1; // 완료
    }

    status->animation_counter++;
    return 0; // 진행 중
}

/**
 * @brief 초기 애니메이션 시작
 * @param status: UI 상태 구조체
 * @param target_voltage: 목표 전압
 */
void UI_StartInitAnimation(UI_Status_t *status, float target_voltage)
{
    status->init_animation_active = 1;
    status->animation_voltage = 18.6f; // 최소 전압부터 시작
    status->animation_counter = 0;
    status->battery_voltage = target_voltage; // 목표 전압 설정
}

/**
 * @brief 전체 화면 그리기
 * @param status: UI 상태 구조체
 */
void UI_DrawFullScreen(UI_Status_t *status)
{
    // 화면 클리어
    UI_Clear();

    // 타이머 실행 표시기 (좌측 상단)
    UI_DrawTimerIndicator(status->timer_indicator_blink);

    // 좌측 영역: 배터리 전압 (96x64)
    UI_DrawBatteryArea(status->battery_voltage, status);

    // 우측 영역: 정보 (32x64)
    UI_DrawInfoArea(status);

    // 화면 테두리(삭제 금지)
    Paint_DrawRectangle(81, 1, 128, 64, WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

    // 화면 업데이트
    OLED_1in3_C_Display(BlackImage);
}

/**
 * @brief 최적화된 전체 화면 그리기
 * @param status: UI 상태 구조체
 */
void UI_DrawFullScreenOptimized(UI_Status_t *status)
{
    static float prev_battery_voltage = 0.0f; // 이전 배터리 전압값
    static Timer_Status_t prev_timer_status = TIMER_STATUS_STANDBY;
    static bool is_changed_timer_status = false;
    static uint8_t prev_timer_minutes = 255;
    static uint8_t prev_timer_seconds = 255;
    static LED_Connection_t prev_l1_connected = LED_DISCONNECTED;
    static LED_Connection_t prev_l2_connected = LED_DISCONNECTED;
    static uint8_t prev_low_bat_state = 0; // 이전 LOW BAT 상태 추적

    // 현재 LOW BAT 상태 확인
    uint8_t current_low_bat_state = (status->battery_voltage <= CRITICAL_BATTERY_VOLTAGE) ? 1 : 0;

    // 초기 애니메이션 업데이트
    uint8_t animation_completed = UI_UpdateInitAnimation(status);

    // LOW BAT 상태 변화 감지 시 전체 업데이트 강제
    if (prev_low_bat_state != current_low_bat_state)
    {
        status->force_full_update = 1;
        prev_low_bat_state = current_low_bat_state;
    }

    // 전체 업데이트가 필요한 경우 또는 애니메이션 진행 중
    if (status->force_full_update || status->init_animation_active)
    {
        UI_DrawFullScreen(status);
        status->force_full_update = 0;

        // 애니메이션 완료 시에만 이전 값들 업데이트
        if (animation_completed)
        {
            status->init_animation_active = false;
            prev_battery_voltage = status->battery_voltage;
            prev_timer_status = status->timer_status;
            prev_timer_minutes = status->timer_minutes;
            prev_timer_seconds = status->timer_seconds;
            prev_l1_connected = status->l1_connected;
            prev_l2_connected = status->l2_connected;
        }
        return; // 전체 업데이트 후 종료
    }

    if (status->timer_status == TIMER_STATUS_RUNNING)
    {
        UI_DrawTimerIndicator(is_half_second_tick);
    }
    else if (status->warning_status == 0)
    {
        UI_DrawTimerIndicator(0);
    }

    // 타이머 시간 업데이트 (값이 변경되거나 깜빡임이 필요한 경우)
    if (prev_timer_minutes != status->timer_minutes ||
        prev_timer_seconds != status->timer_seconds ||
        status->timer_status == TIMER_STATUS_SETTING)
    {
        UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                         (status->timer_status == TIMER_STATUS_SETTING), status->blink_counter);

        // 설정 모드가 아닌 경우에만 이전 값 업데이트 (깜빡임을 위해)
        if (status->timer_status != TIMER_STATUS_SETTING)
        {
            prev_timer_minutes = status->timer_minutes;
            prev_timer_seconds = status->timer_seconds;
        }
    }

    // 상태 아이콘 업데이트
    if (prev_timer_status != status->timer_status || status->is_timer_toggle_animation_running)
    {
        is_changed_timer_status = true;
        UI_DrawTimerStatus(status->timer_status);

        // 설정 모드에서 다른 상태로 변경될 때 타이머 값 강제 업데이트
        if (prev_timer_status == TIMER_STATUS_SETTING)
        {
            UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                             (status->timer_status == TIMER_STATUS_SETTING), status->blink_counter);
            prev_timer_minutes = status->timer_minutes;
            prev_timer_seconds = status->timer_seconds;
        }

        prev_timer_status = status->timer_status;
    }

    // LED 상태 업데이트 (변경된 경우만)
    if (prev_l1_connected != status->l1_connected || prev_l2_connected != status->l2_connected || is_changed_timer_status)
    {
        is_changed_timer_status = false;
        UI_DrawLEDStatus(status->timer_status, status->l1_connected, status->l2_connected);
        prev_l1_connected = status->l1_connected;
        prev_l2_connected = status->l2_connected;
    }

    // 배터리 전압 업데이트 (값이 변경된 경우이고 LOW BAT 상태가 아닐 때)
    if (prev_battery_voltage != status->battery_voltage)
    {
        UI_DrawBatteryArea(status->battery_voltage, status);
        prev_battery_voltage = status->battery_voltage;
    }

    // 화면 업데이트
    OLED_1in3_C_Display(BlackImage);
}

/**
 * @brief 토글 스위치 초기화
 * @param toggle: 토글 스위치 구조체 포인터
 * @param x: X 위치
 * @param y: Y 위치
 */
void UI_InitToggleSwitch(Toggle_Switch_t *toggle, uint16_t x, uint16_t y)
{
    toggle->x = x;
    toggle->y = y;
    toggle->state = TOGGLE_STATE_OFF;
    toggle->target_state = TOGGLE_STATE_OFF;
    toggle->animation_step = 0;
    toggle->last_update_time = 0;
    toggle->is_animating = 0;
}

/**
 * @brief 토글 스위치 애니메이션 시작
 * @param toggle: 토글 스위치 구조체 포인터
 * @param target_state: 목표 상태
 */
void UI_StartToggleAnimation(Toggle_Switch_t *toggle, Toggle_State_t target_state)
{
    // 목표 상태가 현재 상태와 다를 때만 애니메이션 시작
    if (toggle->target_state != target_state)
    {
        toggle->target_state = target_state;
        toggle->is_animating = 1;
        toggle->animation_step = 0;
        toggle->last_update_time = HAL_GetTick();
    }
}

/**
 * @brief 토글 스위치 애니메이션 업데이트
 * @param toggle: 토글 스위치 구조체 포인터
 * @param current_time: 현재 시간 (ms)
 * @return 애니메이션 완료 여부 (1: 완료, 0: 진행중)
 */
uint8_t UI_UpdateToggleAnimation(Toggle_Switch_t *toggle, uint32_t current_time)
{
    if (!toggle->is_animating)
        return 1;

    // 애니메이션 지연 시간 확인 (더 정확한 타이밍)
    if (current_time - toggle->last_update_time >= TOGGLE_ANIMATION_DELAY)
    {
        if (8 > toggle->animation_step)
        {
            toggle->animation_step += 2;
        }
        else
        {
            toggle->animation_step++;
        }
        toggle->last_update_time = current_time;

        // 애니메이션 완료 확인
        if (toggle->animation_step >= TOGGLE_ANIMATION_STEPS)
        {
            toggle->state = toggle->target_state;
            toggle->is_animating = 0;
            toggle->animation_step = 0;
            current_status.is_timer_toggle_animation_running = 0;

            return 1; // 애니메이션 완료
        }
    }

    return 0; // 애니메이션 진행중
}

/**
 * @brief 토글 스위치 그리기
 * @param toggle: 토글 스위치 구조체 포인터
 */
void UI_DrawToggleSwitch(Toggle_Switch_t *toggle)
{
    uint16_t base_x = toggle->x;
    uint16_t base_y = toggle->y;

    // 배경 영역 클리어 (텍스트 포함하여 더 넓게)
    Paint_DrawRectangle(base_x, base_y - 6,
                        126, base_y + TOGGLE_SWITCH_HEIGHT + 4,
                        COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // 현재 상태에 따른 배경색 결정
    uint16_t bg_color;
    uint8_t current_is_on = 0;

    if (toggle->is_animating)
    {
        // 애니메이션 중에는 목표 상태를 기준으로 색상 결정
        current_is_on = (toggle->target_state == TOGGLE_STATE_ON) ? 1 : 0;
    }
    else
    {
        // 정적 상태에서는 현재 상태를 기준으로 색상 결정
        current_is_on = (toggle->state == TOGGLE_STATE_ON) ? 1 : 0;
    }

    if (current_is_on)
    {
        // ON 상태: 배경 흰색
        bg_color = COLOR_BLACK;
    }
    else
    {
        // OFF 상태: 배경 검정
        bg_color = COLOR_BLACK;
    }

    // 스위치 배경 그리기
    Paint_DrawRectangle(base_x + 1, base_y,
                        base_x + TOGGLE_SWITCH_WIDTH + 2, base_y + TOGGLE_SWITCH_HEIGHT,
                        bg_color, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    Paint_DrawCircle(base_x + 8, base_y + TOGGLE_SWITCH_HEIGHT / 2, TOGGLE_SWITCH_RADIUS + 2, COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    Paint_DrawCircle(base_x + TOGGLE_SWITCH_WIDTH - 6, base_y + TOGGLE_SWITCH_HEIGHT / 2, TOGGLE_SWITCH_RADIUS + 2, COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

    // 스위치 테두리 (항상 흰색)
    Paint_DrawRectangle(base_x + 8, base_y,
                        base_x + TOGGLE_SWITCH_WIDTH - 5, base_y + TOGGLE_SWITCH_HEIGHT,
                        COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    // 스위치 배경 그리기
    Paint_DrawRectangle(base_x + 8, base_y + 1,
                        base_x + TOGGLE_SWITCH_WIDTH - 5, base_y + TOGGLE_SWITCH_HEIGHT,
                        bg_color, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // 핸들 위치 계산
    uint16_t handle_x_off = base_x + TOGGLE_SWITCH_RADIUS + 2;                  // OFF 위치 (좌측)
    uint16_t handle_x_on = base_x + TOGGLE_SWITCH_WIDTH - TOGGLE_SWITCH_RADIUS; // ON 위치 (우측)
    uint16_t handle_y = base_y + TOGGLE_SWITCH_HEIGHT / 2;
    uint16_t handle_x;

    if (toggle->is_animating)
    {
        // 애니메이션 중일 때 정확한 선형 보간
        float progress = (float)toggle->animation_step / (float)TOGGLE_ANIMATION_STEPS;

        // 진행도 제한 (0.0 ~ 1.0)
        if (progress > 1.0f)
            progress = 1.0f;
        if (progress < 0.0f)
            progress = 0.0f;

        if (toggle->target_state == TOGGLE_STATE_ON)
        {
            // OFF -> ON 애니메이션: 왼쪽에서 오른쪽으로
            float distance = (float)(handle_x_on - handle_x_off);
            handle_x = handle_x_off + (uint16_t)(distance * progress);
        }
        else
        {
            // ON -> OFF 애니메이션: 오른쪽에서 왼쪽으로
            float distance = (float)(handle_x_on - handle_x_off);
            handle_x = handle_x_on - (uint16_t)(distance * progress);
        }
    }
    else
    {
        // 정적 상태
        if (toggle->state == TOGGLE_STATE_ON)
        {
            handle_x = handle_x_on;
        }
        else
        {
            handle_x = handle_x_off;
        }
    }

    // 핸들 그리기 (항상 흰색 원형)
    Paint_DrawCircle(handle_x, handle_y, TOGGLE_SWITCH_RADIUS - 1, COLOR_WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // 애니메이션 중이 아닐 때만 텍스트 표시
    if (!toggle->is_animating)
    {
        if (toggle->state == TOGGLE_STATE_OFF)
        {
            // OFF 상태: 핸들이 왼쪽에 있으므로 오른쪽에 "OFF" 표시
            Paint_DrawString_EN(base_x + 14, base_y + 2, "OFF", &Font12, COLOR_WHITE, bg_color);
        }
        else
        {
            // ON 상태: 핸들이 오른쪽에 있으므로 왼쪽에 "ON" 표시
            Paint_DrawString_EN(base_x + 5, base_y + 2, "ON", &Font12, COLOR_WHITE, bg_color);
        }
    }
}

/**
 * @brief 타이머 상태에 따른 토글 스위치 표시 및 애니메이션 처리
 * @param status: 타이머 상태
 * @param toggle: 토글 스위치 구조체 포인터
 * @param current_time: 현재 시간 (ms)
 */
void UI_DrawTimerToggleStatus(Timer_Status_t status, Toggle_Switch_t *toggle, uint32_t current_time)
{
    // STANDBY와 RUNNING 상태에서만 토글 스위치 표시
    if (status == TIMER_STATUS_STANDBY || status == TIMER_STATUS_RUNNING)
    {
        // 목표 상태 결정
        Toggle_State_t target_state = (status == TIMER_STATUS_RUNNING) ? TOGGLE_STATE_ON : TOGGLE_STATE_OFF;

        // 상태 변화 확인 및 애니메이션 시작
        if (toggle->target_state != target_state)
        {
            current_status.is_timer_toggle_animation_running = 1;
            UI_StartToggleAnimation(toggle, target_state);
        }

        // 애니메이션 업데이트
        UI_UpdateToggleAnimation(toggle, current_time);

        // 토글 스위치 그리기
        UI_DrawToggleSwitch(toggle);
    }
    else 
    {
        // 다른 상태에서는 기존 아이콘 표시
        uint16_t icon_x = (INFO_AREA_X + (INFO_AREA_WIDTH / 2) - (19 / 2)) - 1;
        uint16_t icon_y = INFO_STATUS_Y;

        uint16_t base_x = toggle->x;
        uint16_t base_y = toggle->y;

        // 배경 영역 클리어 (텍스트 포함하여 더 넓게)
        Paint_DrawRectangle(base_x - 1, base_y - 1,
                            base_x + TOGGLE_SWITCH_WIDTH + 2, base_y + TOGGLE_SWITCH_HEIGHT + 1,
                            COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
        // 상태 아이콘 영역 클리어 (텍스트 영역까지 포함)
        Paint_DrawRectangle(icon_x - 20, icon_y - 3,
                            icon_x + 42, icon_y + 22,
                            COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

        switch (status)
        {
        case TIMER_STATUS_SETTING:
            UI_DrawIcon19x19(icon_x, icon_y, setting_icon_19x19, COLOR_WHITE);
            break;
        case TIMER_STATUS_COOLING:
            UI_DrawIcon19x19(icon_x, icon_y, cooling_icon_19x19, COLOR_WHITE);
            break;
        case TIMER_STATUS_LOCKING:
            UI_DrawIcon19x19(icon_x, icon_y, lock_icon_19x19, COLOR_WHITE);
            break;
        case TIMER_STATUS_WARNING:
            UI_DrawIcon19x19(icon_x, icon_y, warning_icon_19x19, COLOR_WHITE);
            break;
        default:
            break;
        }
    }
}