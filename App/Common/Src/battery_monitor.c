/**
 * @file    battery_monitor.c
 * @brief   배터리 모니터링 및 잔량 계산 기능 구현
 */

#include "main.h"
#include "flash_storage.h"
#include "battery_monitor.h"
#include <math.h>
#include <string.h>

/* Private defines */
#define BATTERY_PERCENTAGE_SAVE_THRESHOLD 2
#define BATTERY_FLASH_SAVE_INTERVAL_MS 300000
#define TEN_SECOND_SAMPLE_PERIOD_MS 100
#define VOLTAGE_CHANGE_THRESHOLD_ADC 24

/* Private variables */
static const uint16_t battery_lookup_table[][2] = {
    {2741, 0}, {2750, 1}, {2780, 5}, {2820, 10}, {2860, 15},
    {2900, 20}, {2940, 25}, {2980, 30}, {3020, 35}, {3060, 40},
    {3100, 45}, {3140, 50}, {3180, 55}, {3220, 60}, {3260, 65},
    {3300, 70}, {3340, 75}, {3380, 80}, {3420, 85}, {3460, 90},
    {3500, 95}, {3540, 98}, {3580, 99}, {3640, 100}, {3730, 100}
};

#define BATTERY_LOOKUP_TABLE_SIZE (sizeof(battery_lookup_table) / sizeof(battery_lookup_table[0]))

/* Private function prototypes */
static uint16_t Battery_Filter_ADC_Samples(Battery_Monitor_t *monitor);
static void Battery_Update_Ten_Second_Average(Battery_Monitor_t *monitor, uint16_t voltage);
static uint16_t Battery_Get_Ten_Second_Average(Battery_Monitor_t *monitor);
static bool Battery_Should_Update_Percentage(Battery_Monitor_t *monitor, bool is_load_active);

uint8_t Battery_Get_Percentage_Integer(Battery_Monitor_t *monitor)
{
    return (uint8_t)roundf(monitor->battery_percentage);
}

float Battery_Get_Percentage_Float(Battery_Monitor_t *monitor)
{
    return monitor->battery_percentage;
}

float Battery_ADC_To_Voltage(uint16_t adc_value)
{
    const float VREF = 3.3f;
    const float ADC_RESOLUTION = 4095.0f;
    const float VOLTAGE_DIVIDER_RATIO = 25.4f / 3.3f;
    
    float adc_voltage = ((float)adc_value / ADC_RESOLUTION) * VREF;
    return adc_voltage * VOLTAGE_DIVIDER_RATIO;
}

float Battery_Get_Voltage(Battery_Monitor_t *monitor)
{
    return Battery_ADC_To_Voltage(monitor->compensated_voltage);
}

void Battery_Monitor_Init(Battery_Monitor_t *monitor)
{
    memset(monitor, 0, sizeof(Battery_Monitor_t));
    
    monitor->battery_percentage = 50.0f;
    monitor->status = BATTERY_STATUS_NORMAL;
    monitor->last_saved_percentage = 50.0f;
    monitor->is_power_on_sequence = false;
    
    uint32_t current_time = HAL_GetTick();
    monitor->last_update_time = current_time;
    monitor->last_flash_save_time = current_time;
    monitor->power_on_time = current_time;
    monitor->ten_second_start_time = current_time;
    
    Battery_Load_From_Flash(monitor);
}

void Battery_Monitor_Update(Battery_Monitor_t *monitor, uint16_t raw_adc_value, bool is_load_active)
{
    uint32_t current_time = HAL_GetTick();
    
    if (monitor->is_under_load != is_load_active)
    {
        monitor->is_under_load = is_load_active;
        monitor->last_load_state_change_time = current_time;
        monitor->ten_second_start_time = current_time;
        monitor->ten_second_index = 0;
        monitor->ten_second_buffer_full = false;
        
        if (!is_load_active)
        {
            monitor->voltage_recovery_in_progress = true;
        }
    }
    
    monitor->raw_adc_samples[monitor->sample_index] = raw_adc_value;
    monitor->sample_index = (monitor->sample_index + 1) % BATTERY_SAMPLE_BUFFER_SIZE;
    
    if (!monitor->sample_buffer_full && monitor->sample_index == 0)
    {
        monitor->sample_buffer_full = true;
    }
    
    monitor->filtered_voltage = Battery_Filter_ADC_Samples(monitor);
    
    uint32_t time_since_load_change = current_time - monitor->last_load_state_change_time;
    uint16_t voltage_for_calculation;
    
    if (is_load_active)
    {
        voltage_for_calculation = monitor->filtered_voltage;
    }
    else
    {
        voltage_for_calculation = Battery_Apply_Load_Compensation(
            monitor->filtered_voltage, false, time_since_load_change);
    }
    
    monitor->compensated_voltage = voltage_for_calculation;
    
    if ((current_time - monitor->last_update_time) >= TEN_SECOND_SAMPLE_PERIOD_MS)
    {
        Battery_Update_Ten_Second_Average(monitor, voltage_for_calculation);
        monitor->last_update_time = current_time;
    }
    
    if (Battery_Should_Update_Percentage(monitor, is_load_active))
    {
        uint16_t avg_voltage = Battery_Get_Ten_Second_Average(monitor);
        if (avg_voltage > 0)
        {
            float new_percentage = Battery_Calculate_Percentage(avg_voltage);
            float percentage_diff = new_percentage - monitor->battery_percentage;
            
            if (fabs(percentage_diff) <= 2.0f)
            {
                monitor->battery_percentage = new_percentage;
            }
            else if (percentage_diff > 2.0f)
            {
                monitor->battery_percentage += 2.0f;
            }
            else if (percentage_diff < -2.0f)
            {
                monitor->battery_percentage -= 2.0f;
            }
            
            if (monitor->battery_percentage > 100.0f) monitor->battery_percentage = 100.0f;
            if (monitor->battery_percentage > 150.0f && monitor->battery_percentage < 255.0f) monitor->battery_percentage = 0.0f;
        }
    }
    
    if (monitor->compensated_voltage >= BATTERY_FULL)
    {
        monitor->battery_percentage = 100.0f;
    }
    
    if (monitor->battery_percentage <= 10.0f)
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
    
    float percentage_diff = fabs(monitor->battery_percentage - monitor->last_saved_percentage);
    uint32_t time_since_save = current_time - monitor->last_flash_save_time;
    
    if ((percentage_diff >= (float)BATTERY_PERCENTAGE_SAVE_THRESHOLD) || 
        (time_since_save >= BATTERY_FLASH_SAVE_INTERVAL_MS))
    {
        Battery_Save_To_Flash(monitor);
    }
    
    if (monitor->voltage_recovery_in_progress && 
        time_since_load_change >= BATTERY_RECOVERY_TIME_MS)
    {
        monitor->voltage_recovery_in_progress = false;
    }
}

float Battery_Calculate_Percentage(uint16_t adc_value)
{
    if (adc_value >= battery_lookup_table[BATTERY_LOOKUP_TABLE_SIZE-1][0])
    {
        return 100.0f;
    }
    
    if (adc_value <= battery_lookup_table[0][0])
    {
        return 0.0f;
    }
    
    for (uint8_t i = 1; i < BATTERY_LOOKUP_TABLE_SIZE; i++)
    {
        if (adc_value <= battery_lookup_table[i][0])
        {
            uint16_t adc_low = battery_lookup_table[i-1][0];
            uint16_t adc_high = battery_lookup_table[i][0];
            float percent_low = (float)battery_lookup_table[i-1][1];
            float percent_high = (float)battery_lookup_table[i][1];
            
            float ratio = (float)(adc_value - adc_low) / (float)(adc_high - adc_low);
            float interpolated = percent_low + (ratio * (percent_high - percent_low));
            
            return roundf(interpolated * 100.0f) / 100.0f;
        }
    }
    
    return 0.0f;
}

uint16_t Battery_Apply_Load_Compensation(uint16_t raw_adc, bool is_under_load, uint32_t time_since_load_change)
{
    uint16_t compensated_adc = raw_adc;
    
    if (!is_under_load)
    {
        if (time_since_load_change < BATTERY_RECOVERY_TIME_MS)
        {
            float recovery_ratio = (float)time_since_load_change / (float)BATTERY_RECOVERY_TIME_MS;
            if (recovery_ratio > 1.0f) recovery_ratio = 1.0f;
            
            float recovery_factor = 1.0f - expf(-3.0f * recovery_ratio);
            uint16_t max_recovery = BATTERY_LOAD_VOLTAGE_DROP_ADC;
            
            compensated_adc -= (uint16_t)(max_recovery * recovery_factor);
        }
        else
        {
            compensated_adc -= BATTERY_LOAD_VOLTAGE_DROP_ADC;
        }
    }
    
    return compensated_adc;
}

void Battery_Save_To_Flash(Battery_Monitor_t *monitor)
{
    uint8_t percentage_int = (uint8_t)roundf(monitor->battery_percentage);
    
    HAL_StatusTypeDef status = Flash_WriteBatteryData(
        percentage_int,
        (uint8_t)monitor->status,
        monitor->compensated_voltage
    );
    
    if (status == HAL_OK)
    {
        monitor->last_saved_percentage = monitor->battery_percentage;
        monitor->last_flash_save_time = HAL_GetTick();
    }
}

void Battery_Load_From_Flash(Battery_Monitor_t *monitor)
{
    uint8_t percentage = 0;
    uint8_t status = 0;
    uint16_t adc_value = 0;
    
    HAL_StatusTypeDef result = Flash_ReadBatteryData(&percentage, &status, &adc_value);
    
    if (result == HAL_OK)
    {
        if (percentage <= 100 && status <= BATTERY_STATUS_CRITICAL && 
            adc_value >= BATTERY_MIN && adc_value <= BATTERY_MAX)
        {
            if (percentage >= 5 && percentage <= 95)
            {
                monitor->battery_percentage = (float)percentage;
                monitor->status = (Battery_Status_t)status;
                monitor->last_saved_percentage = (float)percentage;
                monitor->compensated_voltage = adc_value;
            }
            else
            {
                monitor->battery_percentage = 50.0f;
                monitor->last_saved_percentage = 50.0f;
                monitor->compensated_voltage = adc_value;
                monitor->status = BATTERY_STATUS_NORMAL;
            }
        }
        else
        {
            monitor->battery_percentage = 50.0f;
            monitor->last_saved_percentage = 50.0f;
            monitor->status = BATTERY_STATUS_NORMAL;
        }
    }
    else
    {
        monitor->battery_percentage = 50.0f;
        monitor->last_saved_percentage = 50.0f;
        monitor->status = BATTERY_STATUS_NORMAL;
    }
}

/* Private functions */
static uint16_t Battery_Filter_ADC_Samples(Battery_Monitor_t *monitor)
{
    uint32_t sum = 0;
    uint8_t count = monitor->sample_buffer_full ? BATTERY_SAMPLE_BUFFER_SIZE : monitor->sample_index;
    
    if (count == 0) return 0;
    
    for (uint8_t i = 0; i < count; i++)
    {
        sum += monitor->raw_adc_samples[i];
    }
    
    return (uint16_t)(sum / count);
}

static void Battery_Update_Ten_Second_Average(Battery_Monitor_t *monitor, uint16_t voltage)
{
    monitor->ten_second_samples[monitor->ten_second_index] = voltage;
    monitor->ten_second_index = (monitor->ten_second_index + 1) % 50;
    
    if (!monitor->ten_second_buffer_full && monitor->ten_second_index == 0)
    {
        monitor->ten_second_buffer_full = true;
    }
}

static uint16_t Battery_Get_Ten_Second_Average(Battery_Monitor_t *monitor)
{
    uint32_t sum = 0;
    uint8_t count = monitor->ten_second_buffer_full ? 50 : monitor->ten_second_index;
    
    if (count == 0) return 0;
    
    for (uint8_t i = 0; i < count; i++)
    {
        sum += monitor->ten_second_samples[i];
    }
    
    monitor->ten_second_average = (uint16_t)(sum / count);
    return monitor->ten_second_average;
}

static bool Battery_Should_Update_Percentage(Battery_Monitor_t *monitor, bool is_load_active)
{
    uint32_t current_time = HAL_GetTick();
    
    if ((current_time - monitor->ten_second_start_time) < 10000)
    {
        return false;
    }
    
    if (!monitor->ten_second_buffer_full)
    {
        return false;
    }
    
    if (is_load_active)
    {
        return true;
    }
    
    uint16_t avg_voltage = Battery_Get_Ten_Second_Average(monitor);
    if (avg_voltage > 0)
    {
        int voltage_diff = (int)avg_voltage - (int)monitor->filtered_voltage;
        if (abs(voltage_diff) >= VOLTAGE_CHANGE_THRESHOLD_ADC)
        {
            return true;
        }
    }
    
    if ((current_time - monitor->last_flash_save_time) >= BATTERY_FLASH_SAVE_INTERVAL_MS)
    {
        return true;
    }
    
    return false;
} 