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

  /* USER CODE END Includes */

  /* Exported types ------------------------------------------------------------*/
  /* USER CODE BEGIN ET */
  // LED PWM 제어를 위한 변수들
  typedef enum
  {
    LED_STATE_LOW = 0,
    LED_STATE_FLOATING,
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
  } Adc_t;

  // 버튼 제어를 위한 변수들
  typedef struct
  {
    uint8_t Timer_Value;           // 타이머 초기값 5
    uint32_t Timer_Set_Start_Time; // TIMER_SET 상태 비활성화 시간 추적

    uint32_t second_count; // 타이머 초 카운트
    uint32_t minute_count; // 타이머 분 카운트

    Button_State_t Current_Button_State; // 현재 버튼 상태
    bool is_Start_Timer;                 // 타이머 시작 여부

    uint32_t Button_Press_Start_Time; // 버튼 누름 시작 시간

    GPIO_PinState Button_Current_State; // 현재 버튼 상태
    GPIO_PinState Button_Prev_State;    // 이전 버튼 상태
    uint32_t Button_Press_Duration;     // 버튼 누름 지속 시간
    uint32_t Button_Current_Time;       // 현재 시간

    // 버튼 안정화를 위한 디바운싱 변수
    bool is_pushed_changed; // 버튼 누름 상태로 인한 변경여부
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

#define DUTY_100 800
#define DUTY_50 400
#define DUTY_0 0

  /* USER CODE BEGIN Private defines */

  /* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
