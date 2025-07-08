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

extern const unsigned char percent_12x12[];
extern const unsigned char exclamation_12x12[];

extern const unsigned char digit_5x7[10][7];
extern const unsigned char colon_3x7[7];

static float sin_table[720] = {0};
static float cos_table[720] = {0};
static uint8_t lookup_table_initialized = 0;

static void init_trig_lookup_table(void)
{
    if (lookup_table_initialized)
        return;

    for (int i = 0; i < 720; i++)
    {
        float angle = (i * 0.5f - 90.0f) * M_PI / 180.0f;
        sin_table[i] = sin(angle);
        cos_table[i] = cos(angle);
    }
    lookup_table_initialized = 1;
}

void UI_Init(void)
{
    Paint_Clear(BLACK);
    OLED_1in3_C_Display(BlackImage);
}

void UI_Clear(void)
{
    Paint_Clear(BLACK);
}

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
                Paint_SetPixel(x + col * font_scale, y + row * font_scale, color);
                Paint_SetPixel(x + col * font_scale + 1, y + row * font_scale, color);
                Paint_SetPixel(x + col * font_scale, y + row * font_scale + 1, color);
                Paint_SetPixel(x + col * font_scale + 1, y + row * font_scale + 1, color);
            }
        }
    }
}

void UI_DrawTwoDigitsLarge(uint16_t x, uint16_t y, uint8_t value)
{
    uint8_t tens = value / 10;
    uint8_t ones = value % 10;

    UI_DrawDigitLarge(x, y, tens, COLOR_WHITE, 2);
    UI_DrawDigitLarge(x + 12, y, ones, COLOR_WHITE, 2);
}

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
            offset_x += 6;
        }
    }
}

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

void UI_DrawIcon19x19(uint16_t x, uint16_t y, const unsigned char *icon_data, uint16_t color)
{
    for (int row = 0; row < 19; row++)
    {
        uint32_t data = (icon_data[row * 3] << 16) | (icon_data[row * 3 + 1] << 8) | icon_data[row * 3 + 2];

        for (int col = 0; col < 19; col++)
        {
            if (data & (0x800000 >> col))
            {
                Paint_SetPixel(x + col, y + row, color);
            }
        }
    }
}

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

void UI_DrawCircle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color, uint8_t filled)
{
    if (filled)
    {
        Paint_DrawCircle(x, y, radius, color, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    }
    else
    {
        Paint_DrawCircle(x, y, radius, color, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    }
}

static void draw_smooth_circle_outline(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int x = radius;
    int y = 0;
    int decision = 1 - radius;

    while (x >= y)
    {
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

static void draw_optimized_arc(uint16_t center_x, uint16_t center_y, uint16_t radius,
                               float start_angle, float end_angle, uint16_t color, int thickness)
{
    int start_index = (int)(start_angle * 2.0f);
    int end_index = (int)(end_angle * 2.0f);
    if (end_index > 720)
        end_index = 720;

    for (int t = 0; t < thickness; t++)
    {
        int current_radius = radius - t;
        if (current_radius < 5)
            continue;

        int prev_x = -999, prev_y = -999;

        for (int i = start_index; i < end_index; i += 1)
        {
            int x = center_x + (int)(current_radius * cos_table[i]);
            int y = center_y + (int)(current_radius * sin_table[i]);

            Paint_SetPixel(x, y, color);

            if (prev_x != -999 && prev_y != -999)
            {
                int dx = x - prev_x;
                int dy = y - prev_y;

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

void UI_DrawCircularProgressOptimized(uint16_t center_x, uint16_t center_y, uint16_t radius, uint8_t progress, uint16_t color, uint8_t should_update)
{
    if (!should_update)
    {
        return;
    }

    init_trig_lookup_table();

    Paint_DrawCircle(center_x, center_y, radius, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    const int outer_radius = radius - 1;
    const int inner_radius = radius - 8;
    const int progress_start_radius = radius - 1;

    draw_smooth_circle_outline(center_x, center_y, outer_radius, color);
    draw_smooth_circle_outline(center_x, center_y, inner_radius, color);
    draw_smooth_circle_outline(center_x, center_y, outer_radius + 1, COLOR_BLACK);

    if (progress == 0)
        return;

    float progress_angle = (progress * 360.0f) / 100.0f;

    int progress_thickness = progress_start_radius - inner_radius;
    if (progress_thickness > 7)
        progress_thickness = 7;

    draw_optimized_arc(center_x, center_y, progress_start_radius, 0, progress_angle, color, progress_thickness);

    if (progress > 3)
    {
        int start_x = center_x;
        int start_y = center_y - (radius - 4);

        Paint_SetPixel(start_x, start_y, color);
        Paint_SetPixel(start_x + 1, start_y, color);
        Paint_SetPixel(start_x, start_y + 1, color);
        Paint_SetPixel(start_x + 1, start_y + 1, color);

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

void UI_DrawTimerIndicator(uint8_t show)
{
    Paint_DrawRectangle(TIMER_INDICATOR_X - TIMER_INDICATOR_RADIUS - 1,
                        TIMER_INDICATOR_Y - TIMER_INDICATOR_RADIUS - 1,
                        TIMER_INDICATOR_X + TIMER_INDICATOR_RADIUS + 1,
                        TIMER_INDICATOR_Y + TIMER_INDICATOR_RADIUS + 1,
                        COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    if (show)
    {
        UI_DrawCircle(TIMER_INDICATOR_X, TIMER_INDICATOR_Y, TIMER_INDICATOR_RADIUS, COLOR_WHITE, 1);
    }
}

void UI_DrawBatteryArea(uint8_t percent, float voltage, bool show_voltage)
{
    Paint_DrawLine(LEFT_AREA_WIDTH, 0, LEFT_AREA_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
    UI_DrawBatteryProgress(percent);
    UI_DrawBatteryPercentage(percent, voltage, show_voltage);
}

void UI_DrawBatteryProgress(uint8_t percent)
{
    UI_DrawCircularProgressOptimized(BATTERY_CENTER_X, BATTERY_CENTER_Y, BATTERY_OUTER_RADIUS, percent, COLOR_WHITE, 1);
}

void UI_DrawBatteryPercentage(uint8_t percent, float voltage, bool show_voltage)
{
    uint16_t base_x = BATTERY_PERCENT_X - 20;
    uint16_t base_y = BATTERY_PERCENT_Y - 12;

    if (show_voltage)
    {
        uint16_t voltage_int = (uint16_t)voltage;
        uint16_t voltage_frac = (uint16_t)((voltage - voltage_int) * 10);
        
        uint16_t clear_x = base_x + 2;
        Paint_DrawRectangle(clear_x - 2, base_y - 2, clear_x + 38, base_y + 16, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
        
        if (voltage_int >= 10)
        {
            UI_DrawDigitLarge(clear_x, base_y, voltage_int / 10, COLOR_WHITE, 1.5);
            UI_DrawDigitLarge(clear_x + 11, base_y, voltage_int % 10, COLOR_WHITE, 1.5);
            Paint_SetPixel(clear_x + 22, base_y + 12, COLOR_WHITE);
            Paint_SetPixel(clear_x + 23, base_y + 12, COLOR_WHITE);
            Paint_SetPixel(clear_x + 22, base_y + 13, COLOR_WHITE);
            Paint_SetPixel(clear_x + 23, base_y + 13, COLOR_WHITE);
            UI_DrawDigitLarge(clear_x + 26, base_y, voltage_frac, COLOR_WHITE, 1.5);
        }
        else
        {
            UI_DrawDigitLarge(clear_x + 5, base_y, voltage_int, COLOR_WHITE, 1.5);
            Paint_SetPixel(clear_x + 16, base_y + 12, COLOR_WHITE);
            Paint_SetPixel(clear_x + 17, base_y + 12, COLOR_WHITE);
            Paint_SetPixel(clear_x + 16, base_y + 13, COLOR_WHITE);
            Paint_SetPixel(clear_x + 17, base_y + 13, COLOR_WHITE);
            UI_DrawDigitLarge(clear_x + 20, base_y, voltage_frac, COLOR_WHITE, 1.5);
        }
        
        UI_DrawIcon12x16(base_x + 11, base_y + 17, electric_12x16, COLOR_WHITE);
    }
    else
    {
        if (percent >= 100)
        {
            uint16_t safe_x = base_x + 4;
            Paint_DrawRectangle(safe_x - 2, base_y - 2, safe_x + 34, base_y + 16, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

            UI_DrawDigitLarge(safe_x, base_y, 1, COLOR_WHITE, 1.5);
            UI_DrawDigitLarge(safe_x + 11, base_y, 0, COLOR_WHITE, 1.5);
            UI_DrawDigitLarge(safe_x + 22, base_y, 0, COLOR_WHITE, 1.5);
        }
        else if (percent >= 10)
        {
            uint16_t clear_x = base_x + 6;
            Paint_DrawRectangle(clear_x - 2, base_y - 2, clear_x + 26, base_y + 16, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

            UI_DrawDigitLarge(base_x + 7, base_y, percent / 10, COLOR_WHITE, 2);
            UI_DrawDigitLarge(base_x + 21, base_y, percent % 10, COLOR_WHITE, 2);
        }
        else
        {
            uint16_t clear_x = base_x + 12;
            Paint_DrawRectangle(clear_x - 2, base_y - 2, clear_x + 14, base_y + 16, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
            UI_DrawDigitLarge(base_x + 14, base_y, percent, COLOR_WHITE, 2);
        }

        UI_DrawIcon12x16(base_x + 11, base_y + 17, percent_12x16, COLOR_WHITE);
    }
}

void UI_DrawInfoArea(UI_Status_t *status)
{
    UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                     (status->timer_status == TIMER_STATUS_SETTING), status->blink_counter);
    UI_DrawTimerStatus(status->timer_status);
    UI_DrawLEDStatus(status->l1_connected, status->l2_connected);
}

void UI_DrawTimerTime(uint8_t minutes, uint8_t seconds, uint8_t should_blink, uint32_t blink_counter)
{
    uint16_t x_pos = INFO_TIMER_X;
    uint16_t y_pos = INFO_TIMER_Y;

    uint8_t show_text = 1;
    if (should_blink && ((blink_counter / 20) % 2 == 0))
    {
        show_text = 0;
    }

    if (show_text)
    {
        char time_str[8];
        sprintf(time_str, "%02d:%02d", minutes, seconds);
        Paint_DrawString_EN(x_pos, y_pos, time_str, &Font12, COLOR_WHITE, COLOR_BLACK);
    }
    else
    {
        Paint_DrawRectangle(x_pos, y_pos, x_pos + 35, y_pos + 12, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    }
}

void UI_DrawTimerStatus(Timer_Status_t status)
{
    uint16_t icon_x = (INFO_AREA_X + (INFO_AREA_WIDTH / 2) - (19 / 2)) - 1;
    uint16_t icon_y = INFO_STATUS_Y;

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
    }
}

void UI_DrawLEDStatus(LED_Connection_t l1_status, LED_Connection_t l2_status)
{
    Paint_DrawRectangle(INFO_L1_X - INFO_L1_RADIUS, INFO_L1_Y - INFO_L1_RADIUS, INFO_L2_X + INFO_L2_RADIUS, INFO_L2_Y + INFO_L2_RADIUS, COLOR_BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    if (l1_status == LED_CONNECTED_2 || l1_status == LED_CONNECTED_4)
    {
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
        UI_DrawCircle(INFO_L1_X, INFO_L1_Y, INFO_L1_RADIUS, COLOR_WHITE, 0);
    }

    if (l2_status == LED_CONNECTED_2 || l2_status == LED_CONNECTED_4)
    {
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
    }
    else
    {
        UI_DrawCircle(INFO_L2_X, INFO_L2_Y, INFO_L2_RADIUS, COLOR_WHITE, 0);
    }
}

void UI_DrawCoolingTime(uint8_t seconds)
{
    UNUSED(seconds);
}

void UI_DrawFullScreen(UI_Status_t *status)
{
    UI_Clear();
    UI_DrawTimerIndicator(status->timer_indicator_blink);
    UI_DrawInfoArea(status);
    Paint_DrawRectangle(81, 1, 128, 64, WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    OLED_1in3_C_Display(BlackImage);
}

void UI_DrawFullScreenOptimized(UI_Status_t *status)
{
    static uint8_t prev_battery_percent = 255;
    static Timer_Status_t prev_timer_status = TIMER_STATUS_STANDBY;
    static uint8_t prev_timer_minutes = 255;
    static uint8_t prev_timer_seconds = 255;
    static LED_Connection_t prev_l1_connected = LED_DISCONNECTED;
    static LED_Connection_t prev_l2_connected = LED_DISCONNECTED;
    static uint8_t prev_timer_indicator = 255;

    if (status->force_full_update)
    {
        UI_DrawFullScreen(status);
        status->force_full_update = 0;
        prev_battery_percent = status->battery_percent;
        prev_timer_status = status->timer_status;
        prev_timer_minutes = status->timer_minutes;
        prev_timer_seconds = status->timer_seconds;
        prev_l1_connected = status->l1_connected;
        prev_l2_connected = status->l2_connected;
        prev_timer_indicator = status->timer_indicator_blink;
        return;
    }

    if (status->init_battery_percent <= 100 && status->init_bat_animation == false)
    {
        uint8_t real_bat = status->battery_percent;
        status->battery_percent = status->init_battery_percent;
        status->init_battery_percent += 2;
        if (status->init_battery_percent > real_bat || status->init_battery_percent >= 100)
        {
            status->init_bat_animation = true;
        }
    }

    uint16_t base_x = 62;
    uint16_t base_y = 2;

    if (status->battery_percent <= 20 && status->battery_percent > 0 && status->init_bat_animation == true)
    {
        uint8_t interval = (status->battery_percent / 5) + 1;
        uint16_t update_interval = (status->progress_update_counter % (PROGRESS_UPDATE_INTERVAL_MS * interval / UI_UPDATE_INTERVAL_MS));
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

    static bool prev_show_voltage = false;
    if (status->force_full_update || status->battery_percent != prev_battery_percent || status->show_voltage != prev_show_voltage)
    {
        UI_DrawBatteryProgress(status->battery_percent);
        UI_DrawBatteryPercentage(status->battery_percent, status->battery_voltage, status->show_voltage);
        prev_battery_percent = status->battery_percent;
        prev_show_voltage = status->show_voltage;
    }

    if (prev_timer_indicator != status->timer_indicator_blink)
    {
        UI_DrawTimerIndicator(status->timer_indicator_blink);
        prev_timer_indicator = status->timer_indicator_blink;
    }

    if (prev_timer_minutes != status->timer_minutes ||
        prev_timer_seconds != status->timer_seconds ||
        status->timer_status == TIMER_STATUS_SETTING)
    {
        UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                         (status->timer_status == TIMER_STATUS_SETTING), status->blink_counter);

        if (status->timer_status != TIMER_STATUS_SETTING)
        {
            prev_timer_minutes = status->timer_minutes;
            prev_timer_seconds = status->timer_seconds;
        }
    }

    if (prev_timer_status != status->timer_status)
    {
        UI_DrawTimerStatus(status->timer_status);

        if (prev_timer_status == TIMER_STATUS_SETTING)
        {
            UI_DrawTimerTime(status->timer_minutes, status->timer_seconds,
                             (status->timer_status == TIMER_STATUS_SETTING), status->blink_counter);
            prev_timer_minutes = status->timer_minutes;
            prev_timer_seconds = status->timer_seconds;
        }

        prev_timer_status = status->timer_status;
    }

    if (prev_l1_connected != status->l1_connected || prev_l2_connected != status->l2_connected)
    {
        UI_DrawLEDStatus(status->l1_connected, status->l2_connected);
        prev_l1_connected = status->l1_connected;
        prev_l2_connected = status->l2_connected;
    }

    OLED_1in3_C_Display(BlackImage);
}