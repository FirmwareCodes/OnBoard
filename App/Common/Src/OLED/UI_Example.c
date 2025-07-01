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
    .battery_percent = 85,              // 초기 배터리 85%
    .timer_minutes = 2,                 // 초기 타이머 2분
    .timer_seconds = 30,                // 초기 타이머 30초
    .timer_status = TIMER_STATUS_STANDBY, // 초기 대기 상태
    .l1_connected = LED_DISCONNECTED,      // L1 연결됨
    .l2_connected = LED_DISCONNECTED,      // L2 연결됨
    .cooling_seconds = 0                // 쿨링 시간 없음
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
 * @param minutes: 분 (0-59)
 * @param seconds: 초 (0-59)
 */
void UI_UpdateTimerSetting(uint8_t minutes, uint8_t seconds)
{
    if (minutes > 59) minutes = 59;
    if (seconds > 59) seconds = 59;

    g_ui_status.timer_minutes = minutes;
    g_ui_status.timer_seconds = seconds;
    UI_DrawFullScreen(&g_ui_status);
}

/**
 * @brief 타이머 실행 상태 토글
 */
void UI_ToggleTimerStatus(void)
{
    switch(g_ui_status.timer_status) {
        case TIMER_STATUS_STANDBY:
            g_ui_status.timer_status = TIMER_STATUS_RUNNING;
            break;
        case TIMER_STATUS_RUNNING:
            g_ui_status.timer_status = TIMER_STATUS_STANDBY;
            break;
        case TIMER_STATUS_SETTING:
            g_ui_status.timer_status = TIMER_STATUS_STANDBY;
            break;
        case TIMER_STATUS_COOLING:
            g_ui_status.timer_status = TIMER_STATUS_STANDBY;
            break;
    }
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
    }

    // 타이머 상태를 정지로 변경
    g_ui_status.timer_status = TIMER_STATUS_STANDBY;
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