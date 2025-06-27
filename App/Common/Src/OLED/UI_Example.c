/*****************************************************************************
 * | File      	:   UI_Example.c
 * | Author      :   OnBoard LED Light Timer
 * | Function    :   UI usage example and test functions
 * | Info        :   Example implementation for LED timer UI
 *----------------
 * |	This version:   V1.0
 * | Date        :   2024-01-01
 * | Info        :   Example and test code
 ******************************************************************************/

#include "../../Inc/OLED/UI_Layout.h"
#include "../../Inc/OLED/DEV_Config.h"
#include "cmsis_os.h"

// 전역 UI 상태 변수
static UI_Status_t g_ui_status = {
    .battery_percent = 85, // 초기 배터리 85%
    .timer_hours = 2,      // 초기 타이머 2시간
    .timer_minutes = 30,   // 초기 타이머 30분
    .is_timer_running = 0, // 초기 타이머 정지 상태
    .is_connected = 1      // 연결 상태
};

/**
 * @brief UI 시스템 초기화 및 첫 화면 표시
 */
void UI_SystemInit(void)
{
    // UI 초기화
    UI_Init();

    // 초기 화면 표시
    UI_DrawFullScreen(&g_ui_status);

    osDelay(2000); // 2초간 표시
}

/**
 * @brief 배터리 레벨 업데이트
 * @param percent: 새로운 배터리 퍼센티지 (0-100)
 */
void UI_UpdateBattery(uint8_t percent)
{
    if (percent > 100)
        percent = 100;

    g_ui_status.battery_percent = percent;
    UI_DrawFullScreen(&g_ui_status);
}

/**
 * @brief 타이머 설정값 업데이트
 * @param hours: 시간 (0-23)
 * @param minutes: 분 (0-59)
 */
void UI_UpdateTimerSetting(uint8_t hours, uint8_t minutes)
{
    if (hours > 23)
        hours = 23;
    if (minutes > 59)
        minutes = 59;

    g_ui_status.timer_hours = hours;
    g_ui_status.timer_minutes = minutes;
    UI_DrawFullScreen(&g_ui_status);
}

/**
 * @brief 타이머 실행 상태 토글
 */
void UI_ToggleTimerStatus(void)
{
    g_ui_status.is_timer_running = !g_ui_status.is_timer_running;
    UI_DrawFullScreen(&g_ui_status);
}

/**
 * @brief 현재 UI 상태 반환
 * @return UI_Status_t*: 현재 UI 상태 구조체 포인터
 */
UI_Status_t *UI_GetCurrentStatus(void)
{
    return &g_ui_status;
}

/**
 * @brief UI 데모 테스트 함수
 */
void UI_DemoTest(void)
{
    // 시스템 초기화

    // 배터리 레벨 변화 테스트
    for (int i = 100; i >= 0; i -= 10)
    {
        UI_UpdateBattery(i);
        osDelay(500);
    }

    // 배터리 레벨 복구
    UI_UpdateBattery(75);
    osDelay(1000);

    // 타이머 상태 토글 테스트
    for (int i = 0; i < 5; i++)
    {
        UI_ToggleTimerStatus();
        osDelay(800);
    }

    // 타이머 설정값 변경 테스트
    uint8_t timer_settings[][2] = {
        {1, 15}, // 1시간 15분
        {0, 30}, // 30분
        {3, 45}, // 3시간 45분
        {2, 0},  // 2시간
        {0, 5}   // 5분
    };

    for (int i = 0; i < 5; i++)
    {
        UI_UpdateTimerSetting(timer_settings[i][0], timer_settings[i][1]);
        osDelay(1500);
    }

    // 최종 상태로 복원
    UI_UpdateTimerSetting(2, 30);
    UI_UpdateBattery(85);
}

/**
 * @brief 배터리 부족 경고 표시
 */
void UI_ShowLowBatteryWarning(void)
{
    // 배터리 부족 시 깜빡임 효과
    for (int i = 0; i < 6; i++)
    {
        if (i % 2 == 0)
        {
            UI_Clear();
            OLED_1in3_C_Display(BlackImage);
        }
        else
        {
            UI_DrawFullScreen(&g_ui_status);
        }
        osDelay(300);
    }
}

/**
 * @brief 타이머 완료 알림 표시
 */
void UI_ShowTimerComplete(void)
{
    // 타이머 완료 시 전체 화면 깜빡임
    for (int i = 0; i < 10; i++)
    {
        if (i % 2 == 0)
        {
            // 전체 화면을 흰색으로
            Paint_Clear(WHITE);
            OLED_1in3_C_Display(BlackImage);
        }
        else
        {
            // 원래 화면으로
            UI_DrawFullScreen(&g_ui_status);
        }
        osDelay(200);
    }

    // 타이머 상태를 정지로 변경
    g_ui_status.is_timer_running = 0;
    UI_DrawFullScreen(&g_ui_status);
}

/**
 * @brief 절전 모드 진입 전 화면 페이드아웃
 */
void UI_FadeOut(void)
{
    // 화면을 점진적으로 어둡게 만드는 효과
    for (int i = 0; i < 5; i++)
    {
        UI_DrawFullScreen(&g_ui_status);
        osDelay(100);
        UI_Clear();
        osDelay(100 + i * 50);
    }

    // 최종적으로 화면 끄기
    UI_Clear();
    OLED_1in3_C_Display(BlackImage);
}

/**
 * @brief 메인 UI 업데이트 루프 (타이머 및 시스템에서 호출)
 */
void UI_UpdateLoop(void)
{
    // 배터리 레벨 체크
    if (g_ui_status.battery_percent <= 10)
    {
        UI_ShowLowBatteryWarning();
    }

    // 일반적인 화면 업데이트
    UI_DrawFullScreen(&g_ui_status);
}