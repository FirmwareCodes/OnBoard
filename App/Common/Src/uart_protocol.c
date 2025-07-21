#include "uart_protocol.h"
#include "def.h"
#include "battery_monitor.h"

extern UART_State_t UART_State;
extern osTimerId_t MainTimerHandle;
extern Button_t Button_State;
extern Adc_t Adc_State;
extern Battery_Monitor_t Battery_Monitor;
extern UART_HandleTypeDef huart1;
extern osMutexId_t UartMutexHandle;

/**
 * @brief UART 명령어 처리 함수 (최적화 버전)
 */
void UART_ProcessCommand(void)
{
  // 명령어 문자열 최적화 (직접 참조로 성능 향상)
  char *cmd_str = (char *)UART_State.cmd_buffer;

  // 빠른 길이 체크 (빈 명령어 즉시 거부)
  if (UART_State.cmd_index == 0)
  {
    UART_State.command_ready = 0;
    return;
  }

  // NULL 종료 보장
  UART_State.cmd_buffer[UART_State.cmd_index] = '\0';

  // 개행 문자 제거 (최적화된 방식)
  for (int i = UART_State.cmd_index - 1; i >= 0; i--)
  {
    if (cmd_str[i] == '\n' || cmd_str[i] == '\r' || cmd_str[i] == ' ')
    {
      cmd_str[i] = '\0';
      UART_State.cmd_index = i;
    }
    else
    {
      break;
    }
  }

  // 명령어 길이 재확인
  if (UART_State.cmd_index == 0)
  {
    UART_State.command_ready = 0;
    return;
  }

  // 명령어 처리 (빈도 높은 명령어 우선 처리)
  if (memcmp(cmd_str, "GET_SCREEN", 10) == 0 && UART_State.cmd_index == 10)
  {
    UART_SendScreenData();
  }
  else if (memcmp(cmd_str, "GET_STATUS", 10) == 0 && UART_State.cmd_index == 10)
  {
    UART_SendStatusData();
  }
  else if (memcmp(cmd_str, "PING", 4) == 0 && UART_State.cmd_index == 4)
  {
    UART_SendResponse("PONG\n");
  }
  else if (memcmp(cmd_str, "TEST", 4) == 0 && UART_State.cmd_index == 4)
  {
    UART_SendResponse("TEST:OK\n");
  }
  else if (memcmp(cmd_str, "START_MONITOR", 13) == 0 && UART_State.cmd_index == 13)
  {
    UART_State.monitoring_enabled = 1;
    UART_SendResponse("OK:Monitoring started\n");
  }
  else if (memcmp(cmd_str, "STOP_MONITOR", 12) == 0 && UART_State.cmd_index == 12)
  {
    UART_State.monitoring_enabled = 0;
    UART_SendResponse("OK:Monitoring stopped\n");
  }
  else if (memcmp(cmd_str, "SET_UPDATE_MODE:", 16) == 0 && UART_State.cmd_index > 16)
  {
    UART_ProcessUpdateMode(cmd_str + 16);
  }
  else if (memcmp(cmd_str, "SET_TIMER:", 10) == 0 && UART_State.cmd_index > 10)
  {
    UART_ProcessTimerSet(cmd_str + 10);
  }
  else if (memcmp(cmd_str, "START_TIMER", 11) == 0 && UART_State.cmd_index == 11)
  {
    UART_ProcessTimerStart();
  }
  else if (memcmp(cmd_str, "STOP_TIMER", 10) == 0 && UART_State.cmd_index == 10)
  {
    UART_ProcessTimerStop();
  }
  else if (memcmp(cmd_str, "RESET", 5) == 0 && UART_State.cmd_index == 5)
  {
    UART_ProcessReset();
  }
  else if (memcmp(cmd_str, "GET_SIMPLE", 10) == 0 && UART_State.cmd_index == 10)
  {
    UART_SendResponse("SIMPLE:Test pattern sent\n");
  }
  else
  {
  }

  // 명령어 버퍼 즉시 초기화 (성능 최적화)
  UART_State.cmd_index = 0;
  UART_State.command_ready = 0;
}

/**
 * @brief 화면 데이터 전송 (안정성 강화 버전)
 */
void UART_SendScreenData(void)
{

  if (Paint.Image == NULL)
  {
    // 뮤텍스를 이미 획득한 상태이므로 직접 전송
    const char *error_msg = "ERROR:No screen data available\n";
    HAL_UART_Transmit(&huart1, (uint8_t *)error_msg, strlen(error_msg), 1000);
    osMutexRelease(UartMutexHandle);
    return;
  }

  // UART 플러시 (이전 데이터 완전 제거)
  __HAL_UART_FLUSH_DRREGISTER(&huart1);

  // 화면 데이터 시작 헤더 전송 (개행 문자 추가하여 명확히 구분)
  const char *header = "\n<<SCREEN_START>>\nSIZE:128x64\nFORMAT:PAINT_IMAGE\n";
  HAL_StatusTypeDef status = HAL_UART_Transmit(&huart1, (uint8_t *)header, strlen(header), 1000);

  if (status != HAL_OK)
  {
    // 헤더 전송 실패 시 중단
    osMutexRelease(UartMutexHandle);
    return;
  }

  // 전송 전 잠시 대기 (헤더 완전 전송 보장)
  osDelay(3);

  // Paint.Image 데이터를 한번에 전송 (안정성 강화)
  // OLED 화면 데이터: 128x64 = 8192 pixels = 1024 bytes (8 pixels per byte)
  uint16_t image_size = (OLED_1in3_C_WIDTH * OLED_1in3_C_HEIGHT) / 8; // 1024 bytes

  // 체크섬 계산 (데이터 무결성 검증용)
  uint32_t checksum = 0;
  for (uint16_t i = 0; i < image_size; i++)
  {
    checksum += Paint.Image[i];
  }

  // 체크섬 헤더 전송
  char checksum_header[32];
  snprintf(checksum_header, sizeof(checksum_header), "CHECKSUM:%08lX\n", checksum);
  HAL_UART_Transmit(&huart1, (uint8_t *)checksum_header, strlen(checksum_header), 1000);

  // 데이터 시작 마커
  const char *data_marker = "<<DATA_START>>\n";
  HAL_UART_Transmit(&huart1, (uint8_t *)data_marker, strlen(data_marker), 1000);
  // 전체 이미지를 한번에 전송 (최대 안정성)
  status = HAL_UART_Transmit(&huart1, Paint.Image, image_size, 3000); // 3초 타임아웃
  if (status != HAL_OK)
  {
    // 전송 실패시에도 종료 마커 전송
    const char *error_marker = "\n<<TRANSMISSION_ERROR>>\n";
    HAL_UART_Transmit(&huart1, (uint8_t *)error_marker, strlen(error_marker), 1000);
    osMutexRelease(UartMutexHandle);
    return;
  }

  // 전송 완료 후 안정화 딜레이
  osDelay(3);

  // 데이터 종료 마커
  const char *data_end_marker = "\n<<DATA_END>>\n";
  HAL_UART_Transmit(&huart1, (uint8_t *)data_end_marker, strlen(data_end_marker), 1000);

  // 화면 데이터 종료 헤더 전송 (개행 문자 추가)
  const char *footer = "<<SCREEN_END>>\n\n";
  HAL_UART_Transmit(&huart1, (uint8_t *)footer, strlen(footer), 1000);

  // 뮤텍스 해제
  osMutexRelease(UartMutexHandle);

  osDelay(1);
  UART_SendStatusData();
}

/**
 * @brief 상태 정보 전송
 */
/** __attribute__((optimize("O0"))) */
void UART_SendStatusData(void)
{
  // 뮤텍스 획득 (최대 100ms 대기)
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 100);
  osDelay(1);
  if (mutex_status != osOK)
  {
    // 뮤텍스 획득 실패 - 전송 포기
    return;
  }

  char status_buffer[256];

  // 새로운 배터리 모니터링 시스템에서 소수점 값 사용
  float battery_voltage = Battery_Get_Voltage(&Battery_Monitor);
  uint16_t battery_voltage_int = (uint16_t)(battery_voltage * 100);

  // 타이머 상태 문자열
  const char *status_str;
  if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
  {
    status_str = "SETTING";
  }
  else if (Button_State.is_start_to_cooling)
  {
    status_str = "COOLING";
  }
  else if (Button_State.is_Start_Timer)
  {
    status_str = "RUNNING";
  }
  else
  {
    status_str = "STANDBY";
  }

  // LED 연결 상태
  uint8_t l1_connected = (Adc_State.LED1_State != LED_STATE_MIDDLE) ? 1 : 0;
  uint8_t l2_connected = (Adc_State.LED2_State != LED_STATE_MIDDLE) ? 1 : 0;

  // 타이머 시간 계산
  uint8_t timer_minutes, timer_seconds;
  if (Button_State.Current_Button_State == BUTTON_STATE_TIMER_SET)
  {
    timer_minutes = Button_State.Timer_Value;
    timer_seconds = 0;
  }
  else if (Button_State.is_start_to_cooling)
  {
    timer_minutes = Button_State.cooling_second / 60;
    timer_seconds = Button_State.cooling_second % 60;
  }
  else
  {
    timer_minutes = Button_State.minute_count;
    timer_seconds = Button_State.second_count;
  }

  // 상태 정보 문자열 생성
  snprintf(status_buffer, sizeof(status_buffer),
           "STATUS:BAT:%dV,TIMER:%02d:%02d,STATUS:%s,L1:%d,L2:%d,BAT_ADC:%d,BAT_VOLT:%0.2f\n",
           battery_voltage_int, timer_minutes, timer_seconds, status_str, l1_connected, l2_connected, Adc_State.VBat_ADC_Value, battery_voltage);

  HAL_UART_Transmit(&huart1, (uint8_t *)status_buffer, strlen(status_buffer), 1000);

  // 뮤텍스 해제
  osMutexRelease(UartMutexHandle);
}

/**
 * @brief 응답 메시지 전송 (최적화된 버전)
 */
void UART_SendResponse(const char *response)
{
  // 뮤텍스 없이 직접 전송으로 응답성 최대화
  // 짧은 응답 메시지는 충돌 위험이 낮음
  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 500); // 타임아웃 단축
}

/**
 * @brief 타이머 설정 처리
 */
void UART_ProcessTimerSet(const char *time_str)
{
  int minutes, seconds;
  if (sscanf(time_str, "%d:%d", &minutes, &seconds) == 2)
  {
    if (minutes >= 0 && minutes <= 99 && seconds >= 0 && seconds <= 59)
    {
      // 실제 타이머 값 설정 (초 단위로 변환)
      Button_State.Timer_Value = minutes; // 분 단위로 저장
      UART_SendResponse("OK:Timer set\n");
    }
    else
    {
      UART_SendResponse("ERROR:Invalid time range\n");
    }
  }
  else
  {
    UART_SendResponse("ERROR:Invalid time format\n");
  }
}

/**
 * @brief 타이머 시작 처리
 */
void UART_ProcessTimerStart(void)
{
  if (!Button_State.is_Start_Timer && !Button_State.is_start_to_cooling)
  {
    Button_State.is_Start_Timer = true;
    Button_State.minute_count = Button_State.Timer_Value;
    Button_State.second_count = 0;

    // 메인 타이머 시작
    osTimerStart(MainTimerHandle, 1000);

    // 팬 ON
    HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_SET);

    UART_SendResponse("OK:Timer started\n");
  }
  else
  {
    UART_SendResponse("ERROR:Timer already running\n");
  }
}

/**
 * @brief 타이머 정지 처리
 */
void UART_ProcessTimerStop(void)
{
  if (Button_State.is_Start_Timer)
  {
    Button_State.is_Start_Timer = false;

    // 쿨링 시작 조건 확인
    if (Button_State.Timer_Value - Button_State.minute_count != 0 && Button_State.second_count <= 50)
    {
      Button_State.is_start_to_cooling = true;
      int8_t cooling_second = (Button_State.Timer_Value - Button_State.minute_count) * 10;
      if (cooling_second > 60)
        cooling_second = 60;
      Button_State.cooling_second = cooling_second;
      UART_SendResponse("OK:Timer stopped, cooling started\n");
    }
    else
    {
      // 완전 정지
      osTimerStop(MainTimerHandle);
      HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);
      UART_SendResponse("OK:Timer stopped\n");
    }
  }
  else
  {
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

  UART_SendResponse("OK:System reset\n");
}

/**
 * @brief 업데이트 모드 처리
 */
void UART_ProcessUpdateMode(const char *mode_str)
{
  // mode_str 형식: "REQUEST_RESPONSE,100" (모드,주기ms)
  char mode[32];
  int interval_ms = 100; // 기본값

  // 모드와 주기 파싱
  if (sscanf(mode_str, "%31[^,],%d", mode, &interval_ms) >= 1)
  {
    if (strcmp(mode, "REQUEST_RESPONSE") == 0)
    {
      // 요청-응답 모드 설정
      UART_State.monitoring_enabled = 1;

      // 주기 검증 (50ms ~ 5000ms 범위)
      if (interval_ms < 50)
        interval_ms = 50;
      if (interval_ms > 5000)
        interval_ms = 5000;

      // 간단한 OK 응답으로 변경 (파싱 오류 방지)
      UART_SendResponse("OK:Request-Response mode set\n");
    }
    else if (strcmp(mode, "AUTO") == 0)
    {
      // 자동 모드는 더 이상 지원하지 않음 - 요청-응답 방식만 지원
      UART_State.monitoring_enabled = 1;

      // 간단한 OK 응답으로 변경 (파싱 오류 방지)
      UART_SendResponse("OK:Request-Response mode set\n");
    }
    else if (strcmp(mode, "MANUAL") == 0)
    {
      // 수동 모드
      UART_State.monitoring_enabled = 0;

      UART_SendResponse("OK:Manual mode set\n");
    }
    else
    {
      UART_SendResponse("ERROR:Unknown update mode\n");
    }
  }
  else
  {
    UART_SendResponse("ERROR:Invalid update mode format\n");
  }
}
