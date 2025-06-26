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
#include "fonts.h"
#include <stdio.h>
#include <string.h>

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

// UI 관련 변수들
static uint32_t ui_blink_counter = 0; // 깜빡임 효과용 카운터

// 애니메이션 매니저
static AnimationManager_t anim_manager = {0};

// 단순화된 애니메이션 함수들
void Animation_Init(void);
void Animation_Update(void);
uint8_t Animation_Start(Animation_Type_t type, uint8_t max_val);
uint8_t Animation_GetValue(uint8_t index);

// 애니메이션 초기화
void Animation_Init(void)
{
  memset(&anim_manager, 0, sizeof(AnimationManager_t));
}

// 애니메이션 시작 (단순화)
uint8_t Animation_Start(Animation_Type_t type, uint8_t max_val)
{
  // 빈 슬롯 찾기
  for (uint8_t i = 0; i < 3; i++)
  {
    if (anim_manager.animations[i].state == ANIM_STATE_IDLE)
    {
      Animation_t *anim = &anim_manager.animations[i];
      anim->type = type;
      anim->state = ANIM_STATE_RUNNING;
      anim->counter = 0;
      anim->max_value = max_val;
      anim->current_value = 0;
      return i;
    }
  }
  return 255; // 슬롯 없음
}

// 간단한 애니메이션 업데이트
void Animation_Update(void)
{
  anim_manager.frame_counter++;

  for (uint8_t i = 0; i < 3; i++)
  {
    Animation_t *anim = &anim_manager.animations[i];
    if (anim->state != ANIM_STATE_RUNNING)
      continue;

    anim->counter++;

    switch (anim->type)
    {
    case ANIM_TYPE_BLINK:
      anim->current_value = ((anim->counter / 10) % 2) ? anim->max_value : 0;
      break;

    case ANIM_TYPE_BOUNCE:
    {
      uint8_t cycle = anim->counter % 40; // 2초 주기
      if (cycle < 20)
        anim->current_value = (cycle * anim->max_value) / 20;
      else
        anim->current_value = ((40 - cycle) * anim->max_value) / 20;
    }
    break;

    default:
      break;
    }
  }
}

// 애니메이션 값 가져오기
uint8_t Animation_GetValue(uint8_t index)
{
  if (index >= 3)
    return 0;
  return anim_manager.animations[index].current_value;
}

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

  char display_text[64];

  // 애니메이션 시스템 초기화
  Animation_Init();

  // 애니메이션 인덱스들
  static uint8_t setup_blink_anim = 255;

  // Paint 시스템 초기화
  Paint_NewImage(BlackImage, 128, 64, 180, WHITE);
  Paint_SelectImage(BlackImage);
  Paint_SetRotate(ROTATE_180);
  Paint_SetMirroring(MIRROR_NONE);

  /* Infinite loop */
  for (;;)
  {
    // 애니메이션 업데이트 (20fps)
    Animation_Update();

    // 화면 초기화
    Paint_Clear(BLACK);

    // UI 카운터 증가 (깜빡임 효과용)
    ui_blink_counter++;

    // === 128x64 OLED 가시성 최적화 UI ===

    // 상단 라인 (0-15px): LED 연결 상태만 표시
    // L1 상태 - 연결 상태에 따른 애니메이션 효과
    Paint_DrawString_EN(3, 2, "L1:", &Font12, WHITE, BLACK);
    if (Adc_State.LED1_State != LED_STATE_FLOATING)
    {
      // 연결됨 - 부드러운 깜빡임 효과
      uint8_t brightness = 255;
      if ((ui_blink_counter / 10) % 2 == 0)
        brightness = 180;
      DRAW_ICON(23, 0, ICON_CONNECTED, brightness > 200 ? WHITE : GRAY, BLACK);
    }
    else
    {
      DRAW_ICON(23, 0, ICON_DISCONNECTED, WHITE, BLACK);
    }

    // L2 상태 - 연결 상태에 따른 애니메이션 효과
    Paint_DrawString_EN(43, 2, "L2:", &Font12, WHITE, BLACK);
    if (Adc_State.LED2_State != LED_STATE_FLOATING)
    {
      // 연결됨 - 부드러운 깜빡임 효과
      uint8_t brightness = 255;
      if ((ui_blink_counter / 10) % 2 == 0)
        brightness = 180;
      DRAW_ICON(63, 0, ICON_CONNECTED, brightness > 200 ? WHITE : GRAY, BLACK);
    }
    else
    {
      DRAW_ICON(63, 0, ICON_DISCONNECTED, WHITE, BLACK);
    }

    // 배터리 상태 - 아이콘 애니메이션
    uint8_t bat_percent = (uint8_t)((float)(Adc_State.VBat_ADC_Value - 700) / 2200 * 100);

    if (bat_percent > 100)
    {
      bat_percent = 0;
    }

    // 배터리 레벨에 따른 아이콘 선택 (7단계)
    uint8_t battery_icon;
    if (bat_percent > 85)
    {
      battery_icon = ICON_BATTERY_HIGH; // 80% 이상: 높음
    }
    else if (bat_percent > 70)
    {
      battery_icon = ICON_BATTERY_MIDHIGH; // 65-80%: 중상
    }
    else if (bat_percent > 55)
    {
      battery_icon = ICON_BATTERY_MID; // 50-65%: 중간
    }
    else if (bat_percent > 40)
    {
      battery_icon = ICON_BATTERY_MIDLOW; // 35-50%: 중하
    }
    else if (bat_percent > 25)
    {
      battery_icon = ICON_BATTERY_LOW; // 20-35%: 낮음
    }
    else if (bat_percent > 10)
    {
      battery_icon = ICON_BATTERY_VERY_LOW; // 10-20%: 매우 낮음
    }
    else
    {
      battery_icon = ICON_BATTERY_EMPTY; // 10% 이하: 빈 배터리
      // 배터리 부족시 깜빡임
      if ((ui_blink_counter / 15) % 2 == 0)
      {
        battery_icon = ICON_SPACE;
      }
    }

    DRAW_ICON(108, 1, battery_icon, WHITE, BLACK);

    // 구분선
    Paint_DrawLine(0, 15, 127, 15, WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);

    // 하단 3줄 (16-63px): 큰 타이머 표시
    if (Button_State.is_Start_Timer)
    {
      DRAW_ICON(2, 16, ICON_PLAY, WHITE, BLACK);
      sprintf(display_text, "%d min", Button_State.Timer_Value);
      Paint_DrawString_EN(Button_State.Timer_Value < 10 ? 85 : 80, 16, display_text, &Font12, WHITE, BLACK);

      sprintf(display_text, "%02d:%02d", Button_State.minute_count, Button_State.second_count);
      Paint_DrawString_EN(22, 30, display_text, &Font24, WHITE, BLACK);
    }
    else if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
    {
      DRAW_ICON(2, 16, ICON_TIMER_SET, WHITE, BLACK);

      // 타이머 설정 모드 - 깜빡이는 애니메이션
      sprintf(display_text, "SETUP");
      Paint_DrawString_EN(45, 20, display_text, &Font12, WHITE, BLACK);

      // 부드러운 깜빡이는 설정값
      if (setup_blink_anim == 255)
      {
        setup_blink_anim = Animation_Start(ANIM_TYPE_BLINK, 255);
      }

      if (Animation_GetValue(setup_blink_anim) > 128)
      {
        sprintf(display_text, "%d min", Button_State.Timer_Value);
        Paint_DrawString_EN(Button_State.Timer_Value < 10 ? 45 : 40, 35, display_text, &Font12, WHITE, BLACK);
      }

      Paint_DrawString_EN(25, 50, "PRESS +2min", &Font12, WHITE, BLACK);
    }
    else
    {
      // 애니메이션 리셋
      setup_blink_anim = 255;

      if (!Button_State.is_start_to_cooling)
      {
        DRAW_ICON(2, 16, ICON_STANDBY, WHITE, BLACK);
        // 대기 모드
        sprintf(display_text, "READY");
        Paint_DrawString_EN(45, 20, display_text, &Font12, WHITE, BLACK);

        sprintf(display_text, "%d min", Button_State.Timer_Value);
        Paint_DrawString_EN(Button_State.Timer_Value < 10 ? 45 : 40, 35, display_text, &Font12, WHITE, BLACK);

        Paint_DrawString_EN(25, 50, "PRESS START", &Font12, WHITE, BLACK);
      }
      else
      {
        DRAW_ICON(2, 16, ICON_STOP, WHITE, BLACK);

        // 쿨링 모드 - 깜빡이는 텍스트
        if ((ui_blink_counter / 10) % 2 == 0)
        {
          sprintf(display_text, "COOLING");
          Paint_DrawString_EN(38, 20, display_text, &Font12, WHITE, BLACK);
        }

        sprintf(display_text, "%d sec", Button_State.cooling_second);
        Paint_DrawString_EN(Button_State.cooling_second < 10 ? 45 : 40, 35, display_text, &Font12, WHITE, BLACK);

        Paint_DrawString_EN(25, 50, "PLEASE WAIT", &Font12, WHITE, BLACK);

        // 쿨링 진행률 표시
        float cooling_progress = 1.0f - ((float)Button_State.cooling_second / 60.0f);
        uint8_t cooling_width = (uint8_t)(cooling_progress * 100);
        Paint_DrawRectangle(14, 55, 14 + cooling_width, 57, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
        Paint_DrawRectangle(13, 54, 115, 58, WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
      }
    }

    // 화면 테두리
    Paint_DrawRectangle(1, 1, 128, 64, WHITE, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);

    // 디스플레이 업데이트
    OLED_1in3_C_Display(BlackImage);

    // 20fps: 50ms 주기로 업데이트
    vTaskDelayUntil(&lastWakeTime, 50 * portTICK_PERIOD_MS);
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
              osTimerStart(MainTimerHandle, 1001);
              Button_State.minute_count = Button_State.Timer_Value;
              Button_State.second_count = 0;
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
    Button_State.second_count--;
    if (Button_State.second_count < 0)
    {
      Button_State.minute_count--;
      Button_State.second_count = 59;

      // 다운카운트: 설정된 시간에 도달하면 타이머 정지
      if (Button_State.minute_count < 0)
      {
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

/* USER CODE END Application */
