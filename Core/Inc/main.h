/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.h
 * @brief          : Header for main.c file.
 *                   This file contains the common defines of the application.
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 STMicroelectronics.
 * All rights reserved.
 *
 * This software is licensed under terms that can be found in the LICENSE file
 * in the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C"
{
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32l4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "def.h"
#include "cmsis_os.h"
#include "flash_storage.h"

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */
#define VBAT_FILTER_SIZE 8 // VBat 이동평균 필터 크기

// 배터리 측정 버퍼 크기
#define BATTERY_SAMPLE_BUFFER_SIZE 8
#define BATTERY_MIN_VOLTAGE_BUFFER_SIZE 8

// 배터리 전압 보정값 (부하 시 전압 강하)
#define BATTERY_LOAD_VOLTAGE_DROP_ADC 90  // 약 0.8V 강하 (ADC 값)
#define BATTERY_RECOVERY_TIME_MS 5000    // 회복 시간

// 배터리 상태 열거형
typedef enum
{
  BATTERY_STATUS_NORMAL = 0,
  BATTERY_STATUS_LOW,
  BATTERY_STATUS_CRITICAL
} Battery_Status_t;

// 배터리 측정 및 보정 구조체
typedef struct
{
  uint16_t raw_adc_samples[BATTERY_SAMPLE_BUFFER_SIZE];     // 최근 8개 ADC 샘플
  uint16_t min_voltage_samples[BATTERY_MIN_VOLTAGE_BUFFER_SIZE]; // 최저 전압 8개 샘플
  uint8_t sample_index;                                     // 현재 샘플 인덱스
  uint8_t min_voltage_index;                               // 최저 전압 샘플 인덱스
  uint8_t sample_buffer_full;                              // 샘플 버퍼 가득참 여부
  uint8_t min_voltage_buffer_full;                         // 최저 전압 버퍼 가득함 여부
  
  // 10초 평균값 계산을 위한 필드들
  uint16_t ten_second_samples[50];                         // 10초간 샘플 (20ms * 50 = 1초, 실제로는 500개 정도 필요하지만 메모리 절약)
  uint8_t ten_second_index;                                // 10초 샘플 인덱스
  uint8_t ten_second_buffer_full;                          // 10초 버퍼 가득참 여부
  uint32_t ten_second_start_time;                          // 10초 측정 시작 시간
  
  uint16_t filtered_voltage;                               // 일정 횟수 측정값을 평균 필터링된 전압 (ADC)
  uint16_t compensated_voltage;                            // 부하 보정된 전압 (ADC)
  uint16_t display_voltage;                                // 표시용 실측 전압 (ADC, 보정 적용 안함)
  uint16_t ten_second_average;                             // 10초 평균값
  float battery_percentage;                                // 배터리 잔량 퍼센트 (소수점 2자리)
  float last_saved_percentage;                             // 마지막 저장된 퍼센트 (소수점 2자리)
  Battery_Status_t status;                                 // 배터리 상태
  
  uint32_t last_load_state_change_time;                    // 마지막 부하 상태 변경 시간
  bool is_under_load;                                      // 현재 부하 상태
  bool voltage_recovery_in_progress;                       // 전압 회복 진행 중
  bool is_power_on_sequence;                               // 전원 켜짐 시퀀스 중
  
  uint32_t last_update_time;                              // 마지막 업데이트 시간
  uint32_t last_flash_save_time;                          // 마지막 플래시 저장 시간
  uint32_t power_on_time;                                 // 전원 켜진 시간
} Battery_Monitor_t;

  // LED PWM 제어를 위한 변수들
  typedef enum
  {
    LED_STATE_LOW = 0,
    LED_STATE_MIDDLE,
    LED_STATE_HIGH
  } LED_State_t;

  typedef enum
  {
    BUTTON_STATE_STANDBY = 0,
    BUTTON_STATE_TIMER_SET,
  } Button_State_t;

  typedef struct
  {
    uint16_t LED1_ADC_Value; // LED1 ADC 값
    uint16_t LED2_ADC_Value; // LED2 ADC 값
    uint16_t VBat_ADC_Value; // VBat ADC 값

    LED_State_t LED1_State;    // LED1 상태
    LED_State_t LED2_State;    // LED2 상태
    uint32_t State_Start_Time; // 상태 시작 시간
    uint16_t Current_PWM_Duty; // 현재 PWM 듀티
    bool Cut_Off_PWM;          // PWM 차단 여부

    // VBat 필터링 관련 필드들
    uint16_t VBat_Filtered;                 // 필터링된 VBat 값
    uint16_t VBat_Buffer[VBAT_FILTER_SIZE]; // VBat 이동평균 버퍼
    uint8_t VBat_Buffer_Index;              // VBat 버퍼 인덱스
    uint8_t VBat_Buffer_Full;               // VBat 버퍼 채워짐 여부
  } Adc_t;

  // 버튼 제어를 위한 변수들
  typedef struct
  {
    uint8_t Timer_Value;           // 타이머 초기값 5
    uint32_t Timer_Set_Start_Time; // TIMER_SET 상태 비활성화 시간 추적

    int8_t second_count; // 타이머 초 카운트
    int8_t minute_count; // 타이머 분 카운트

    Button_State_t Current_Button_State; // 현재 버튼 상태
    bool is_Start_Timer;                 // 타이머 시작 여부

    uint32_t Button_Press_Start_Time; // 버튼 누름 시작 시간

    GPIO_PinState Button_Current_State; // 현재 버튼 상태
    GPIO_PinState Button_Prev_State;    // 이전 버튼 상태
    uint32_t Button_Press_Duration;     // 버튼 누름 지속 시간
    uint32_t Button_Current_Time;       // 현재 시간

    // 버튼 안정화를 위한 디바운싱 변수
    bool is_pushed_changed;   // 버튼 누름 상태로 인한 변경여부
    bool is_start_to_cooling; // 쿨링 시작 여부
    int8_t cooling_second;    // 쿨링 초 카운트
    
    // 더블 클릭 감지를 위한 변수들
    uint32_t last_click_time;     // 마지막 클릭 시간
    uint8_t click_count;          // 클릭 카운트
    bool double_click_detected;   // 더블 클릭 감지 여부
    
    // 단일클릭 지연 처리를 위한 변수들
    bool pending_single_click;    // 대기 중인 단일클릭 여부
    uint32_t single_click_time;   // 단일클릭 발생 시간
    uint32_t single_click_duration; // 단일클릭 버튼 누름 시간
    
    // 배터리 표시 토글
    bool show_battery_voltage;    // true: 전압 표시, false: 퍼센트 표시
  } Button_t;

  /* USER CODE END ET */

  /* Exported constants --------------------------------------------------------*/
  /* USER CODE BEGIN EC */

  /* USER CODE END EC */

  /* Exported macro ------------------------------------------------------------*/
  /* USER CODE BEGIN EM */

  /* USER CODE END EM */

  void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

  /* Exported functions prototypes ---------------------------------------------*/
  void Error_Handler(void);

  /* USER CODE BEGIN EFP */
  void RTOS_Start(void);
  void StartOneSecondTask(void *argument);
  void StartAdcTask(void *argument);
  void StartDisplayTask(void *argument);
  void StartButtonTask(void *argument);
  void Callback01(void *argument);

  // 플래시 저장 관련 함수 선언
  void Timer_LoadFromFlash(void);
  void Timer_SaveToFlash(uint32_t timer_value);

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define LCD_CLK_Pin GPIO_PIN_1
#define LCD_CLK_GPIO_Port GPIOA
#define LED_PWM_Pin GPIO_PIN_3
#define LED_PWM_GPIO_Port GPIOA
#define LED1_ADC_Pin GPIO_PIN_5
#define LED1_ADC_GPIO_Port GPIOA
#define LCD_DIN_Pin GPIO_PIN_7
#define LCD_DIN_GPIO_Port GPIOA
#define LED2_ADC_Pin GPIO_PIN_0
#define LED2_ADC_GPIO_Port GPIOB
#define VBat_ADC_Pin GPIO_PIN_1
#define VBat_ADC_GPIO_Port GPIOB
#define FAN_ONOFF_Pin GPIO_PIN_12
#define FAN_ONOFF_GPIO_Port GPIOB
#define LCD_CS_Pin GPIO_PIN_14
#define LCD_CS_GPIO_Port GPIOB
#define LCD_DC_Pin GPIO_PIN_15
#define LCD_DC_GPIO_Port GPIOB
#define LCD_RES_Pin GPIO_PIN_8
#define LCD_RES_GPIO_Port GPIOA
#define DEBUG_TX_Pin GPIO_PIN_9
#define DEBUG_TX_GPIO_Port GPIOA
#define DEBUG_RX_Pin GPIO_PIN_10
#define DEBUG_RX_GPIO_Port GPIOA
#define Setting_Button_Pin GPIO_PIN_5
#define Setting_Button_GPIO_Port GPIOB
#define System_LED_Pin GPIO_PIN_9
#define System_LED_GPIO_Port GPIOB

#define OUT_DC_EN_Pin GPIO_PIN_14
#define OUT_DC_EN_GPIO_Port GPIOC

#define DUTY_100 800
#define DUTY_50 400
#define DUTY_5 40
#define DUTY_0 0

#define LED_LOW_MAX 2100
#define LED_LOW_MIN 1500
#define LED_MIDDLE_MAX 2800
#define LED_MIDDLE_MIN 2100
#define LED_HIGH_MAX 4095
#define LED_HIGH_MIN 2800

#define BATTERY_MAX 3720 //25.2V
#define BATTERY_FULL 3640 
#define BATTERY_MIN 2740 //18.6V

#define WARNING_BATTERY_VOLTAGE 20.0f
  /* USER CODE BEGIN Private defines */

  /* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
