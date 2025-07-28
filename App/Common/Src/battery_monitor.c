/**
 ******************************************************************************
 * @file    battery_monitor.c
 * @brief   배터리 모니터링 및 잔량 계산 기능 구현
 ******************************************************************************
 * @attention
 *
 * 이 파일은 24V 배터리의 잔량을 정확하게 측정하고 관리하는 기능을 제공합니다.
 * 부하 상태에 따른 전압 보정 및 필터링 기능을 포함합니다.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "flash_storage.h"
#include "battery_monitor.h"
#include <math.h>
#include <string.h>

/* Private defines -----------------------------------------------------------*/
#define BATTERY_PERCENTAGE_SAVE_THRESHOLD 2   // 5% 이상 변화 시 저장
#define BATTERY_FLASH_SAVE_INTERVAL_MS 300000 // 5분마다 자동 저장
#define TEN_SECOND_SAMPLE_PERIOD_MS 100       // 100ms 간격으로 샘플링 
#define VOLTAGE_CHANGE_THRESHOLD_ADC 24 // 0.2V 변화 임계값 (ADC)

/* Private variables ---------------------------------------------------------*/
static const uint16_t battery_lookup_table[][2] = {
    // {ADC값, 배터리퍼센트} - 19.0V=0%, 24.0V=100% 선형 분배
    // ADC 2802 (19.0V) = 0%, ADC 3542 (24.0V) = 100%
    // 5V 범위를 20단계로 분할 (0.25V당 5%)
    {2802, 0},   // 19.0V = 0%
    {2839, 5},   // 19.25V = 5%
    {2876, 10},  // 19.5V = 10%
    {2913, 15},  // 19.75V = 15%
    {2950, 20},  // 20.0V = 20%
    {2987, 25},  // 20.25V = 25%
    {3024, 30},  // 20.5V = 30%
    {3061, 35},  // 20.75V = 35%
    {3098, 40},  // 21.0V = 40%
    {3135, 45},  // 21.25V = 45%
    {3172, 50},  // 21.5V = 50%
    {3209, 55},  // 21.75V = 55%
    {3246, 60},  // 22.0V = 60%
    {3283, 65},  // 22.25V = 65%
    {3320, 70},  // 22.5V = 70%
    {3357, 75},  // 22.75V = 75%
    {3394, 80},  // 23.0V = 80%
    {3431, 85},  // 23.25V = 85%
    {3468, 90},  // 23.5V = 90%
    {3505, 95},  // 23.75V = 95%
    {3542, 100}, // 24.0V = 100%
    {3580, 100}, // 24.2V = 100%
    {3620, 100}, // 24.5V = 100%
    {3660, 100}, // 24.8V = 100%
    {3700, 100}, // 25.1V = 100%
    {3720, 100}  // 25.2V = 100%
};

#define BATTERY_LOOKUP_TABLE_SIZE (sizeof(battery_lookup_table) / sizeof(battery_lookup_table[0]))

/* Private function prototypes -----------------------------------------------*/
static uint16_t Battery_Filter_ADC_Samples(Battery_Monitor_t *monitor);

/**
 * @brief  배터리 퍼센트 정수 값 반환 (LCD 표시용)
 * @param  monitor: 배터리 모니터 구조체 포인터
 * @retval 배터리 퍼센트 정수 값 (0-100)
 */
uint8_t Battery_Get_Percentage_Integer(Battery_Monitor_t *monitor)
{
    return (uint8_t)roundf(monitor->battery_percentage);
}

/**
 * @brief  배터리 퍼센트 소수점 값 반환 (UART 전송용)
 * @param  monitor: 배터리 모니터 구조체 포인터
 * @retval 배터리 퍼센트 소수점 값 (0.00-100.00)
 */
float Battery_Get_Percentage_Float(Battery_Monitor_t *monitor)
{
    return monitor->battery_percentage;
}

/**
 * @brief  ADC 값을 전압으로 변환
 * @param  adc_value: ADC 값 (0-4095)
 * @retval 전압 값 (V)
 * @note   실제 측정값 기준: ADC 3720 = 25.2V, ADC 2740 = 18.6V
 *         선형 보간을 사용하여 전압 계산
 */
float Battery_ADC_To_Voltage(uint16_t adc_value)
{
    // 실제 측정값 기준 선형 변환
    const float ADC_MAX = 3720.0f; // 25.2V에 해당하는 ADC 값
    // const float ADC_MIN = 2740.0f;    // 18.6V에 해당하는 ADC 값
    const float ADC_MIN = 2498.0f; // 17.0V에 해당하는 ADC 값

    const float VOLTAGE_MAX = 25.2f; // 최대 전압 (V)
    // const float VOLTAGE_MIN = 18.6f;  // 최소 전압 (V)
    const float VOLTAGE_MIN = 17.0f; // 최소 전압 (V)

    // 선형 보간을 사용한 전압 계산
    // Voltage = VOLTAGE_MIN + (adc_value - ADC_MIN) * (VOLTAGE_MAX - VOLTAGE_MIN) / (ADC_MAX - ADC_MIN)
    float voltage = VOLTAGE_MIN + ((float)(adc_value - ADC_MIN) * (VOLTAGE_MAX - VOLTAGE_MIN)) / (ADC_MAX - ADC_MIN);

    // 전압 보정
    voltage -= 0.04f;

    return voltage;
}

/**
 * @brief  현재 배터리 전압 반환 (실측값만 사용)
 * @param  monitor: 배터리 모니터 구조체 포인터
 * @retval 배터리 전압 (V)
 */
float Battery_Get_Voltage(Battery_Monitor_t *monitor)
{
    // 전압 표시에는 실측값만 사용 (보정 완전 제거)
    return Battery_ADC_To_Voltage(monitor->filtered_voltage);
}

/* Function implementations --------------------------------------------------*/

/**
 * @brief  배터리 모니터 초기화
 * @param  monitor: 배터리 모니터 구조체 포인터
 * @retval None
 */
void Battery_Monitor_Init(Battery_Monitor_t *monitor)
{
    // 모든 값 초기화
    memset(monitor, 0, sizeof(Battery_Monitor_t));

    // 초기값 설정
    monitor->battery_percentage = 50.0f; // 기본값 50.0%
    monitor->status = BATTERY_STATUS_NORMAL;
    monitor->last_saved_percentage = 50.0f;
    monitor->is_power_on_sequence = false;

    // 현재 시간 설정
    uint32_t current_time = HAL_GetTick();
    monitor->last_update_time = current_time;
    monitor->last_flash_save_time = current_time;
    monitor->power_on_time = current_time;

    // 플래시에서 배터리 데이터 로드
    // Battery_Load_From_Flash(monitor);

}

/**
 * @brief  배터리 모니터 업데이트 
 * @param  monitor: 배터리 모니터 구조체 포인터
 * @param  raw_adc_value: 원시 ADC 값
 * @param  is_load_active: 부하 활성 상태 (사용 안함)
 * @retval None
 */
void Battery_Monitor_Update(Battery_Monitor_t *monitor, uint16_t raw_adc_value, bool is_load_active)
{
    UNUSED(is_load_active);
    uint32_t current_time = HAL_GetTick();

    // ADC 샘플 버퍼에 추가
    monitor->raw_adc_samples[monitor->sample_index] = raw_adc_value;
    monitor->sample_index = (monitor->sample_index + 1) % BATTERY_SAMPLE_BUFFER_SIZE;

    if (!monitor->sample_buffer_full && monitor->sample_index == 0)
    {
        monitor->sample_buffer_full = true;
    }

    // 필터링된 전압 계산 (실측값만 사용)
    monitor->filtered_voltage = Battery_Filter_ADC_Samples(monitor);

    // 표시용 전압도 동일한 실측값 사용
    monitor->display_voltage = monitor->filtered_voltage;
    monitor->compensated_voltage = monitor->filtered_voltage;

    // 배터리 퍼센트 계산 (실측값 기준)
    monitor->battery_percentage = Battery_Calculate_Percentage(monitor->filtered_voltage);

    // 범위 제한
    if (monitor->battery_percentage > 100.0f)
        monitor->battery_percentage = 100.0f;
    if (monitor->battery_percentage < 0.0f)
        monitor->battery_percentage = 0.0f;

    // 배터리 상태 업데이트
    if (monitor->battery_percentage <= 18.0f)
    {
        monitor->status = BATTERY_STATUS_CRITICAL;
    }
    else if (monitor->battery_percentage <= 20.0f)
    {
        monitor->status = BATTERY_STATUS_LOW;
    }
    else
    {
        monitor->status = BATTERY_STATUS_NORMAL;
    }

    monitor->last_update_time = current_time;
}

/**
 * @brief  ADC 값으로부터 배터리 퍼센트 계산
 * @param  adc_value: ADC 값
 * @retval 배터리 퍼센트 (0.00-100.00, 소수점 2자리)
 */
/** __attribute__((optimize("O0"))) */
float Battery_Calculate_Percentage(uint16_t adc_value)
{
    // 범위 체크
    if (adc_value >= battery_lookup_table[BATTERY_LOOKUP_TABLE_SIZE - 1][0])
    {
        return 100.0f;
    }

    if (adc_value <= battery_lookup_table[0][0])
    {
        return 0.0f;
    }

    // 룩업 테이블에서 선형 보간
    for (uint8_t i = 1; i < BATTERY_LOOKUP_TABLE_SIZE; i++)
    {
        if (adc_value <= battery_lookup_table[i][0])
        {
            uint16_t adc_low = battery_lookup_table[i - 1][0];
            uint16_t adc_high = battery_lookup_table[i][0];
            float percent_low = (float)battery_lookup_table[i - 1][1];
            float percent_high = (float)battery_lookup_table[i][1];

            // 선형 보간 계산 (소수점 2자리 정밀도)
            float ratio = (float)(adc_value - adc_low) / (float)(adc_high - adc_low);
            float interpolated = percent_low + (ratio * (percent_high - percent_low));

            // 소수점 2자리로 반올림
            return roundf(interpolated * 100.0f) / 100.0f;
        }
    }

    return 0.0f;
}

/* Private function implementations ------------------------------------------*/

/**
 * @brief  ADC 샘플들의 이동평균 필터 계산
 * @param  monitor: 배터리 모니터 구조체 포인터
 * @retval 필터링된 ADC 값
 */
static uint16_t Battery_Filter_ADC_Samples(Battery_Monitor_t *monitor)
{
    uint32_t sum = 0;
    uint8_t count = monitor->sample_buffer_full ? BATTERY_SAMPLE_BUFFER_SIZE : monitor->sample_index;

    if (count == 0)
        return 0;

    for (uint8_t i = 0; i < count; i++)
    {
        sum += monitor->raw_adc_samples[i];
    }

    return (uint16_t)(sum / count);
}
