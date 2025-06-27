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
    .LED1_ADC_Value = 0,              // LED1 ADC 값
    .LED2_ADC_Value = 0,              // LED2 ADC 값
    .VBat_ADC_Value = 0,              // VBat ADC 값
    .LED1_State = LED_STATE_FLOATING, // LED1 상태
    .LED2_State = LED_STATE_FLOATING, // LED2 상태
    .State_Start_Time = 0,            // 상태 시작 시간
    .Current_PWM_Duty = 0,            // 현재 PWM 듀티
};

Button_t Button_State = {
    .Timer_Value = 10,                            // 타이머 초기값
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
};

/* USER CODE END Variables */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN FunctionPrototypes */

/* USER CODE END FunctionPrototypes */

/* Private application code --------------------------------------------------*/
/* USER CODE BEGIN Application */

/* USER CODE END Application */

void RTOS_Start(void)
{
  osKernelInitialize();

  /* USER CODE BEGIN RTOS_MUTEX */
  /* add mutexes, ... */
  /* USER CODE END RTOS_MUTEX */

  /* USER CODE BEGIN RTOS_SEMAPHORES */
  /* add semaphores, ... */
  /* USER CODE END RTOS_SEMAPHORES */

  /* Create the timer(s) */
  /* creation of MainTimer */
  MainTimerHandle = osTimerNew(Callback01, osTimerPeriodic, NULL, &MainTimer_attributes);

  /* USER CODE BEGIN RTOS_TIMERS */
  /* start timers, add new ones, ... */
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

    HAL_GPIO_TogglePin(System_LED_GPIO_Port, System_LED_Pin);
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
  LED_State_t prev_LED1_State = LED_STATE_FLOATING;
  LED_State_t prev_LED2_State = LED_STATE_FLOATING;
  uint32_t state_timer = 0;
  uint16_t target_duty = 0;
  uint8_t last_button_state = 0;

  // PWM 시작
  HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_4);

  /* Infinite loop */
  for (;;)
  {
    // LED1 ADC 읽기
    sConfig2.Channel = ADC_CHANNEL_10;
    sConfig2.Rank = ADC_REGULAR_RANK_1;
    sConfig2.SamplingTime = ADC_SAMPLETIME_92CYCLES_5;
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

    // VBat ADC 읽기
    sConfig1.Channel = ADC_CHANNEL_16;
    sConfig1.Rank = ADC_REGULAR_RANK_1;
    sConfig1.SamplingTime = ADC_SAMPLETIME_12CYCLES_5;
    sConfig1.SingleDiff = ADC_SINGLE_ENDED;
    sConfig1.OffsetNumber = ADC_OFFSET_NONE;
    sConfig1.Offset = 0;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig1);
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 1000);
    Adc_State.VBat_ADC_Value = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    // 간단한 LED 상태 판단
    Adc_State.LED1_State = (Adc_State.LED1_ADC_Value == 0) ? LED_STATE_LOW : (Adc_State.LED1_ADC_Value >= 3000) ? LED_STATE_HIGH
                                                                                                                : LED_STATE_FLOATING;

    Adc_State.LED2_State = (Adc_State.LED2_ADC_Value == 0) ? LED_STATE_LOW : (Adc_State.LED2_ADC_Value >= 3000) ? LED_STATE_HIGH
                                                                                                                : LED_STATE_FLOATING;

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
      else if ((Adc_State.LED1_State == LED_STATE_LOW && Adc_State.LED2_State == LED_STATE_FLOATING) ||
               (Adc_State.LED2_State == LED_STATE_LOW && Adc_State.LED1_State == LED_STATE_FLOATING))
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

    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4,
                          Button_State.is_Start_Timer ? Adc_State.Current_PWM_Duty : DUTY_0);

    vTaskDelayUntil(&lastWakeTime, 20 * portTICK_PERIOD_MS);
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

  // 초기 화면 안정화를 위한 딜레이
  osDelay(200);

  // UI 상태 초기화
  UI_Status_t current_status = {
      .battery_percent = 0,
      .timer_minutes = 0,
      .timer_seconds = 0,
      .timer_status = TIMER_STATUS_STANDBY,
      .l1_connected = LED_DISCONNECTED,
      .l2_connected = LED_DISCONNECTED,
      .cooling_seconds = 0,
      .progress_update_counter = 0,
      .blink_counter = 0,
      .force_full_update = 1  // 첫 번째는 전체 업데이트
  };

  /* Infinite loop */
  for (;;)
  {
    // 카운터 증가
    current_status.progress_update_counter++;
    current_status.blink_counter++;
    
    // 배터리 전압을 퍼센티지로 변환 (ADC 값 기반)
    uint8_t battery_percent = 0;
    if (Adc_State.VBat_ADC_Value > 500)
    {                                                                                    // 3.0V 이상이면 배터리 상태 계산
      battery_percent = (uint8_t)((float)(Adc_State.VBat_ADC_Value - 500) / 2200 * 100); // 3.0V~4.2V 범위를 0~100%로 매핑
      if (battery_percent > 100)
        battery_percent = 100;
    }

    // 타이머 상태 결정
    Timer_Status_t timer_status = TIMER_STATUS_STANDBY;
    if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
    {
      timer_status = TIMER_STATUS_SETTING;
    }
    else if (Button_State.is_start_to_cooling)
    {
      timer_status = TIMER_STATUS_COOLING;
    }
    else if (Button_State.is_Start_Timer)
    {
      timer_status = TIMER_STATUS_RUNNING;
    }

    // 타이머 시간 설정 (다운카운트 지원)
    uint8_t timer_minutes = 0;
    uint8_t timer_seconds = 0;
    
    if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET) {
      // 타이머 설정 모드: 설정값 표시 (분:초)
      timer_minutes = Button_State.Timer_Value;
      timer_seconds = 0;
    } else {
      // 일반 모드: Callback01에서 사용되는 실제 카운트다운 값 표시
      if (Button_State.is_Start_Timer || Button_State.is_start_to_cooling) {
        // 실행 중이거나 쿨링 중일 때는 실제 카운트다운 값
        timer_minutes = (uint8_t)Button_State.minute_count;
        timer_seconds = (uint8_t)Button_State.second_count;
        
        // 쿨링 중일 때는 쿨링 시간을 초로 표시
        if (Button_State.is_start_to_cooling) {
          timer_minutes = Button_State.cooling_second / 60;
          timer_seconds = Button_State.cooling_second % 60;
        }
      } else {
        // 정지 상태에서는 설정된 초기값 표시
        timer_minutes = Button_State.Timer_Value;
        timer_seconds = 0;
      }
    }

    // LED 연결 상태 판단 (ADC 값 기반)
    LED_Connection_t l1_connected = LED_DISCONNECTED;
    LED_Connection_t l2_connected = LED_DISCONNECTED;

    // LED1 연결 상태 (ADC 값이 특정 범위에 있으면 연결됨)
    if (Adc_State.LED1_State != LED_STATE_FLOATING)
    {
      l1_connected = LED_CONNECTED;
    }

    // LED2 연결 상태 (ADC 값이 특정 범위에 있으면 연결됨)
    if (Adc_State.LED2_State != LED_STATE_FLOATING)
    {
      l2_connected = LED_CONNECTED;
    }

    // UI 상태 구조체 업데이트
    current_status.battery_percent = battery_percent;
    current_status.timer_minutes = timer_minutes;
    current_status.timer_seconds = timer_seconds;
    current_status.timer_status = timer_status;
    current_status.l1_connected = l1_connected;
    current_status.l2_connected = l2_connected;
    current_status.cooling_seconds = (uint8_t)Button_State.cooling_second;

    // 최적화된 화면 그리기
    UI_DrawFullScreenOptimized(&current_status);

    // 배터리 부족 경고 (10% 이하일 때)
    if (battery_percent <= 10 && battery_percent > 0)
    {
      // 5초마다 한 번씩 경고 표시 (50ms * 100 = 5초)
      static uint32_t low_battery_counter = 0;
      low_battery_counter++;
      if (low_battery_counter >= 100)
      {
        UI_ShowLowBatteryWarning();
        low_battery_counter = 0;
      }
    }

    // 타이머 완료 시 알림
    if (Button_State.minute_count == 0 && Button_State.second_count == 0 &&
        Button_State.is_Start_Timer && !Button_State.is_start_to_cooling)
    {
      UI_ShowTimerComplete();
    }

    // UI_UPDATE_INTERVAL_MS 주기로 업데이트
    vTaskDelayUntil(&lastWakeTime, UI_UPDATE_INTERVAL_MS * portTICK_PERIOD_MS);
  }
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

        // 버튼 상태에 따른 동작 처리
        switch (Button_State.Current_Button_State)
        {
        case BUTTON_STATE_STANDBY:
          // STANDBY에서 1초 이하 클릭 -> ON 상태로 전환
          if (Button_State.Button_Press_Duration < (1000 / portTICK_PERIOD_MS) && !Button_State.is_start_to_cooling)
          {
            Button_State.is_Start_Timer = !Button_State.is_Start_Timer;
            HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_SET);

            if (Button_State.is_Start_Timer)
            {
              osTimerStart(MainTimerHandle, 1000);  // 1000ms = 1초 주기
              Button_State.minute_count = Button_State.Timer_Value;
              Button_State.second_count = 59;  // 59초부터 시작 (첫 번째 콜백에서 59->58로)
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
            else if (Button_State.is_Start_Timer && !Button_State.is_start_to_cooling)
            {
              osTimerStop(MainTimerHandle);
              HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
            }
          }
          break;

        case BUTTON_STATE_TIMER_SET:
          // TIMER_SET에서 1초 이하 클릭 -> 타이머 값 증가
          if (Button_State.Button_Press_Duration < (1000 / portTICK_PERIOD_MS))
          {
            Button_State.Timer_Value += 2;
            if (Button_State.Timer_Value > 10)
            {
              Button_State.Timer_Value = 2; // 10을 넘으면 1부터 다시 시작
            }
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
      }
    }

    // TIMER_SET 상태에서 5초간 비활성화시 STANDBY로 복귀
    if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET && is_Button_Released)
    {
      if ((Button_State.Button_Current_Time - Button_State.Timer_Set_Start_Time) >= (5000 / portTICK_PERIOD_MS))
      {
        Button_State.Current_Button_State = BUTTON_STATE_STANDBY;
      }
    }

    // 이전 상태 업데이트 (안정화된 상태에서만)
    if (button_stable_count >= 3)
    {
      Button_State.Button_Prev_State = Button_State.Button_Current_State;
    }

    vTaskDelayUntil(&lastWakeTime, 10 * portTICK_PERIOD_MS);
  }
  /* USER CODE END StartButtonTask */
}

/* Callback01 function */
void Callback01(void *argument)
{
  /* USER CODE BEGIN Callback01 */
  UNUSED(argument);
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
          cooling_time = 30;
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
        HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
        osTimerStop(MainTimerHandle);
      }
    }
  }

  /* USER CODE END Callback01 */
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
