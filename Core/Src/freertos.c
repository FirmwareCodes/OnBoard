/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * File Name          : freertos.c
 * Description        : Code for freertos applications
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

/* Includes ------------------------------------------------------------------*/
#include "FreeRTOS.h"
#include "task.h"
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "def.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "../../App/Common/Inc/OLED/UI_Layout.h"
#include "../../App/Common/Inc/OLED/DEV_Config.h"
#include "../../App/Common/Inc/OLED/OLED_1in3_c.h"
// #include "flash_storage.h"
#include "uart_protocol.h"
#include "battery_monitor.h"

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* Definitions for OneSecondTask */
osThreadId_t OneSecondTaskHandle;
const osThreadAttr_t OneSecondTask_attributes = {
    .name = "OneSecondTask",
    .stack_size = 128 * 4,
    .priority = (osPriority_t)osPriorityNormal,
};
/* Definitions for AdcTask */
osThreadId_t AdcTaskHandle;
const osThreadAttr_t AdcTask_attributes = {
    .name = "AdcTask",
    .stack_size = 128 * 4,
    .priority = (osPriority_t)osPriorityHigh,
};
/* Definitions for DisplayTask */
osThreadId_t DisplayTaskHandle;
const osThreadAttr_t DisplayTask_attributes = {
    .name = "DisplayTask",
    .stack_size = 256 * 4,
    .priority = (osPriority_t)osPriorityLow,
};
/* Definitions for ButtonTask */
osThreadId_t ButtonTaskHandle;
const osThreadAttr_t ButtonTask_attributes = {
    .name = "ButtonTask",
    .stack_size = 128 * 4,
    .priority = (osPriority_t)osPriorityNormal1,
};
/* Definitions for UartTask */
osThreadId_t UartTaskHandle;
const osThreadAttr_t UartTask_attributes = {
    .name = "UartTask",
    .stack_size = 1024 * 4,                      // 스택 크기 대폭 증가 (512*4 -> 1024*4)
    .priority = (osPriority_t)osPriorityNormal1, // 우선순위 낮춤 (High1 -> Normal1)
};
/* Definitions for UartMutex */
osMutexId_t UartMutexHandle;
const osMutexAttr_t UartMutex_attributes = {
    .name = "UartMutex",
    .attr_bits = osMutexPrioInherit, // 우선순위 상속으로 priority inversion 방지
};
/* Definitions for MainTimer */
osTimerId_t MainTimerHandle;
const osTimerAttr_t MainTimer_attributes = {
    .name = "MainTimer",
};
/* Definitions for MainStatusEvent */
osEventFlagsId_t MainStatusEventHandle;
const osEventFlagsAttr_t MainStatusEvent_attributes = {
    .name = "MainStatusEvent"};
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
/* USER CODE BEGIN Variables */
extern ADC_HandleTypeDef hadc1;
extern ADC_HandleTypeDef hadc2;
extern UART_HandleTypeDef huart1;
extern TIM_HandleTypeDef htim2;

Adc_t Adc_State = {
    .LED1_ADC_Value = 0,            // LED1 ADC 값
    .LED2_ADC_Value = 0,            // LED2 ADC 값
    .VBat_ADC_Value = 0,            // VBat ADC 값
    .LED1_State = LED_STATE_MIDDLE, // LED1 상태
    .LED2_State = LED_STATE_MIDDLE, // LED2 상태
    .State_Start_Time = 0,          // 상태 시작 시간
    .Current_PWM_Duty = 0,          // 현재 PWM 듀티
    .Cut_Off_PWM = false,           // PWM 차단 여부
    .VBat_Filtered = 0,             // 필터링된 VBat 값
    .VBat_Buffer = {0},             // VBat 이동평균 버퍼
    .VBat_Buffer_Index = 0,         // VBat 버퍼 인덱스
    .VBat_Buffer_Full = 0,          // VBat 버퍼 채워짐 여부
};

Button_t Button_State = {
    .Timer_Value = 10,                            // 타이머 초기값 (플래시에서 로드될 예정)
    .Timer_Set_Start_Time = 0,                    // TIMER_SET 상태 비활성화 시간
    .second_count = 0,                            // 타이머 초 카운트
    .minute_count = 0,                            // 타이머 분 카운트
    .Current_Button_State = BUTTON_STATE_STANDBY, // 현재 버튼 상태
    .Button_Press_Start_Time = 0,                 // 버튼 누름 시작 시간
    .Button_Press_Duration = 0,                   // 버튼 누름 지속 시간
    .Button_Current_Time = 0,                     // 현재 시간
    .Button_Current_State = GPIO_PIN_SET,         // 현재 버튼 상태
    .Button_Prev_State = GPIO_PIN_SET,            // 이전 버튼 상태
    .is_pushed_changed = false,                   // 버튼 누름 상태로 인한 변경여부
    .is_start_to_cooling = false,                 // 쿨링 시작 여부
    .cooling_second = 0,                          // 쿨링 초 카운트
    .last_click_time = 0,                         // 마지막 버튼 클릭 시간
    .click_count = 0,                             // 더블 클릭 카운트
    .double_click_detected = false,               // 더블 클릭 감지 플래그
    .show_battery_voltage = false,                // 배터리 표시 토글 플래그
    .pending_single_click = false,                // 대기 중인 단일클릭 플래그
    .single_click_time = 0,                       // 단일클릭 시작 시간
    .single_click_duration = 0,                   // 단일클릭 지속 시간
};

UART_State_t UART_State = {
    .rx_index = 0,
    .cmd_index = 0,
    .command_ready = 0,
    .monitoring_enabled = 0};

// UI 상태 초기화
UI_Status_t current_status = {
    .battery_voltage = 0.0f,
    .timer_minutes = 0,
    .timer_seconds = 0,
    .timer_status = TIMER_STATUS_STANDBY,
    .warning_status = 0,
    .l1_connected = LED_DISCONNECTED,
    .l2_connected = LED_DISCONNECTED,
    .cooling_seconds = 0,
    .progress_update_counter = 0,
    .blink_counter = 0,
    .force_full_update = 1,     // 첫 번째는 전체 업데이트
    .timer_indicator_blink = 0, // 타이머 표시기 초기값
    .init_animation_active = 0, // 애니메이션 비활성 상태로 시작
    .animation_voltage = 19.0f,
    .animation_counter = 0,
    .timer_toggle_switch = {// 토글 스위치 초기화
                            .x = 0,
                            .y = 0,
                            .state = TOGGLE_STATE_OFF,
                            .target_state = TOGGLE_STATE_OFF,
                            .animation_step = 0,
                            .last_update_time = 0,
                            .is_animating = 0}};

// 새로운 배터리 모니터링 시스템
Battery_Monitor_t Battery_Monitor = {0};

bool is_can_use_vbat = false;

bool is_half_second_tick = false;

/* USER CODE END Variables */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN FunctionPrototypes */
void StartOneSecondTask(void *argument);
void StartAdcTask(void *argument);
void StartDisplayTask(void *argument);
void StartButtonTask(void *argument);
void StartUartTask(void *argument);
void Callback01(void *argument);

/* USER CODE END FunctionPrototypes */

/* Private application code --------------------------------------------------*/
/* USER CODE BEGIN Application */

/* USER CODE END Application */

void RTOS_Start(void)
{
  osKernelInitialize();

  /* USER CODE BEGIN RTOS_MUTEX */
  /* Create the mutex(es) */
  /* creation of UartMutex */
  UartMutexHandle = osMutexNew(&UartMutex_attributes);
  if (UartMutexHandle == NULL)
  {
    Error_Handler();
  }
  /* USER CODE END RTOS_MUTEX */

  /* USER CODE BEGIN RTOS_SEMAPHORES */
  /* add semaphores, ... */
  /* USER CODE END RTOS_SEMAPHORES */

  /* Create the timer(s) */
  /* creation of MainTimer */
  MainTimerHandle = osTimerNew(Callback01, osTimerPeriodic, NULL, &MainTimer_attributes);

  /* USER CODE BEGIN RTOS_TIMERS */
  /* start timers, add new ones, ... */

  // 플래시에서 타이머 값 로드
  // Timer_LoadFromFlash();

  // 배터리 모니터링 시스템 초기화
  Battery_Monitor_Init(&Battery_Monitor);

  /* USER CODE END RTOS_TIMERS */

  /* USER CODE BEGIN RTOS_QUEUES */
  /* add queues, ... */
  /* USER CODE END RTOS_QUEUES */

  /* Create the thread(s) */
  /* creation of OneSecondTask */
  OneSecondTaskHandle = osThreadNew(StartOneSecondTask, NULL, &OneSecondTask_attributes);
  if (OneSecondTaskHandle == NULL)
  {
    Error_Handler();
  }
  osDelay(10); // 태스크 생성 안정화

  /* creation of AdcTask */
  AdcTaskHandle = osThreadNew(StartAdcTask, NULL, &AdcTask_attributes);
  if (AdcTaskHandle == NULL)
  {
    Error_Handler();
  }
  osDelay(10); // 태스크 생성 안정화

  /* creation of ButtonTask */
  ButtonTaskHandle = osThreadNew(StartButtonTask, NULL, &ButtonTask_attributes);
  if (ButtonTaskHandle == NULL)
  {
    Error_Handler();
  }
  osDelay(10); // 태스크 생성 안정화

  /* creation of DisplayTask */
  DisplayTaskHandle = osThreadNew(StartDisplayTask, NULL, &DisplayTask_attributes);
  if (DisplayTaskHandle == NULL)
  {
    Error_Handler();
  }
  osDelay(10); // 태스크 생성 안정화

  /* creation of UartTask */
  UartTaskHandle = osThreadNew(StartUartTask, NULL, &UartTask_attributes);
  if (UartTaskHandle == NULL)
  {
    Error_Handler();
  }
  osDelay(10); // 태스크 생성 안정화

  /* USER CODE BEGIN RTOS_THREADS */
  /* add threads, ... */
  /* USER CODE END RTOS_THREADS */

  /* Create the event(s) */
  /* creation of MainStatusEvent */
  MainStatusEventHandle = osEventFlagsNew(&MainStatusEvent_attributes);

  /* USER CODE BEGIN RTOS_EVENTS */
  /* add events, ... */
  /* USER CODE END RTOS_EVENTS */

  /* Start scheduler */
  osKernelStart();

  /* We should never get here as control is now taken by the scheduler */
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/* USER CODE BEGIN Header_StartOneSecondTask */
/**
 * @brief  Function implementing the OneSecondTask thread.
 * @param  argument: Not used
 * @retval None
 */
/* USER CODE END Header_StartOneSecondTask */
void StartOneSecondTask(void *argument)
{

  /* USER CODE BEGIN 5 */
  UNUSED(argument);
  TickType_t lastWakeTime;
  lastWakeTime = xTaskGetTickCount();

  /* Infinite loop */
  for (;;)
  {

    // 타이머 시작 시간
    if (is_can_use_vbat == true)
      HAL_GPIO_TogglePin(System_LED_GPIO_Port, System_LED_Pin);
    else if (is_can_use_vbat == false && HAL_GPIO_ReadPin(System_LED_GPIO_Port, System_LED_Pin) == GPIO_PIN_SET)
    {
      HAL_GPIO_WritePin(System_LED_GPIO_Port, System_LED_Pin, GPIO_PIN_RESET);
    }

    vTaskDelayUntil(&lastWakeTime, 1000 * portTICK_PERIOD_MS);
  }
  /* USER CODE END 5 */
}

/* USER CODE BEGIN Header_StartAdcTask */
/**
 * @brief Function implementing the AdcTask thread.
 * @param argument: Not used
 * @retval None
 */
/* USER CODE END Header_StartAdcTask */
void StartAdcTask(void *argument)
{
  UNUSED(argument);
  /* USER CODE BEGIN StartAdcTask */
  TickType_t lastWakeTime;
  lastWakeTime = xTaskGetTickCount();

  ADC_ChannelConfTypeDef sConfig1 = {0}; // ADC1용 설정
  ADC_ChannelConfTypeDef sConfig2 = {0}; // ADC2용 설정

  // LED 상태 관련 변수들
  LED_State_t prev_LED1_State = LED_STATE_MIDDLE;
  LED_State_t prev_LED2_State = LED_STATE_MIDDLE;
  uint32_t state_timer = 0;
  uint16_t target_duty = 0;
  uint8_t last_button_state = 0;

  // VBat 필터링 관련 변수들
  uint32_t vbat_sum = 0;
  uint8_t vbat_samples = 0;

  is_can_use_vbat = true;

  // PWM 시작
  HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_4);

  /* Infinite loop */
  for (;;)
  {
    // LED1 ADC 읽기
    sConfig2.Channel = ADC_CHANNEL_10;
    sConfig2.Rank = ADC_REGULAR_RANK_1;
    sConfig2.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    sConfig2.SingleDiff = ADC_SINGLE_ENDED;
    sConfig2.OffsetNumber = ADC_OFFSET_NONE;
    sConfig2.Offset = 0;
    HAL_ADC_ConfigChannel(&hadc2, &sConfig2);
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 1000);
    Adc_State.LED1_ADC_Value = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);

    // LED2 ADC 읽기
    sConfig2.Channel = ADC_CHANNEL_15;
    HAL_ADC_ConfigChannel(&hadc2, &sConfig2);
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 1000);
    Adc_State.LED2_ADC_Value = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);

    // VBat ADC 읽기 (여러 번 샘플링하여 평균화)
    sConfig1.Channel = ADC_CHANNEL_16;
    sConfig1.Rank = ADC_REGULAR_RANK_1;
    sConfig1.SamplingTime = ADC_SAMPLETIME_24CYCLES_5; // 더 긴 샘플링 시간으로 안정성 향상
    sConfig1.SingleDiff = ADC_SINGLE_ENDED;
    sConfig1.OffsetNumber = ADC_OFFSET_NONE;
    sConfig1.Offset = 0;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig1);

    // VBat 5회 연속 샘플링하여 평균값 계산
    vbat_sum = 0;
    vbat_samples = 5;
    for (uint8_t i = 0; i < vbat_samples; i++)
    {
      HAL_ADC_Start(&hadc1);
      HAL_ADC_PollForConversion(&hadc1, 1000);
      vbat_sum += HAL_ADC_GetValue(&hadc1);
      HAL_ADC_Stop(&hadc1);
      osDelay(5); // 2ms 간격으로 샘플링
    }

    // 평균값 계산
    uint16_t vbat_current = vbat_sum / vbat_samples;

    // 이동평균 필터 적용 (8개 샘플)
    Adc_State.VBat_Buffer[Adc_State.VBat_Buffer_Index] = vbat_current;
    Adc_State.VBat_Buffer_Index = (Adc_State.VBat_Buffer_Index + 1) % VBAT_FILTER_SIZE;

    if (!Adc_State.VBat_Buffer_Full && Adc_State.VBat_Buffer_Index == 0)
    {
      Adc_State.VBat_Buffer_Full = 1; // 버퍼가 한 번 다 채워짐
    }

    // 이동평균 계산
    uint32_t filtered_sum = 0;
    uint8_t samples_count = Adc_State.VBat_Buffer_Full ? VBAT_FILTER_SIZE : (Adc_State.VBat_Buffer_Index + 1);

    for (uint8_t i = 0; i < samples_count; i++)
    {
      filtered_sum += Adc_State.VBat_Buffer[i];
    }

    uint16_t filtered_value = filtered_sum / samples_count;

    // 급격한 변화 방지 (임계값 기반 필터링)
    if (Adc_State.VBat_Filtered == 0)
    {
      // 첫 번째 값은 그대로 사용
      Adc_State.VBat_Filtered = filtered_value;
    }
    else
    {
      // 이전 값과 차이가 30 이상이면 점진적으로 변경 (노이즈 제거)
      int16_t diff = filtered_value - Adc_State.VBat_Filtered;
      if (abs(diff) > 15)
      {
        // 점진적 변경 (차이의 1/4씩 적용)
        Adc_State.VBat_Filtered += diff / 4;
      }
      else
      {
        // 작은 변화는 그대로 적용
        Adc_State.VBat_Filtered = filtered_value;
      }
    }
    // 최종 필터링된 값을 VBat_ADC_Value에 저장
    Adc_State.VBat_ADC_Value = Adc_State.VBat_Filtered;

    if (Adc_State.VBat_Buffer_Index >= VBAT_FILTER_SIZE - 1)
    {
      if (vbat_current < SYSTEM_CUT_OFF_VOLTAGE && is_can_use_vbat == true)
      {
        is_can_use_vbat = false;
        // 초기 화면 클리어
        Paint_Clear(BLACK);
        OLED_1in3_C_Display(BlackImage);
        osDelay(100);
        OLED_1in3_C_LCD_OFF();
      }
      else if (is_can_use_vbat == false && vbat_current > SYSTEM_RECOVERY_VOLTAGE)
      {
        is_can_use_vbat = true;
        NVIC_SystemReset();
      }
    }

    // 간단한 LED 상태 판단 LOW(1500~2050) MIDDLE(2050~2500) HIGH(2500~4095) 0630 기준
    // LOW 1.5V(1900) , MIDDLE 1.77V(2200) , HIGH 2.4V(3000)
    Adc_State.LED1_State = (Adc_State.LED1_ADC_Value < LED_LOW_MAX && Adc_State.LED1_ADC_Value > LED_LOW_MIN) ? LED_STATE_LOW : (Adc_State.LED1_ADC_Value >= LED_HIGH_MIN && Adc_State.LED1_ADC_Value <= LED_HIGH_MAX) ? LED_STATE_HIGH
                                                                                                                                                                                                                       : LED_STATE_MIDDLE;

    Adc_State.LED2_State = (Adc_State.LED2_ADC_Value < LED_LOW_MAX && Adc_State.LED2_ADC_Value > LED_LOW_MIN) ? LED_STATE_LOW : (Adc_State.LED2_ADC_Value >= LED_HIGH_MIN && Adc_State.LED2_ADC_Value <= LED_HIGH_MAX) ? LED_STATE_HIGH
                                                                                                                                                                                                                       : LED_STATE_MIDDLE;

    // 상태 변화 감지 및 타이머
    if (Adc_State.LED1_State != prev_LED1_State || Adc_State.LED2_State != prev_LED2_State)
    {
      state_timer = xTaskGetTickCount();
      prev_LED1_State = Adc_State.LED1_State;
      prev_LED2_State = Adc_State.LED2_State;
    }

    // 100ms 안정화 후 PWM 설정
    if (state_timer != 0 && (xTaskGetTickCount() - state_timer) >= (100 / portTICK_PERIOD_MS))
    {
      // 단순화된 PWM 로직
      if ((Adc_State.LED1_State == LED_STATE_LOW && Adc_State.LED2_State == LED_STATE_LOW) ||
          (Adc_State.LED1_State == LED_STATE_HIGH || Adc_State.LED2_State == LED_STATE_HIGH))
      {
        target_duty = DUTY_100;
      }
      else if ((Adc_State.LED1_State == LED_STATE_LOW && Adc_State.LED2_State == LED_STATE_MIDDLE) ||
               (Adc_State.LED2_State == LED_STATE_LOW && Adc_State.LED1_State == LED_STATE_MIDDLE))
      {
        target_duty = DUTY_50;
      }
      else
      {
        target_duty = DUTY_0;
      }

      if (Adc_State.Current_PWM_Duty != target_duty)
      {
        Adc_State.Current_PWM_Duty = target_duty;
        state_timer = 0;
      }
    }

    // PWM 출력 제어
    if (last_button_state != Button_State.is_Start_Timer)
    {
      last_button_state = Button_State.is_Start_Timer;
    }

    // 타이머 실행 시 차단 상태에서는 0% 출력, 아니면 현재 PWM 듀티 출력
    uint16_t pwm_duty = Button_State.is_Start_Timer ? (Adc_State.Cut_Off_PWM ? DUTY_0 : Adc_State.Current_PWM_Duty) : DUTY_0;

    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, pwm_duty);

    uint8_t CAM_ONOFF = HAL_GPIO_ReadPin(CAM_ONOFF_GPIO_Port, CAM_ONOFF_Pin);
    if (Adc_State.Cut_Off_PWM && CAM_ONOFF != GPIO_PIN_RESET)
    {
      HAL_GPIO_WritePin(CAM_ONOFF_GPIO_Port, CAM_ONOFF_Pin, GPIO_PIN_RESET);
    }
    else if (!Adc_State.Cut_Off_PWM && CAM_ONOFF != GPIO_PIN_SET)
    {
      HAL_GPIO_WritePin(CAM_ONOFF_GPIO_Port, CAM_ONOFF_Pin, GPIO_PIN_SET);
    }

    vTaskDelayUntil(&lastWakeTime, 50 * portTICK_PERIOD_MS);
  }
  /* USER CODE END StartAdcTask */
}

/* USER CODE BEGIN Header_StartDisplayTask */
/**
 * @brief Function implementing the DisplayTask thread.
 * @param argument: Not used
 * @retval None
 */
/* USER CODE END Header_StartDisplayTask */
void StartDisplayTask(void *argument)
{
  UNUSED(argument);
  /* USER CODE BEGIN StartDisplayTask */
  TickType_t lastWakeTime;
  lastWakeTime = xTaskGetTickCount();

  // UI 시스템 초기화 (메인에서 기본 초기화가 완료된 후)
  UI_Init();

  osDelay(500);

  // 첫 번째 전압 측정 및 초기 애니메이션 시작
  Battery_Monitor_Update(&Battery_Monitor, Adc_State.VBat_ADC_Value, false);
  float initial_voltage = Battery_Get_Voltage(&Battery_Monitor);

  // 초기 애니메이션 시작
  UI_StartInitAnimation(&current_status, initial_voltage);

  // 토글 스위치 초기화 (우측 영역 중앙에 위치)
  uint16_t toggle_x = INFO_AREA_X + (INFO_AREA_WIDTH / 2) - (TOGGLE_SWITCH_WIDTH / 2) - 1;
  uint16_t toggle_y = INFO_STATUS_Y + 2;
  UI_InitToggleSwitch(&current_status.timer_toggle_switch, toggle_x, toggle_y);

  /* Infinite loop */
  for (;;)
  {
    if (is_can_use_vbat == true)
    {
      // 카운터 증가
      current_status.progress_update_counter++;
      // blink_counter는 더 이상 시스템 틱 기반 깜빡임으로 대체되어 불필요

      // 배터리 모니터 업데이트
      Battery_Monitor_Update(&Battery_Monitor, Adc_State.VBat_ADC_Value, false);

      // 업데이트된 배터리 전압 사용
      float battery_voltage = Battery_Get_Voltage(&Battery_Monitor);

      // 타이머 상태 결정
      if (current_status.warning_status == 0)
      {
        if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
        {
          current_status.timer_status = TIMER_STATUS_SETTING;
        }
        else if (Button_State.is_start_to_cooling)
        {
          current_status.timer_status = TIMER_STATUS_COOLING;
        }
        else if (Button_State.is_Start_Timer)
        {
          current_status.timer_status = TIMER_STATUS_RUNNING;
        }
        else if (Button_State.Current_Button_State == BUTTON_STATE_STANDBY)
        {
          current_status.timer_status = TIMER_STATUS_STANDBY;
        }
      }
      else if (current_status.warning_status != 0)
      {
        current_status.timer_status = TIMER_STATUS_WARNING;
      }

      // 배터리 전압 기반 경고 상태 처리
      if (Battery_Get_Voltage(&Battery_Monitor) < CRITICAL_BATTERY_VOLTAGE && current_status.warning_status == 0)
      {
        current_status.timer_status = TIMER_STATUS_WARNING;
        current_status.warning_status = 1;
      }
      else if (Battery_Get_Voltage(&Battery_Monitor) > WARNING_BATTERY_VOLTAGE && current_status.warning_status != 0)
      {
        current_status.timer_status = TIMER_STATUS_STANDBY;
        current_status.warning_status = 0;
      }

      // 배터리 전압 기반 PWM 차단 로직, 배터리 전압 경고시 PWM 차단
      if (current_status.warning_status == 1)
      {
        Adc_State.Cut_Off_PWM = true;
      }
      else if (current_status.warning_status == 0)
      {
        Adc_State.Cut_Off_PWM = false;
      }

      // 타이머 시간 설정 (다운카운트)
      uint8_t timer_minutes = 0;
      uint8_t timer_seconds = 0;

      if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
      {
        // 타이머 설정 모드: 설정값 표시 (분:초)
        timer_minutes = Button_State.Timer_Value;
        timer_seconds = 0;
      }
      else
      {
        // 일반 모드: Callback01에서 사용되는 실제 카운트다운 값 표시
        if (Button_State.is_Start_Timer || Button_State.is_start_to_cooling)
        {
          // 실행 중이거나 쿨링 중일 때는 실제 카운트다운 값
          timer_minutes = (uint8_t)Button_State.minute_count;
          timer_seconds = (uint8_t)Button_State.second_count;

          // 쿨링 중일 때는 쿨링 시간을 초로 표시
          if (Button_State.is_start_to_cooling)
          {
            timer_minutes = Button_State.cooling_second / 60;
            timer_seconds = Button_State.cooling_second % 60;
          }
        }
        else
        {
          // 정지 상태에서는 설정된 초기값 표시
          timer_minutes = Button_State.Timer_Value;
          timer_seconds = 0;
        }
      }

      // LED 연결 상태 판단 (ADC 값 기반)
      LED_Connection_t l1_connected = LED_DISCONNECTED;
      LED_Connection_t l2_connected = LED_DISCONNECTED;

      // LED1 연결 상태 (ADC 값이 특정 범위에 있으면 연결됨)
      if (Adc_State.LED1_State != LED_STATE_MIDDLE)
      {
        l1_connected = Adc_State.LED1_State == LED_STATE_LOW ? LED_CONNECTED_2 : LED_CONNECTED_4;
      }

      // LED2 연결 상태 (ADC 값이 특정 범위에 있으면 연결됨)
      if (Adc_State.LED2_State != LED_STATE_MIDDLE)
      {
        l2_connected = Adc_State.LED2_State == LED_STATE_LOW ? LED_CONNECTED_2 : LED_CONNECTED_4;
      }

      // UI 상태 구조체 업데이트
      current_status.battery_voltage = battery_voltage; // 배터리 전압 업데이트
      current_status.battery_percentage = Battery_Get_Percentage_Float(&Battery_Monitor);
      current_status.timer_minutes = timer_minutes;
      current_status.timer_seconds = timer_seconds;
      current_status.l1_connected = l1_connected;
      current_status.l2_connected = l2_connected;
      current_status.cooling_seconds = (uint8_t)Button_State.cooling_second;

      UI_DrawFullScreenOptimized(&current_status);
    }
    vTaskDelayUntil(&lastWakeTime, current_status.init_animation_active ? 50 * portTICK_PERIOD_MS : UI_UPDATE_INTERVAL_MS * portTICK_PERIOD_MS);
  }
  // UI_UPDATE_INTERVAL_MS 주기로 업데이트
  /* USER CODE END StartDisplayTask */
}

/* USER CODE BEGIN Header_StartButtonTask */
/**
 * @brief Function implementing the ButtonTask thread.
 * @param argument: Not used
 * @retval None
 */
/* USER CODE END Header_StartButtonTask */
void StartButtonTask(void *argument)
{
  /* USER CODE BEGIN StartButtonTask */
  UNUSED(argument);
  TickType_t lastWakeTime;
  lastWakeTime = xTaskGetTickCount();

  bool is_Button_Pressed = false;                   // 버튼 누름 상태
  bool is_Button_Released = false;                  // 버튼 릴리즈 상태
  GPIO_PinState button_stable_state = GPIO_PIN_SET; // 버튼 바운드 상태
  uint8_t button_stable_count = 0;                  // 버튼 바운드 카운트

  /* Infinite loop */
  for (;;)
  {
    // 사용할수 있는 전압이고 경고 상태가 아니고 초기 애니메이션이 끝났으면
    if (is_can_use_vbat == true && current_status.timer_status != TIMER_STATUS_WARNING && !current_status.init_animation_active)
    {
      // Setting_Button 핀 상태 읽기 (PULLUP 설정이므로 평상시 HIGH, 눌리면 LOW)
      GPIO_PinState button_raw_state = HAL_GPIO_ReadPin(Setting_Button_GPIO_Port, Setting_Button_Pin);
      Button_State.Button_Current_Time = xTaskGetTickCount();

      // 디바운싱 처리 - 3번 연속 같은 상태일 때만 인정
      if (button_raw_state == button_stable_state)
      {
        button_stable_count++;
        if (button_stable_count >= 3)
        {
          Button_State.Button_Current_State = button_stable_state;
          button_stable_count = 3; // 오버플로우 방지
        }
      }
      else
      {
        button_stable_state = button_raw_state;
        button_stable_count = 1;
      }

      // 버튼 눌림 감지 (HIGH에서 LOW로 전환) - 안정화된 상태에서만 처리
      if (Button_State.Button_Prev_State == GPIO_PIN_SET &&
          Button_State.Button_Current_State == GPIO_PIN_RESET &&
          button_stable_count >= 3)
      {
        Button_State.Button_Press_Start_Time = Button_State.Button_Current_Time;
        is_Button_Pressed = true;
        is_Button_Released = false;
      }

      // 버튼 릴리즈 감지 (LOW에서 HIGH로 전환) - 안정화된 상태에서만 처리
      if (Button_State.Button_Prev_State == GPIO_PIN_RESET &&
          Button_State.Button_Current_State == GPIO_PIN_SET &&
          button_stable_count >= 3)
      {
        Button_State.Button_Press_Duration = Button_State.Button_Current_Time - Button_State.Button_Press_Start_Time;

        Button_State.is_pushed_changed = false;
        is_Button_Pressed = false;
        is_Button_Released = true;

        // 유효한 버튼 클릭인지 확인 (최소 20ms 이상)
        if (Button_State.Button_Press_Duration >= (20 / portTICK_PERIOD_MS))
        {
          uint32_t current_time = Button_State.Button_Current_Time;
          uint32_t time_since_last_click = current_time - Button_State.last_click_time;

          if (Button_State.last_click_time == 0 || time_since_last_click > (100 / portTICK_PERIOD_MS))
          {
            Button_State.pending_single_click = true;
            Button_State.single_click_time = current_time;
            Button_State.single_click_duration = Button_State.Button_Press_Duration;
            Button_State.last_click_time = current_time;
            Button_State.click_count = 1;
            Button_State.double_click_detected = false; // 새로운 클릭 시퀀스 시작
          }
        }
      }

      // 지연된 단일클릭 처리 - 500ms 후에 실행
      if (Button_State.pending_single_click)
      {
        uint32_t time_since_single_click = Button_State.Button_Current_Time - Button_State.single_click_time;

        // 500ms 대기 후 단일클릭 처리
        if (time_since_single_click >= (500 / portTICK_PERIOD_MS))
        {
          Button_State.pending_single_click = false;

          // 단일클릭 처리 (더블클릭이 감지된 경우 이미 pending_single_click이 false로 설정됨)
          // 버튼 상태에 따른 동작 처리
          switch (Button_State.Current_Button_State)
          {
          case BUTTON_STATE_STANDBY:
            // STANDBY에서 1초 이하 클릭 -> ON 상태로 전환
            if (Button_State.single_click_duration < (1000 / portTICK_PERIOD_MS) && !Button_State.is_start_to_cooling)
            {
              HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_SET);
              Button_State.is_Start_Timer = !Button_State.is_Start_Timer;

              if (Button_State.is_Start_Timer)
              {
                osTimerStart(MainTimerHandle, 500); // 1000ms = 1초 주기
                Button_State.minute_count = Button_State.Timer_Value;
                Button_State.second_count = 0; // 59초부터 시작 (첫 번째 콜백에서 59->58로)
              }
              else if (Button_State.Timer_Value - (uint8_t)Button_State.minute_count != 0 && Button_State.second_count <= 50)
              {
                Button_State.is_start_to_cooling = true;

                int8_t cooling_second = (Button_State.Timer_Value - (uint8_t)Button_State.minute_count) * 10;
                if (cooling_second > 60)
                {
                  cooling_second = 60;
                }
                Button_State.cooling_second = cooling_second;
              }
              else if (!Button_State.is_Start_Timer && !Button_State.is_start_to_cooling)
              {
                osTimerStop(MainTimerHandle);
                HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
              }
            }
            break;

          case BUTTON_STATE_TIMER_SET:
            // TIMER_SET에서 1초 이하 클릭 -> 타이머 값 증가
            if (Button_State.single_click_duration < (1000 / portTICK_PERIOD_MS))
            {
              Button_State.Timer_Value += 2;
              if (Button_State.Timer_Value > 10)
              {
                Button_State.Timer_Value = 2; // 10을 넘으면 1부터 다시 시작
              }

              // 타이머 값이 변경되었으므로 플래시에 저장
              // Timer_SaveToFlash((uint32_t)Button_State.Timer_Value);

              // TIMER_SET에서 활동이 있었으므로 비활성화 타이머 리셋
              Button_State.Timer_Set_Start_Time = Button_State.Button_Current_Time;
            }
            break;

          default:
            break;
          }
        }
      }

      // 버튼이 계속 눌려있는 상태에서 1.5초 이상 지나면 처리
      if (!Button_State.is_pushed_changed && is_Button_Pressed &&
          (Button_State.Button_Current_Time - Button_State.Button_Press_Start_Time) >= (1500 / portTICK_PERIOD_MS))
      {
        if (Button_State.Current_Button_State == BUTTON_STATE_STANDBY && !Button_State.is_Start_Timer)
        {
          Button_State.is_pushed_changed = true;
          Button_State.Current_Button_State = BUTTON_STATE_TIMER_SET;
          Button_State.Timer_Set_Start_Time = Button_State.Button_Current_Time; // TIMER_SET 진입시 비활성화 타이머 시작
        }
        else if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
        {
          // TIMER_SET에서 1.5초 이상 누르면 STANDBY로 복귀
          Button_State.is_pushed_changed = true;
          Button_State.Current_Button_State = BUTTON_STATE_STANDBY;

          // TIMER_SET 모드를 나갈 때 현재 타이머 값을 플래시에 저장
          // Timer_SaveToFlash((uint32_t)Button_State.Timer_Value);
        }
      }

      // TIMER_SET 상태에서 5초간 비활성화시 STANDBY로 복귀
      if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET && is_Button_Released)
      {
        if ((Button_State.Button_Current_Time - Button_State.Timer_Set_Start_Time) >= (5000 / portTICK_PERIOD_MS))
        {
          Button_State.Current_Button_State = BUTTON_STATE_STANDBY;

          // 5초 비활성화로 TIMER_SET 모드를 나갈 때도 플래시에 저장
          // Timer_SaveToFlash((uint32_t)Button_State.Timer_Value);
        }
      }

      // 이전 상태 업데이트 (안정화된 상태에서만)
      if (button_stable_count >= 3)
      {
        Button_State.Button_Prev_State = Button_State.Button_Current_State;
      }
    }
    else
    {
      if (Button_State.is_Start_Timer == true)
      {
        Button_State.is_Start_Timer = false;
        osTimerStop(MainTimerHandle);
        HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
      }
    }
    vTaskDelayUntil(&lastWakeTime, 10 * portTICK_PERIOD_MS);
  }
}
/* USER CODE END StartButtonTask */

/* USER CODE BEGIN Header_StartUartTask */
/**
 * @brief Function implementing the UartTask thread.
 * @param argument: Not used
 * @retval None
 */
/* USER CODE END Header_StartUartTask */
void StartUartTask(void *argument)
{
  UNUSED(argument);
  /* USER CODE BEGIN StartUartTask */
  TickType_t lastWakeTime;
  lastWakeTime = xTaskGetTickCount();

  // UART 상태 초기화
  UART_State.rx_index = 0;
  UART_State.cmd_index = 0;
  UART_State.command_ready = 0;
  UART_State.monitoring_enabled = 0;

  // 초기 안정화 대기
  osDelay(500);

  // UART 인터럽트 수신 시작
  if (HAL_UART_Receive_IT(&huart1, &UART_State.rx_buffer[UART_State.rx_index], 1) != HAL_OK)
  {
    // UART 인터럽트 시작 실패시 재시도
    osDelay(100);
    HAL_UART_Receive_IT(&huart1, &UART_State.rx_buffer[UART_State.rx_index], 1);
  }

  /* Infinite loop */
  for (;;)
  {
    // 1. 수신된 명령어 처리
    if (UART_State.command_ready && is_can_use_vbat == true)
    {
      UART_ProcessCommand();
    }

    // 정상 동작시 10ms 주기
    vTaskDelayUntil(&lastWakeTime, 10 * portTICK_PERIOD_MS);
  }
  /* USER CODE END StartUartTask */
}

/* Callback01 function */
void Callback01(void *argument)
{
  /* USER CODE BEGIN Callback01 */
  UNUSED(argument);
  is_half_second_tick = !is_half_second_tick;
  if (!is_half_second_tick)
  {
    if (Button_State.is_Start_Timer)
    {

      // 초 카운트다운
      if (Button_State.second_count > 0)
      {
        Button_State.second_count--;
      }
      else
      {
        // 초가 0이 되면 분 감소하고 초를 59로 리셋
        if (Button_State.minute_count > 0)
        {
          Button_State.minute_count--;
          Button_State.second_count = 59;
        }
        else
        {
          // 타이머 완료: 0분 0초 도달
          Button_State.is_Start_Timer = false;
          Button_State.is_start_to_cooling = true;

          // 쿨링 시간을 최소 30초, 최대 60초로 설정
          uint32_t cooling_time = Button_State.Timer_Value * 10;
          if (cooling_time < 30)
          {
            cooling_time = 10;
          }
          else if (cooling_time > 60)
          {
            cooling_time = 60;
          }
          Button_State.cooling_second = cooling_time;
        }
      }
    }
    else if (!Button_State.is_Start_Timer)
    {
      if (Button_State.is_start_to_cooling)
      {
        Button_State.cooling_second--;
        if (Button_State.cooling_second <= 0)
        {
          Button_State.is_start_to_cooling = false;
          osTimerStop(MainTimerHandle);
          HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
        }
      }
    }
  }

  /* USER CODE END Callback01 */
}

/**
 * @brief UART 수신 완료 콜백 (인터럽트) - 안정성 강화
 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART1)
  {
    uint8_t received_char = UART_State.rx_buffer[UART_State.rx_index];

    // 명령어 버퍼에 문자 저장
    if (received_char == '\n' || received_char == '\r')
    {
      // 명령어 완료 - 빈 명령어 체크
      if (UART_State.cmd_index > 0 && UART_State.cmd_index < sizeof(UART_State.cmd_buffer))
      {
        UART_State.cmd_buffer[UART_State.cmd_index] = '\0';
        UART_State.command_ready = 1;
      }
    }
    else
    {
      // 유효한 ASCII 문자만 허용 (32-126)
      if (received_char >= 32 && received_char <= 126)
      {
        if (UART_State.cmd_index < sizeof(UART_State.cmd_buffer) - 1)
        {
          UART_State.cmd_buffer[UART_State.cmd_index] = received_char;
          UART_State.cmd_index++;
        }
        else
        {
          // 버퍼 오버플로우 - 명령어 리셋
          UART_State.cmd_index = 0;
        }
      }
      // 제어 문자나 유효하지 않은 문자는 무시
    }

    // 다음 문자 수신 준비
    UART_State.rx_index = (UART_State.rx_index + 1) % sizeof(UART_State.rx_buffer);

    HAL_UART_Receive_IT(&huart1, &UART_State.rx_buffer[UART_State.rx_index], 1);
  }
}

// 스택 오버플로우 후크 함수
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
  UNUSED(xTask);
  UNUSED(pcTaskName);
  /* 스택 오버플로우 발생시 System LED를 빠르게 깜빡이며 에러 표시 */
  while (1)
  {
    HAL_GPIO_TogglePin(System_LED_GPIO_Port, System_LED_Pin);
    HAL_Delay(100);
  }
}
