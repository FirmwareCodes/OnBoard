#ifndef __BATTERY_MONITOR_H
#define __BATTERY_MONITOR_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Function prototypes -------------------------------------------------------*/
void Battery_Monitor_Init(Battery_Monitor_t *monitor);
void Battery_Monitor_Update(Battery_Monitor_t *monitor, uint16_t raw_adc_value, bool is_load_active);
void Battery_Monitor_Update_With_PWM(Battery_Monitor_t *monitor, uint16_t raw_adc_value, bool is_load_active, uint16_t pwm_duty);
float Battery_Calculate_Percentage(uint16_t adc_value);
uint8_t Battery_Get_Percentage_Integer(Battery_Monitor_t *monitor);
float Battery_Get_Percentage_Float(Battery_Monitor_t *monitor);
float Battery_ADC_To_Voltage(uint16_t adc_value);
float Battery_Get_Voltage(Battery_Monitor_t *monitor);
void Battery_Save_To_Flash(Battery_Monitor_t *monitor);
void Battery_Load_From_Flash(Battery_Monitor_t *monitor);

#ifdef __cplusplus
}
#endif

#endif /* __BATTERY_MONITOR_H */ 