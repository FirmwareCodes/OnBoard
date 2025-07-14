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

extern const unsigned char standby_icon_19x19[];
extern const unsigned char running_icon_19x19[];
extern const unsigned char setting_icon_19x19[];
extern const unsigned char cooling_icon_19x19[];
extern const unsigned char warning_icon_19x19[];

extern const unsigned char percent_12x12[];
extern const unsigned char exclamation_12x12[];

extern const unsigned char digit_5x7[10][7];
extern const unsigned char colon_3x7[7];

// 최적화를 위한 전역 변수 (삼각함수 룩업 테이블)
static float sin_table[720] = {0}; // 0.5도 간격으로 360도 * 2
static float cos_table[720] = {0};
static uint8_t lookup_table_initialized = 0;

/**
 * @brief 삼각함수 룩업 테이블 초기화 (최초 1회만 실행)
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
 * @brief 큰 숫자 2자리 그리기 (이전 방식으로 되돌림)
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
 * @brief 부드러운 원형 그리기 (브레젠햄 알고리즘 기반)
 */
static void draw_smooth_circle_outline(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int x = radius;
    int y = 0;
    int decision = 1 - radius;

    while (x >= y)
    {
        // 8방향 대칭으로 픽셀 그리기
        Paint_SetPixel(center_x + x, center_y + y, color);
        Paint_SetPixel(center_x - x, center_y + y, color);
        Paint_SetPixel(center_x + x, center_y - y, color);
        Paint_SetPixel(center_x - x, center_y - y, color);
        Paint_SetPixel(center_x + y, center_y + x, color);
        Paint_SetPixel(center_x - y, center_y + x, color);
        Paint_SetPixel(center_x + y, center_y - x, color);
        Paint_SetPixel(center_x - y, center_y - x, color);

        y++;
        if (decision <= 0)
        {
            decision += 2 * y + 1;
        }
        else
        {
            x--;
            decision += 2 * (y - x) + 1;
        }
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
                    // 간단한 중점 보간 (브레젠햄보다 빠름)
                    int mid_x = prev_x + dx / 2;
                    int mid_y = prev_y + dy / 2;
                    Paint_SetPixel(mid_x, mid_y, color);

                    // 필요시 추가 중점
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
 * @brief 원형 프로그래스바 그리기 (최적화된 버전 - 부드러운 원형)
 * @param center_x: 중심 X 좌표
 * @param center_y: 중심 Y 좌표
 * @param radius: 반지름
 * @param progress: 진행률 (0-100)
 * @param color: 색상
 * @param should_update: 업데이트 여부 (성능 최적화)
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

    // 미리 계산된 값들
    const int outer_radius = radius - 1;
    const int inner_radius = radius - 8;
    const int progress_start_radius = radius - 1;
    // const int progress_end_radius = radius - 4;

    // 브레젠햄 알고리즘으로 완벽한 원형 테두리 그리기
    draw_smooth_circle_outline(center_x, center_y, outer_radius, color);
    draw_smooth_circle_outline(center_x, center_y, inner_radius, color);

    draw_smooth_circle_outline(center_x, center_y, outer_radius + 1, COLOR_BLACK);

    // 진행률이 0이면 테두리만 그리고 종료
    if (progress == 0)
        return;

    // 진행률에 따른 각도 계산 (0도부터 시계방향)
    float progress_angle = (progress * 360.0f) / 100.0f;

    // 최적화된 프로그래스바 그리기 - 단일 함수로 통합
    int progress_thickness = progress_start_radius - inner_radius; // 실제 두께 계산
    if (progress_thickness > 7)
        progress_thickness = 7; // 최대 두께 제한

    draw_optimized_arc(center_x, center_y, progress_start_radius, 0, progress_angle, color, progress_thickness);

    // 시작점과 끝점에 둥근 캡 추가 (간소화된 버전)
    if (progress > 3) // 최소 진행률이 있을 때만
    {
        // 시작점 캡 (12시 방향) - 3x3에서 2x2로 축소
        int start_x = center_x;
        int start_y = center_y - (radius - 4);

        Paint_SetPixel(start_x, start_y, color);
        Paint_SetPixel(start_x + 1, start_y, color);
        Paint_SetPixel(start_x, start_y + 1, color);
        Paint_SetPixel(start_x + 1, start_y + 1, color);

        // 끝점 캡 (진행률이 충분할 때만) - 3x3에서 2x2로 축소
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
    // 영역 경계선 그리기 (선택사항)
    Paint_DrawLine(LEFT_AREA_WIDTH, 0, LEFT_AREA_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);

    // 전압 기반 프로그래스바 그리기 (애니메이션 지원)
    UI_DrawVoltageProgress(voltage, status);

    // 배터리 전압 그리기 (애니메이션 중에는 애니메이션 전압 표시)
    float display_voltage = status->init_animation_active ? status->animation_voltage : voltage;
    UI_DrawBatteryVoltage(display_voltage);
}

/**
 * @brief 전압 기반 원형 프로그래스바 그리기
 * @param voltage: 배터리 전압 (19.0V ~ 24.7V)
 * @param status: UI 상태 구조체 (애니메이션 처리용)
 */
void UI_DrawVoltageProgress(float voltage, UI_Status_t *status)
{
    // 전압을 퍼센트로 변환 (19.0V = 0%, 24.7V = 100%)
    const float WARNING_VOLTAGE = 20.0f; // 경고 전압 임계값

    // 애니메이션 중이면 애니메이션 전압 사용, 아니면 실제 전압 사용
    float current_voltage = status->init_animation_active ? status->animation_voltage : voltage;

    float voltage_percent = status->battery_percentage;

    // 범위 제한
    if (voltage_percent < 0.0f)
        voltage_percent = 0.0f;
    if (voltage_percent > 100.0f)
        voltage_percent = 100.0f;

    uint8_t progress = (uint8_t)voltage_percent;

    // 20V 이하일 때 빨간색 경고, 그 외에는 흰색
    uint16_t progress_color = (current_voltage < WARNING_VOLTAGE) ? COLOR_WHITE : COLOR_WHITE;

    // 원형 프로그래스바 그리기
    UI_DrawCircularProgressOptimized(BATTERY_CENTER_X, BATTERY_CENTER_Y, BATTERY_OUTER_RADIUS, progress, progress_color, 1);
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
    UI_DrawLEDStatus(status->l1_connected, status->l2_connected);
}

/**
 * @brief 타이머 시간 표시 (1구역 - 분:초, 항상 2자리)
 * @param minutes: 분
 * @param seconds: 초
 * @param should_blink: 깜빡임 여부
 * @param blink_counter: 깜빡임 카운터
 */
void UI_DrawTimerTime(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter)
{
    uint16_t x_pos = INFO_TIMER_X;
    uint16_t y_pos = INFO_TIMER_Y;

    // 깜빡임 효과: 20프레임마다 토글 (50ms * 20 = 1초 주기)
    uint8_t show_text = 1;
    if (should_blink && ((blink_counter / 20) % 2 == 0))
    {
        show_text = 0; // 숨김
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
 * @brief 타이머 상태 아이콘 표시 (2-3구역 - 19x19 큰 아이콘, 겹침 방지)
 * @param status: 타이머 상태
 */
void UI_DrawTimerStatus(Timer_Status_t status)
{
    // 19x19 아이콘을 우측 영역에 중앙 정렬
    uint16_t icon_x = (INFO_AREA_X + (INFO_AREA_WIDTH / 2) - (19 / 2)) - 1; // 우측 영역 중앙
    uint16_t icon_y = INFO_STATUS_Y;

    // 상태 아이콘 영역을 더 넓게 클리어 (겹침 완전 방지)
    Paint_DrawRectangle(icon_x - 3, icon_y - 3,
                        icon_x + 22, icon_y + 22,
                        COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    switch (status)
    {
    case TIMER_STATUS_STANDBY:
        UI_DrawIcon19x19(icon_x, icon_y, standby_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_RUNNING:
        UI_DrawIcon19x19(icon_x - 3, icon_y, running_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_SETTING:
        UI_DrawIcon19x19(icon_x, icon_y, setting_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_COOLING:
        UI_DrawIcon19x19(icon_x, icon_y, cooling_icon_19x19, COLOR_WHITE);
        break;
    case TIMER_STATUS_WARNING:
        UI_DrawIcon19x19(icon_x, icon_y, warning_icon_19x19, COLOR_WHITE);
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
    Paint_DrawRectangle(INFO_L1_X - INFO_L1_RADIUS, INFO_L1_Y - INFO_L1_RADIUS, INFO_L2_X + INFO_L2_RADIUS, INFO_L2_Y + INFO_L2_RADIUS, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    // L1 상태 표시 (원형)
    if (l1_status == LED_CONNECTED_2 || l1_status == LED_CONNECTED_4)
    {
        // 연결됨: 채워진 원형
        UI_DrawCircle(INFO_L1_X, INFO_L1_Y, INFO_L1_RADIUS, COLOR_WHITE, 1);

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

        // Paint_DrawLine(INFO_L2_X, INFO_L2_Y - 10, INFO_L2_X, INFO_L2_Y - 7, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
        // Paint_DrawLine(INFO_L2_X - 7, INFO_L2_Y - 8, INFO_L2_X - 6, INFO_L2_Y - 5, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
        // Paint_DrawLine(INFO_L2_X + 7, INFO_L2_Y - 8, INFO_L2_X + 6, INFO_L2_Y - 5, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    }
    else
    {
        // 연결 안됨: 빈 원형
        UI_DrawCircle(INFO_L2_X, INFO_L2_Y, INFO_L2_RADIUS, COLOR_WHITE, 0);

        // Paint_DrawLine(INFO_L2_X, INFO_L2_Y - 10, INFO_L2_X, INFO_L2_Y - 7, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
        // Paint_DrawLine(INFO_L2_X - 7, INFO_L2_Y - 8, INFO_L2_X - 6, INFO_L2_Y - 5, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
        // Paint_DrawLine(INFO_L2_X + 7, INFO_L2_Y - 8, INFO_L2_X + 6, INFO_L2_Y - 5, COLOR_BLACK, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
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

    // 현재 목표 전압까지 0.2V씩 증가
    const float ANIMATION_STEP = 0.1f;

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
 * @brief 전체 화면 그리기 (새로운 레이아웃)
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
 * @brief 최적화된 전체 화면 그리기 (성능 향상)
 * @param status: UI 상태 구조체
 */
void UI_DrawFullScreenOptimized(UI_Status_t *status)
{
    static float prev_battery_voltage = 0.0f; // 이전 배터리 전압값
    static Timer_Status_t prev_timer_status = TIMER_STATUS_STANDBY;
    static uint8_t prev_timer_minutes = 255;
    static uint8_t prev_timer_seconds = 255;
    static LED_Connection_t prev_l1_connected = LED_DISCONNECTED;
    static LED_Connection_t prev_l2_connected = LED_DISCONNECTED;
    static uint8_t prev_timer_indicator = 255; // 이전 타이머 표시기 상태

    // 초기 애니메이션 업데이트
    uint8_t animation_completed = UI_UpdateInitAnimation(status);

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
            prev_timer_indicator = status->timer_indicator_blink;
        }
    }

    // 타이머 실행 표시기 업데이트 (상태가 변경된 경우)
    if (prev_timer_indicator != status->timer_indicator_blink)
    {
        UI_DrawTimerIndicator(status->timer_indicator_blink);
        prev_timer_indicator = status->timer_indicator_blink;
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

    // 상태 아이콘 업데이트 (상태가 변경된 경우, 겹침 방지를 위해 항상 클리어 후 재그리기)
    if (prev_timer_status != status->timer_status)
    {
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
    if (prev_l1_connected != status->l1_connected || prev_l2_connected != status->l2_connected)
    {
        UI_DrawLEDStatus(status->l1_connected, status->l2_connected);
        prev_l1_connected = status->l1_connected;
        prev_l2_connected = status->l2_connected;
    }

    // 배터리 부족 경고 아이콘 위치
    uint16_t base_x = 62; // 중앙 정렬 조정
    uint16_t base_y = 2;  // 중앙 정렬 조정

    // 배터리 부족 경고
    if (status->battery_voltage < WARNING_BATTERY_VOLTAGE)
    {
        uint8_t interval = abs((int)status->battery_voltage - 16) + (status->battery_voltage < 16.0f ? 1 : 0);
        uint16_t update_interval = (status->progress_update_counter % (PROGRESS_UPDATE_INTERVAL_MS * interval / UI_UPDATE_INTERVAL_MS));

        // 느낌표 아이콘 그리기
        if (update_interval == 0 || update_interval == 1)
        {
            UI_DrawIcon12x16(base_x, base_y, electric_12x16, COLOR_BLACK);
        }
        else
        {
            UI_DrawIcon12x16(base_x, base_y, electric_12x16, COLOR_WHITE);
        }
    }
    else
    {
        UI_DrawIcon12x16(base_x, base_y, electric_12x16, COLOR_BLACK);
    }

    // 배터리 전압 업데이트 (값이 변경된 경우)
    if (prev_battery_voltage != status->battery_voltage)
    {
        UI_DrawBatteryArea(status->battery_voltage, status);
        prev_battery_voltage = status->battery_voltage;
    }

    // 화면 업데이트
    OLED_1in3_C_Display(BlackImage);
}