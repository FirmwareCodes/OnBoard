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
#include "flash_storage.h"

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
    .stack_size = 512 * 4,  // UART 처리를 위해 더 큰 스택 할당
    .priority = (osPriority_t)osPriorityHigh1,  // 높은 우선순위로 설정
};
/* Definitions for UartMutex */
osMutexId_t UartMutexHandle;
const osMutexAttr_t UartMutex_attributes = {
    .name = "UartMutex",
    .attr_bits = osMutexPrioInherit,  // 우선순위 상속으로 priority inversion 방지
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
};

// UART 태스크용 전역 변수
typedef struct {
    uint8_t rx_buffer[256];           // 수신 버퍼
    uint8_t tx_buffer[1200];          // 송신 버퍼 (화면 데이터용)
    uint8_t cmd_buffer[128];          // 명령어 버퍼
    uint16_t rx_index;                // 수신 인덱스
    uint16_t cmd_index;               // 명령어 인덱스
    uint8_t command_ready;            // 명령어 준비 플래그
    uint8_t monitoring_enabled;       // 모니터링 활성화 플래그
    uint8_t auto_screen_update;       // 자동 화면 업데이트 플래그
    uint32_t last_screen_update;      // 마지막 화면 업데이트 시간
    uint32_t last_status_update;      // 마지막 상태 업데이트 시간
} UART_State_t;

UART_State_t UART_State = {
    .rx_index = 0,
    .cmd_index = 0,
    .command_ready = 0,
    .monitoring_enabled = 0,
    .auto_screen_update = 0,
    .last_screen_update = 0,
    .last_status_update = 0
};

/* USER CODE END Variables */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN FunctionPrototypes */
void StartOneSecondTask(void *argument);
void StartAdcTask(void *argument);
void StartDisplayTask(void *argument);
void StartButtonTask(void *argument);
void StartUartTask(void *argument);
void Callback01(void *argument);

// UART 태스크 관련 함수 프로토타입
void UART_ProcessCommand(void);
void UART_SendScreenData(void);
void UART_SendStatusData(void);
void UART_SendResponse(const char* response);
void UART_ProcessTimerSet(const char* time_str);
void UART_ProcessTimerStart(void);
void UART_ProcessTimerStop(void);
void UART_ProcessReset(void);

/* USER CODE END FunctionPrototypes */

/* Private application code --------------------------------------------------*/
/* USER CODE BEGIN Application */

/**
 * @brief  플래시에서 타이머 값을 불러와 Button_State에 설정합니다
 * @retval None
 */
void Timer_LoadFromFlash(void)
{
    uint32_t timer_value = 0;
    HAL_StatusTypeDef status = Flash_ReadTimerValue(&timer_value);
    
    if (status == HAL_OK)
    {
        // 유효한 범위 확인 (1초 ~ 255초)
        if (timer_value >= 1 && timer_value <= 255)
        {
            Button_State.Timer_Value = (uint8_t)timer_value;
        }
        else
        {
            // 범위를 벗어나는 경우 기본값 설정
            Button_State.Timer_Value = 10;
        }
    }
    else
    {
        // 플래시에서 읽기 실패 시 기본값 설정
        Button_State.Timer_Value = 10;
    }
}

/**
 * @brief  타이머 값을 플래시에 저장합니다
 * @param  timer_value: 저장할 타이머 값 (초 단위)
 * @retval None
 */
void Timer_SaveToFlash(uint32_t timer_value)
{
    HAL_StatusTypeDef status = Flash_WriteTimerValue(timer_value);
    
    if (status != HAL_OK)
    {
    
    }
}

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
  Timer_LoadFromFlash();
  
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
  LED_State_t prev_LED1_State = LED_STATE_MIDDLE;
  LED_State_t prev_LED2_State = LED_STATE_MIDDLE;
  uint32_t state_timer = 0;
  uint16_t target_duty = 0;
  uint8_t last_button_state = 0;

  // VBat 필터링 관련 변수들
  uint32_t vbat_sum = 0;
  uint8_t vbat_samples = 0;

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
      osDelay(2); // 2ms 간격으로 샘플링
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
      if (abs(diff) > 30)
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
      .init_bat_animation = false,
      .init_battery_percent = 0,
      .battery_percent = 0,
      .timer_minutes = 0,
      .timer_seconds = 0,
      .timer_status = TIMER_STATUS_STANDBY,
      .l1_connected = LED_DISCONNECTED,
      .l2_connected = LED_DISCONNECTED,
      .cooling_seconds = 0,
      .progress_update_counter = 0,
      .blink_counter = 0,
      .force_full_update = 1,    // 첫 번째는 전체 업데이트
      .timer_indicator_blink = 0 // 타이머 표시기 초기값
  };

  /* Infinite loop */
  for (;;)
  {
    // 카운터 증가
    current_status.progress_update_counter++;
    current_status.blink_counter++;

    // 배터리 전압을 퍼센티지로 변환 (ADC 값 기반)
    uint8_t battery_percent = 0;
    static uint8_t prev_battery_display = 255; // 이전 배터리 표시값 (필터링용)

    if (Adc_State.VBat_ADC_Value > 500)
    {                                                                                     // 3.0V 이상이면 배터리 상태 계산
      float battery_float = ((float)(Adc_State.VBat_ADC_Value - 500) / 2200.0f * 100.0f); // 3.0V~4.2V 범위를 0~100%로 매핑
      battery_percent = (uint8_t)(battery_float + 0.5f);                                  // 반올림 처리
    }

    if (battery_percent > 100 || Adc_State.VBat_ADC_Value > 2650)
    {
      battery_percent = 100;
      prev_battery_display = 100;
    }
    // 배터리 표시 안정화 (2% 이상 차이가 날 때만 업데이트)
    else if (prev_battery_display == 255) // 첫 번째 값
    {
      prev_battery_display = battery_percent;
    }
    else if (abs((int)battery_percent - (int)prev_battery_display) >= 2)
    {
      // 2% 이상 차이가 나면 점진적으로 변경
      if (battery_percent > prev_battery_display)
      {
        prev_battery_display += 1;
      }
      else if (battery_percent < prev_battery_display)
      {
        prev_battery_display -= 1;
      }
    }

    // 최종 표시값 사용
    battery_percent = prev_battery_display;

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

    // 타이머 실행 표시기 제어 (0.5초마다 토글)
    if (timer_status == TIMER_STATUS_RUNNING)
    {
      // 타이머 실행 중: 0.5초마다 토글 
      current_status.timer_indicator_blink = (current_status.blink_counter / 10) % 2;
    }
    else
    {
      // 타이머 정지: 표시기 숨김
      current_status.timer_indicator_blink = 0;
    }

    // 타이머 시간 설정 (다운카운트 지원)
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
    current_status.battery_percent = battery_percent;
    current_status.timer_minutes = timer_minutes;
    current_status.timer_seconds = timer_seconds;
    current_status.timer_status = timer_status;
    current_status.l1_connected = l1_connected;
    current_status.l2_connected = l2_connected;
    current_status.cooling_seconds = (uint8_t)Button_State.cooling_second;

    UI_DrawFullScreenOptimized(&current_status);

    // UI_UPDATE_INTERVAL_MS 주기로 업데이트, 초기 애니메이션 때에는 10ms 주기로 업데이트
    vTaskDelayUntil(&lastWakeTime, (current_status.init_bat_animation ? UI_UPDATE_INTERVAL_MS * portTICK_PERIOD_MS : 10 * portTICK_PERIOD_MS));
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
            HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_SET);
            Button_State.is_Start_Timer = !Button_State.is_Start_Timer;

            if (Button_State.is_Start_Timer)
            {
              osTimerStart(MainTimerHandle, 1000); // 1000ms = 1초 주기
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
            else if(!Button_State.is_Start_Timer && !Button_State.is_start_to_cooling)
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
            
            // 타이머 값이 변경되었으므로 플래시에 저장
            Timer_SaveToFlash((uint32_t)Button_State.Timer_Value);
            
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
        Timer_SaveToFlash((uint32_t)Button_State.Timer_Value);
      }
    }

    // TIMER_SET 상태에서 5초간 비활성화시 STANDBY로 복귀
    if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET && is_Button_Released)
    {
      if ((Button_State.Button_Current_Time - Button_State.Timer_Set_Start_Time) >= (5000 / portTICK_PERIOD_MS))
      {
        Button_State.Current_Button_State = BUTTON_STATE_STANDBY;
        
        // 5초 비활성화로 TIMER_SET 모드를 나갈 때도 플래시에 저장
        Timer_SaveToFlash((uint32_t)Button_State.Timer_Value);
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

  // 뮤텍스가 제대로 생성될 때까지 대기
  while (UartMutexHandle == NULL) {
    osDelay(10);
  }

  // UART 초기화 안정화 딜레이
  osDelay(100);

  // UART 상태 초기화
  UART_State.rx_index = 0;
  UART_State.cmd_index = 0;
  UART_State.command_ready = 0;
  UART_State.monitoring_enabled = 0;
  UART_State.auto_screen_update = 0;

  // UART 초기화 메시지 (뮤텍스 보호)
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 1000);
  if (mutex_status == osOK) {
    const char* welcome_msg = "OnBoard LED Timer Ready\n";
    HAL_UART_Transmit(&huart1, (uint8_t*)welcome_msg, strlen(welcome_msg), 1000);
    osMutexRelease(UartMutexHandle);
  }

  // UART 인터럽트 수신 시작
  HAL_UART_Receive_IT(&huart1, &UART_State.rx_buffer[UART_State.rx_index], 1);

  /* Infinite loop */
  for (;;)
  {

    uint32_t current_time = HAL_GetTick();

    // 1. 수신된 명령어 처리
    if (UART_State.command_ready)
    {
      UART_ProcessCommand();
      UART_State.command_ready = 0;
    }

    // 2. 자동 모니터링 처리
    if (UART_State.monitoring_enabled)
    {
      // 100ms마다 화면 데이터 전송
      if (UART_State.auto_screen_update && 
          (current_time - UART_State.last_screen_update >= 100))
      {
        UART_SendScreenData();
        UART_State.last_screen_update = current_time;
      }

      // 자동 모니터링 시에는 상태 정보 전송 비활성화 (충돌 방지)
      // 상태 정보는 별도 GET_STATUS 명령어로만 요청 가능
      /*
      if (current_time - UART_State.last_status_update >= 1000)
      {
        UART_SendStatusData();
        UART_State.last_status_update = current_time;
      }
      */
    }

    // 20ms 주기로 실행
    vTaskDelayUntil(&lastWakeTime, 20 * portTICK_PERIOD_MS);
  }
  /* USER CODE END StartUartTask */
}

/**
 * @brief UART 명령어 처리 함수
 */
void UART_ProcessCommand(void)
{
  // 뮤텍스 획득 (최대 100ms 대기)
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 100);
  if (mutex_status != osOK) {
    // 뮤텍스 획득 실패 - 다음 사이클에서 다시 시도
    return;
  }

  char* cmd_str = (char*)UART_State.cmd_buffer;
  
  // 개행 문자 제거
  char* newline = strchr(cmd_str, '\n');
  if (newline) *newline = '\0';
  newline = strchr(cmd_str, '\r');
  if (newline) *newline = '\0';

  // 명령어 처리
  if (strcmp(cmd_str, "GET_SCREEN") == 0) {
    UART_SendScreenData();
  }
  else if (strcmp(cmd_str, "GET_STATUS") == 0) {
    UART_SendStatusData();
  }
  else if (strcmp(cmd_str, "GET_SIMPLE") == 0) {
    // 간단한 화면 데이터 테스트 (디버깅용) - 실제 작은 패턴 전송
    const char* header = "\nSCREEN_START\nSIZE:128x64\n";
    HAL_UART_Transmit(&huart1, (uint8_t*)header, strlen(header), 1000);
    
    // 간단한 테스트 패턴 생성 (64바이트로 작게)
    uint8_t test_pattern[64];
    for (int i = 0; i < 64; i++) {
      if (i % 8 < 4) {
        test_pattern[i] = 0xFF;  // 흰색 패턴
      } else {
        test_pattern[i] = 0x00;  // 검은색 패턴
      }
    }
    
    // 테스트 패턴 전송
    HAL_UART_Transmit(&huart1, test_pattern, 64, 1000);
    
    // 나머지는 0으로 채움 (1024 - 64 = 960바이트)
    uint8_t zero_buffer[32];
    memset(zero_buffer, 0, 32);
    for (int i = 0; i < 30; i++) {  // 30 * 32 = 960바이트
      HAL_UART_Transmit(&huart1, zero_buffer, 32, 1000);
    }
    
    const char* footer = "\nSCREEN_END\n\n";
    HAL_UART_Transmit(&huart1, (uint8_t*)footer, strlen(footer), 1000);
  }
  else if (strcmp(cmd_str, "START_MONITOR") == 0) {
    UART_State.monitoring_enabled = 1;
    UART_State.auto_screen_update = 1;
    UART_SendResponse("OK:Monitoring started\n");
  }
  else if (strcmp(cmd_str, "STOP_MONITOR") == 0) {
    UART_State.monitoring_enabled = 0;
    UART_State.auto_screen_update = 0;
    UART_SendResponse("OK:Monitoring stopped\n");
  }
  else if (strncmp(cmd_str, "SET_TIMER:", 10) == 0) {
    UART_ProcessTimerSet(cmd_str + 10);
  }
  else if (strcmp(cmd_str, "START_TIMER") == 0) {
    UART_ProcessTimerStart();
  }
  else if (strcmp(cmd_str, "STOP_TIMER") == 0) {
    UART_ProcessTimerStop();
  }
  else if (strcmp(cmd_str, "RESET") == 0) {
    UART_ProcessReset();
  }
  else if (strcmp(cmd_str, "PING") == 0) {
    UART_SendResponse("PONG\n");
  }
  else if (strcmp(cmd_str, "TEST") == 0) {
    UART_SendResponse("TEST:OK\n");
  }
  else {
    UART_SendResponse("ERROR:Unknown command\n");
  }

  // 명령어 버퍼 초기화
  memset(UART_State.cmd_buffer, 0, sizeof(UART_State.cmd_buffer));
  UART_State.cmd_index = 0;

  // 뮤텍스 해제
  osMutexRelease(UartMutexHandle);
}

/**
 * @brief 화면 데이터 전송
 */
void UART_SendScreenData(void)
{
  // 뮤텍스 획득 (최대 200ms 대기 - 화면 데이터 전송은 시간이 걸릴 수 있음)
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 200);
  if (mutex_status != osOK) {
    // 뮤텍스 획득 실패 - 전송 포기
    return;
  }

  if (Paint.Image == NULL) {
    // 뮤텍스를 이미 획득한 상태이므로 직접 전송
    const char* error_msg = "ERROR:No screen data available\n";
    HAL_UART_Transmit(&huart1, (uint8_t*)error_msg, strlen(error_msg), 1000);
    osMutexRelease(UartMutexHandle);
    return;
  }

  // 화면 데이터 시작 헤더 전송 (개행 문자 추가하여 명확히 구분)
  const char* header = "\nSCREEN_START\nSIZE:128x64\n";
  HAL_StatusTypeDef status = HAL_UART_Transmit(&huart1, (uint8_t*)header, strlen(header), 1000);
  
  if (status != HAL_OK) {
    // 헤더 전송 실패 시 중단
    osMutexRelease(UartMutexHandle);
    return;
  }

  // 헤더와 데이터 사이에 딜레이
  osDelay(10);

  // OLED 화면 데이터 전송 (1024 bytes를 분할하여 전송)
  uint16_t image_size = (OLED_1in3_C_WIDTH * OLED_1in3_C_HEIGHT) / 8; // 1024 bytes (128*64/8)
  uint16_t chunk_size = 32; // 32바이트씩 분할 전송 (더 작게)
  uint16_t sent = 0;
  
  while (sent < image_size) {
    uint16_t remaining = image_size - sent;
    uint16_t current_chunk = (remaining > chunk_size) ? chunk_size : remaining;
    
    status = HAL_UART_Transmit(&huart1, &Paint.Image[sent], current_chunk, 1000);
    if (status != HAL_OK) {
      // 전송 실패 시 중단
      break;
    }
    
    sent += current_chunk;
    
    // 각 청크 사이에 작은 딜레이
    if (sent < image_size) {
      osDelay(1);
    }
  }

  // 데이터와 푸터 사이에 딜레이
  osDelay(10);

  // 화면 데이터 종료 헤더 전송 (개행 문자 추가)
  const char* footer = "\nSCREEN_END\n\n";
  HAL_UART_Transmit(&huart1, (uint8_t*)footer, strlen(footer), 1000);

  // 뮤텍스 해제
  osMutexRelease(UartMutexHandle);
}

/**
 * @brief 상태 정보 전송
 */
void UART_SendStatusData(void)
{
  // 뮤텍스 획득 (최대 100ms 대기)
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 100);
  if (mutex_status != osOK) {
    // 뮤텍스 획득 실패 - 전송 포기
    return;
  }

  char status_buffer[256];

  // 배터리 퍼센티지 계산
  uint8_t battery_percent = 0;
  if (Adc_State.VBat_ADC_Value > 500) {
    float battery_float = ((float)(Adc_State.VBat_ADC_Value - 500) / 2200.0f * 100.0f);
    battery_percent = (uint8_t)(battery_float + 0.5f);
  }
  if (battery_percent > 100 || Adc_State.VBat_ADC_Value > 2650) {
    battery_percent = 100;
  }

  // 타이머 상태 문자열
  const char* status_str;
  if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET) {
    status_str = "SETTING";
  } else if (Button_State.is_start_to_cooling) {
    status_str = "COOLING";
  } else if (Button_State.is_Start_Timer) {
    status_str = "RUNNING";
  } else {
    status_str = "STANDBY";
  }

  // LED 연결 상태
  uint8_t l1_connected = (Adc_State.LED1_State != LED_STATE_MIDDLE) ? 1 : 0;
  uint8_t l2_connected = (Adc_State.LED2_State != LED_STATE_MIDDLE) ? 1 : 0;

  // 타이머 시간 계산
  uint8_t timer_minutes, timer_seconds;
  if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET) {
    timer_minutes = Button_State.Timer_Value;
    timer_seconds = 0;
  } else if (Button_State.is_start_to_cooling) {
    timer_minutes = Button_State.cooling_second / 60;
    timer_seconds = Button_State.cooling_second % 60;
  } else {
    timer_minutes = Button_State.minute_count;
    timer_seconds = Button_State.second_count;
  }

  // 상태 정보 문자열 생성
  snprintf(status_buffer, sizeof(status_buffer),
    "STATUS:BAT:%d%%,TIMER:%02d:%02d,STATUS:%s,L1:%d,L2:%d\n",
    battery_percent, timer_minutes, timer_seconds, status_str, l1_connected, l2_connected);

  HAL_UART_Transmit(&huart1, (uint8_t*)status_buffer, strlen(status_buffer), 1000);

  // 뮤텍스 해제
  osMutexRelease(UartMutexHandle);
}

/**
 * @brief 응답 메시지 전송
 */
void UART_SendResponse(const char* response)
{
  // 뮤텍스 획득 시도 (타임아웃 없이 즉시 확인)
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 0);
  
  if (mutex_status == osOK) {
    // 뮤텍스를 성공적으로 획득한 경우
    HAL_UART_Transmit(&huart1, (uint8_t*)response, strlen(response), 1000);
    osMutexRelease(UartMutexHandle);
  } else {
    // 뮤텍스가 이미 사용 중인 경우, 직접 전송 (이미 다른 곳에서 뮤텍스를 획득했다고 가정)
    HAL_UART_Transmit(&huart1, (uint8_t*)response, strlen(response), 1000);
  }
}

/**
 * @brief 타이머 설정 처리
 */
void UART_ProcessTimerSet(const char* time_str)
{
  int minutes, seconds;
  if (sscanf(time_str, "%d:%d", &minutes, &seconds) == 2) {
    if (minutes >= 0 && minutes <= 99 && seconds >= 0 && seconds <= 59) {
      // 실제 타이머 값 설정 (초 단위로 변환)
      Button_State.Timer_Value = minutes; // 분 단위로 저장
      UART_SendResponse("OK:Timer set\n");
    } else {
      UART_SendResponse("ERROR:Invalid time range\n");
    }
  } else {
    UART_SendResponse("ERROR:Invalid time format\n");
  }
}

/**
 * @brief 타이머 시작 처리
 */
void UART_ProcessTimerStart(void)
{
  if (!Button_State.is_Start_Timer && !Button_State.is_start_to_cooling) {
    Button_State.is_Start_Timer = true;
    Button_State.minute_count = Button_State.Timer_Value;
    Button_State.second_count = 0;
    
    // 메인 타이머 시작
    osTimerStart(MainTimerHandle, 1000);
    
    // 팬 ON
    HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_SET);
    
    UART_SendResponse("OK:Timer started\n");
  } else {
    UART_SendResponse("ERROR:Timer already running\n");
  }
}

/**
 * @brief 타이머 정지 처리
 */
void UART_ProcessTimerStop(void)
{
  if (Button_State.is_Start_Timer) {
    Button_State.is_Start_Timer = false;
    
    // 쿨링 시작 조건 확인
    if (Button_State.Timer_Value - Button_State.minute_count != 0 && Button_State.second_count <= 50) {
      Button_State.is_start_to_cooling = true;
      int8_t cooling_second = (Button_State.Timer_Value - Button_State.minute_count) * 10;
      if (cooling_second > 60) cooling_second = 60;
      Button_State.cooling_second = cooling_second;
      UART_SendResponse("OK:Timer stopped, cooling started\n");
    } else {
      // 완전 정지
      osTimerStop(MainTimerHandle);
      HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
      UART_SendResponse("OK:Timer stopped\n");
    }
  } else {
    UART_SendResponse("ERROR:Timer not running\n");
  }
}

/**
 * @brief 시스템 리셋 처리
 */
void UART_ProcessReset(void)
{
  Button_State.is_Start_Timer = false;
  Button_State.is_start_to_cooling = false;
  Button_State.Current_Button_State = BUTTON_STATE_STANDBY;
  
  // 타이머 정지
  osTimerStop(MainTimerHandle);
  
  // 팬 OFF
  HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
  
  // 모니터링 리셋
  UART_State.monitoring_enabled = 0;
  UART_State.auto_screen_update = 0;
  
  UART_SendResponse("OK:System reset\n");
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

  /* USER CODE END Callback01 */
}

/**
 * @brief UART 수신 완료 콜백 (인터럽트)
 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART1) {
    uint8_t received_char = UART_State.rx_buffer[UART_State.rx_index];
    
    // 명령어 버퍼에 문자 저장 (인터럽트에서는 뮤텍스 없이 처리)
    if (received_char == '\n' || received_char == '\r') {
      // 명령어 완료
      if (UART_State.cmd_index > 0) {
        UART_State.cmd_buffer[UART_State.cmd_index] = '\0';
        UART_State.command_ready = 1;
      }
    } else {
      // 문자 추가
      if (UART_State.cmd_index < sizeof(UART_State.cmd_buffer) - 1) {
        UART_State.cmd_buffer[UART_State.cmd_index] = received_char;
        UART_State.cmd_index++;
      } else {
        // 버퍼 오버플로우 - 명령어 리셋 (오류 메시지는 보내지 않음)
        UART_State.cmd_index = 0;
      }
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
