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
#include "GUI_Paint.h"
#include "OLED_1in3_c.h"
#include "ImageData.h"
#include "def.h"
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
    .stack_size = 256 * 4,
    .priority = (osPriority_t)osPriorityNormal,
};
/* Definitions for AdcTask */
osThreadId_t AdcTaskHandle;
const osThreadAttr_t AdcTask_attributes = {
    .name = "AdcTask",
    .stack_size = 384 * 4,
    .priority = (osPriority_t)osPriorityHigh,
};
/* Definitions for DisplayTask */
osThreadId_t DisplayTaskHandle;
const osThreadAttr_t DisplayTask_attributes = {
    .name = "DisplayTask",
    .stack_size = 384 * 4,
    .priority = (osPriority_t)osPriorityLow,
};
/* Definitions for ButtonTask */
osThreadId_t ButtonTaskHandle;
const osThreadAttr_t ButtonTask_attributes = {
    .name = "ButtonTask",
    .stack_size = 256 * 4,
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
    .Timer_Value = 5,                             // 타이머 초기값
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
};

/* USER CODE END Variables */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN FunctionPrototypes */

/* USER CODE END FunctionPrototypes */

/* Private application code --------------------------------------------------*/
/* USER CODE BEGIN Application */

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

  // 이동평균 필터를 위한 변수들
  // #define FILTER_SIZE 8
  //   uint16_t vbat_buffer[FILTER_SIZE] = {0};
  //   uint8_t filter_index = 0;

  // LED 상태 관련 변수들
  LED_State_t prev_LED1_State = LED_STATE_FLOATING;
  LED_State_t prev_LED2_State = LED_STATE_FLOATING;
  uint32_t current_time = 0;
  uint16_t target_duty = 0;

  uint8_t last_button_state = 0;

  // PWM 시작
  HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_4);

  /* Infinite loop */
  for (;;)
  {
    // LED1 ADC - ADC2 Channel 10 읽기
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

    // LED2 ADC - ADC2 Channel 15 읽기
    sConfig2.Channel = ADC_CHANNEL_15;
    sConfig2.Rank = ADC_REGULAR_RANK_1;
    sConfig2.SamplingTime = ADC_SAMPLETIME_92CYCLES_5;
    sConfig2.SingleDiff = ADC_SINGLE_ENDED;
    sConfig2.OffsetNumber = ADC_OFFSET_NONE;
    sConfig2.Offset = 0;
    HAL_ADC_ConfigChannel(&hadc2, &sConfig2);

    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 1000);
    Adc_State.LED2_ADC_Value = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);

    // VBat ADC - ADC1 Channel 16 읽기
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

    // // VBat에만 이동평균 필터 적용
    // vbat_buffer[filter_index] = temp_adc_value;
    // sum = 0;
    // for (int i = 0; i < FILTER_SIZE; i++)
    // {
    //   sum += vbat_buffer[i];
    // }
    // VBat_ADC_Value = sum / FILTER_SIZE;

    // // 필터 인덱스 업데이트
    // filter_index = (filter_index + 1) % FILTER_SIZE;

    // LED1 상태 판단
    if (Adc_State.LED1_ADC_Value == 0)
    {
      Adc_State.LED1_State = LED_STATE_LOW;
    }
    else if (Adc_State.LED1_ADC_Value >= 3000)
    {
      Adc_State.LED1_State = LED_STATE_HIGH;
    }
    else
    {
      Adc_State.LED1_State = LED_STATE_FLOATING;
    }

    // LED2 상태 판단
    if (Adc_State.LED2_ADC_Value == 0)
    {
      Adc_State.LED2_State = LED_STATE_LOW;
    }
    else if (Adc_State.LED2_ADC_Value >= 3000)
    {
      Adc_State.LED2_State = LED_STATE_HIGH;
    }
    else
    {
      Adc_State.LED2_State = LED_STATE_FLOATING;
    }

    // 상태 변화 감지
    if (Adc_State.LED1_State != prev_LED1_State || Adc_State.LED2_State != prev_LED2_State)
    {
      Adc_State.State_Start_Time = xTaskGetTickCount();
      prev_LED1_State = Adc_State.LED1_State;
      prev_LED2_State = Adc_State.LED2_State;
    }

    current_time = xTaskGetTickCount();

    // 0.1초(100ms) 이상 상태 유지 확인
    if (Adc_State.State_Start_Time != 0 && (current_time - Adc_State.State_Start_Time) >= (100 / portTICK_PERIOD_MS))
    {

      // PWM 듀티 결정 로직
      if (Adc_State.LED1_State == LED_STATE_LOW && Adc_State.LED2_State == LED_STATE_LOW)
      {
        // 둘다 Low -> 듀티 100%
        target_duty = DUTY_100;
      }
      else if (Adc_State.LED1_State == LED_STATE_HIGH || Adc_State.LED2_State == LED_STATE_HIGH)
      {
        // 둘다 High -> 듀티 100%
        target_duty = DUTY_100;
      }
      else if (Adc_State.LED1_State == LED_STATE_FLOATING && Adc_State.LED2_State == LED_STATE_FLOATING)
      {
        // 둘다 Floating -> 듀티 0%
        target_duty = DUTY_0;
      }
      else if ((Adc_State.LED1_State == LED_STATE_LOW && Adc_State.LED2_State == LED_STATE_FLOATING) ||
               (Adc_State.LED2_State == LED_STATE_LOW && Adc_State.LED1_State == LED_STATE_FLOATING))
      {
        // 1개만 Low -> 듀티 50%
        target_duty = DUTY_50;
      }
      else if ((Adc_State.LED1_State == LED_STATE_HIGH && Adc_State.LED2_State != LED_STATE_HIGH) ||
               (Adc_State.LED2_State == LED_STATE_HIGH && Adc_State.LED1_State != LED_STATE_HIGH))
      {
        // 1개만 High -> 듀티 100%
        target_duty = DUTY_100;
      }

      if (Adc_State.Current_PWM_Duty != target_duty)
      {
        Adc_State.Current_PWM_Duty = target_duty;
        Adc_State.State_Start_Time = 0;

        if (Button_State.is_Start_Timer)
        {
          __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, Adc_State.Current_PWM_Duty);
        }
        else if (!Button_State.is_Start_Timer)
        {
          __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, DUTY_0);
        }
      }
    }
    else if (Adc_State.Current_PWM_Duty != 0 && Adc_State.LED1_State == LED_STATE_FLOATING && Adc_State.LED2_State == LED_STATE_FLOATING)
    {
      // 둘다 Floating -> 듀티 0%
      target_duty = DUTY_0;

      if (Adc_State.Current_PWM_Duty != target_duty)
      {
        Adc_State.Current_PWM_Duty = target_duty;
        __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, Adc_State.Current_PWM_Duty);
        Adc_State.State_Start_Time = 0;
      }
    }

    if (last_button_state != Button_State.is_Start_Timer)
    {
      last_button_state = Button_State.is_Start_Timer;
      if (Button_State.is_Start_Timer)
      {
        __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, Adc_State.Current_PWM_Duty);
      }
      else if (!Button_State.is_Start_Timer)
      {
        __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, DUTY_0);
      }
    }

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

  /* Infinite loop */
  for (;;)
  {
    Paint_Clear(BLACK);

    Paint_DrawRectangle(1, 1, 128, 64, WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    // Paint_DrawLine(80, 20, 80, 64, WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID); // y-axis line
    // Paint_DrawLine(0, 20, 128, 20, WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID); // x-axis line
    char *button_state_str = (char *)(Button_State.is_Start_Timer == true ? "ON" : Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET ? "TIMER Set"
                                                                                                                                               : "OFF");
    Paint_DrawString_EN(5, 5, button_state_str, &Font12, 0, 0xFF);
    if (Button_State.is_Start_Timer)
    {
      char timer_str[12];
      sprintf(timer_str, "%1d m %02d s", (uint8_t)Button_State.minute_count, (uint8_t)Button_State.second_count);
      Paint_DrawString_EN(60, 5, timer_str, &Font12, 0, 0xFF);
    }

    if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
    {
      char timer_set_str[15];
      uint8_t blank_count = (lastWakeTime / 300) % 3;
      if (blank_count == 0)
      {
        strcpy(timer_set_str, "");
      }
      else
      {
        sprintf(timer_set_str, "Timer: %d min", Button_State.Timer_Value);
      }
      Paint_DrawString_EN(5, 24, timer_set_str, &Font12, 0x00, 0xFF);
    }
    else
    {
      char timer_set_str[15];
      sprintf(timer_set_str, "Timer: %d min", Button_State.Timer_Value);
      Paint_DrawString_EN(5, 24, timer_set_str, &Font12, 0x00, 0xFF);
    }

    OLED_1in3_C_Display(BlackImage);

    vTaskDelayUntil(&lastWakeTime, 100 * portTICK_PERIOD_MS);
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
          if (Button_State.Button_Press_Duration < (1000 / portTICK_PERIOD_MS))
          {
            Button_State.is_Start_Timer = !Button_State.is_Start_Timer;
            if (Button_State.is_Start_Timer)
            {
              osTimerStart(MainTimerHandle, 1001);
              Button_State.minute_count = 0;
              Button_State.second_count = 0;
            }
          }
          break;

        case BUTTON_STATE_TIMER_SET:
          // TIMER_SET에서 1초 이하 클릭 -> 타이머 값 증가
          if (Button_State.Button_Press_Duration < (1000 / portTICK_PERIOD_MS))
          {
            Button_State.Timer_Value++;
            if (Button_State.Timer_Value > 10)
            {
              Button_State.Timer_Value = 1; // 10을 넘으면 1부터 다시 시작
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
      if (Button_State.Current_Button_State == BUTTON_STATE_STANDBY || Button_State.is_Start_Timer)
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
    Button_State.second_count++;
    if (Button_State.second_count > 59)
    {
      Button_State.minute_count++;
      Button_State.second_count = 0;
    }
  }
  else if (!Button_State.is_Start_Timer)
  {
    Button_State.second_count = 0;
    Button_State.minute_count = 0;
  }

  if (Button_State.minute_count >= Button_State.Timer_Value)
  {
    Button_State.is_Start_Timer = false;
    osTimerStop(MainTimerHandle);
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

/* USER CODE END Application */
