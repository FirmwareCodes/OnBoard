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
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
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
  BUTTON_STATE_ON,
  BUTTON_STATE_TIMER_SET,
  BUTTON_STATE_TIMER_UP,
} Button_State_t;
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

uint16_t LED1_ADC_Value = 0;
uint16_t LED2_ADC_Value = 0;
uint16_t VBat_ADC_Value = 0;

LED_State_t LED1_State = LED_STATE_FLOATING;
LED_State_t LED2_State = LED_STATE_FLOATING;
uint32_t State_Start_Time = 0;
uint16_t Current_PWM_Duty = 0;

// 버튼 제어를 위한 변수들
Button_State_t Current_Button_State = BUTTON_STATE_STANDBY;
uint8_t Timer_Value = 5; // 타이머 초기값 5
uint32_t Button_Press_Start_Time = 0;
uint8_t Button_Pressed = 0;
uint8_t Button_Released = 0;
uint32_t Timer_Set_Inactive_Start_Time = 0; // TIMER_SET 상태 비활성화 시간 추적

GPIO_PinState button_current_state = GPIO_PIN_SET;
GPIO_PinState button_prev_state = GPIO_PIN_SET;
uint32_t button_press_duration = 0;
uint32_t current_time = 0;

// 버튼 안정화를 위한 디바운싱 변수
uint8_t button_stable_count = 0;
GPIO_PinState button_stable_state = GPIO_PIN_SET;
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
    LED1_ADC_Value = HAL_ADC_GetValue(&hadc2);
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
    LED2_ADC_Value = HAL_ADC_GetValue(&hadc2);
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
    VBat_ADC_Value = HAL_ADC_GetValue(&hadc1);
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
    if (LED1_ADC_Value == 0)
    {
      LED1_State = LED_STATE_LOW;
    }
    else if (LED1_ADC_Value >= 3000)
    {
      LED1_State = LED_STATE_HIGH;
    }
    else
    {
      LED1_State = LED_STATE_FLOATING;
    }

    // LED2 상태 판단
    if (LED2_ADC_Value == 0)
    {
      LED2_State = LED_STATE_LOW;
    }
    else if (LED2_ADC_Value >= 3000)
    {
      LED2_State = LED_STATE_HIGH;
    }
    else
    {
      LED2_State = LED_STATE_FLOATING;
    }

    // 상태 변화 감지
    if (LED1_State != prev_LED1_State || LED2_State != prev_LED2_State)
    {
      State_Start_Time = xTaskGetTickCount();
      prev_LED1_State = LED1_State;
      prev_LED2_State = LED2_State;
    }

    current_time = xTaskGetTickCount();

    // 0.1초(100ms) 이상 상태 유지 확인
    if (State_Start_Time != 0 && (current_time - State_Start_Time) >= (100 / portTICK_PERIOD_MS))
    {

      // PWM 듀티 결정 로직
      if (LED1_State == LED_STATE_LOW && LED2_State == LED_STATE_LOW)
      {
        // 둘다 Low -> 듀티 100%
        target_duty = DUTY_100;
      }
      else if (LED1_State == LED_STATE_HIGH || LED2_State == LED_STATE_HIGH)
      {
        // 둘다 High -> 듀티 100%
        target_duty = DUTY_100;
      }
      else if (LED1_State == LED_STATE_FLOATING && LED2_State == LED_STATE_FLOATING)
      {
        // 둘다 Floating -> 듀티 0%
        target_duty = DUTY_0;
      }
      else if ((LED1_State == LED_STATE_LOW && LED2_State == LED_STATE_FLOATING) ||
               (LED2_State == LED_STATE_LOW && LED1_State == LED_STATE_FLOATING))
      {
        // 1개만 Low -> 듀티 50%
        target_duty = DUTY_50;
      }
      else if ((LED1_State == LED_STATE_HIGH && LED2_State != LED_STATE_HIGH) ||
               (LED2_State == LED_STATE_HIGH && LED1_State != LED_STATE_HIGH))
      {
        // 1개만 High -> 듀티 100%
        target_duty = DUTY_100;
      }

      if (Current_PWM_Duty != target_duty)
      {
        Current_PWM_Duty = target_duty;
        State_Start_Time = 0;

        if (Current_Button_State == BUTTON_STATE_ON)
        {
          __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, Current_PWM_Duty);
        }
        else if (Current_Button_State == BUTTON_STATE_STANDBY)
        {
          __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, DUTY_0);
        }
      }
    }
    else if (Current_PWM_Duty != 0 && LED1_State == LED_STATE_FLOATING && LED2_State == LED_STATE_FLOATING)
    {
      // 둘다 Floating -> 듀티 0%
      target_duty = DUTY_0;

      if (Current_PWM_Duty != target_duty)
      {
        Current_PWM_Duty = target_duty;
        __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, Current_PWM_Duty);
        State_Start_Time = 0;
      }
    }

    if (last_button_state != Current_Button_State)
    {
      last_button_state = Current_Button_State;
      if (Current_Button_State == BUTTON_STATE_ON)
      {
        __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_4, Current_PWM_Duty);
      }
      else if (Current_Button_State == BUTTON_STATE_STANDBY)
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

    // Paint_DrawNum(27, 5, Dimming, &Font12, 0, 0xFF, 0x00);

    // Paint_DrawString_EN(5, 24, "Temp:   'C", &Font12, 0x00, 0xFF);
    // Paint_DrawNum(42, 24, Direction, &Font12, 0, 0xFF, 0x00);

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

  /* Infinite loop */
  for (;;)
  {
    // Setting_Button 핀 상태 읽기 (PULLUP 설정이므로 평상시 HIGH, 눌리면 LOW)
    GPIO_PinState button_raw_state = HAL_GPIO_ReadPin(Setting_Button_GPIO_Port, Setting_Button_Pin);
    current_time = xTaskGetTickCount();

    // 디바운싱 처리 - 3번 연속 같은 상태일 때만 인정
    if (button_raw_state == button_stable_state)
    {
      button_stable_count++;
      if (button_stable_count >= 3)
      {
        button_current_state = button_stable_state;
        button_stable_count = 3; // 오버플로우 방지
      }
    }
    else
    {
      button_stable_state = button_raw_state;
      button_stable_count = 1;
    }

    // 버튼 눌림 감지 (HIGH에서 LOW로 전환) - 안정화된 상태에서만 처리
    if (button_prev_state == GPIO_PIN_SET && button_current_state == GPIO_PIN_RESET && button_stable_count >= 3)
    {
      Button_Press_Start_Time = current_time;
      Button_Pressed = 1;
      Button_Released = 0;
    }

    // 버튼 릴리즈 감지 (LOW에서 HIGH로 전환) - 안정화된 상태에서만 처리
    if (button_prev_state == GPIO_PIN_RESET && button_current_state == GPIO_PIN_SET && button_stable_count >= 3)
    {
      button_press_duration = current_time - Button_Press_Start_Time;
      Button_Pressed = 0;
      Button_Released = 1;

      // 유효한 버튼 클릭인지 확인 (최소 20ms 이상)
      if (button_press_duration >= (20 / portTICK_PERIOD_MS))
      {

        // 버튼 상태에 따른 동작 처리
        switch (Current_Button_State)
        {
        case BUTTON_STATE_STANDBY:
          // STANDBY에서 1초 이하 클릭 -> ON 상태로 전환
          if (button_press_duration < (1000 / portTICK_PERIOD_MS))
          {
            Current_Button_State = BUTTON_STATE_ON;
          }
          break;

        case BUTTON_STATE_ON:
          // ON에서 1초 이하 클릭 -> STANDBY 상태로 전환
          if (button_press_duration < (1000 / portTICK_PERIOD_MS))
          {
            Current_Button_State = BUTTON_STATE_STANDBY;
          }
          break;

        case BUTTON_STATE_TIMER_SET:
          // TIMER_SET에서 1초 이하 클릭 -> 타이머 값 증가
          if (button_press_duration < (1000 / portTICK_PERIOD_MS))
          {
            Timer_Value++;
            if (Timer_Value > 10)
            {
              Timer_Value = 5; // 10을 넘으면 1부터 다시 시작
            }
            // TIMER_SET에서 활동이 있었으므로 비활성화 타이머 리셋
            Timer_Set_Inactive_Start_Time = current_time;
          }
          break;

        case BUTTON_STATE_TIMER_UP:
          // TIMER_UP에서 클릭 -> STANDBY로 복귀
          if (button_press_duration < (1000 / portTICK_PERIOD_MS))
          {
            Current_Button_State = BUTTON_STATE_STANDBY;
          }
          break;

        default:
          break;
        }
      }
    }

    // 버튼이 계속 눌려있는 상태에서 1.5초 이상 지나면 처리
    if (Button_Pressed && (current_time - Button_Press_Start_Time) >= (1500 / portTICK_PERIOD_MS))
    {
      if (Current_Button_State == BUTTON_STATE_STANDBY || Current_Button_State == BUTTON_STATE_ON)
      {
        Current_Button_State = BUTTON_STATE_TIMER_SET;
        Timer_Set_Inactive_Start_Time = current_time; // TIMER_SET 진입시 비활성화 타이머 시작
        Button_Pressed = 0;                           // 1.5초 이벤트 처리 후 중복 방지
      }
      else if (Current_Button_State == BUTTON_STATE_TIMER_SET)
      {
        // TIMER_SET에서 1.5초 이상 누르면 STANDBY로 복귀
        Current_Button_State = BUTTON_STATE_STANDBY;
        Button_Pressed = 0; // 이벤트 처리 후 중복 방지
      }
    }

    // TIMER_SET 상태에서 5초간 비활성화시 STANDBY로 복귀
    if (Current_Button_State == BUTTON_STATE_TIMER_SET)
    {
      if ((current_time - Timer_Set_Inactive_Start_Time) >= (5000 / portTICK_PERIOD_MS))
      {
        Current_Button_State = BUTTON_STATE_STANDBY;
      }
    }

    // 이전 상태 업데이트 (안정화된 상태에서만)
    if (button_stable_count >= 3)
    {
      button_prev_state = button_current_state;
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

  /* USER CODE END Callback01 */
}

// 스택 오버플로우 후크 함수
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
  /* 스택 오버플로우 발생시 System LED를 빠르게 깜빡이며 에러 표시 */
  while (1)
  {
    HAL_GPIO_TogglePin(System_LED_GPIO_Port, System_LED_Pin);
    HAL_Delay(100);
  }
}

/* USER CODE END Application */
