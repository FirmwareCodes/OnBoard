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

void UART_ProcessCommand(void)
{
  char *cmd_str = (char *)UART_State.cmd_buffer;

  if (UART_State.cmd_index == 0)
  {
    UART_State.command_ready = 0;
    return;
  }

  UART_State.cmd_buffer[UART_State.cmd_index] = '\0';

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

  if (UART_State.cmd_index == 0)
  {
    UART_State.command_ready = 0;
    return;
  }

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

  UART_State.cmd_index = 0;
  UART_State.command_ready = 0;
}

void UART_SendScreenData(void)
{
  if (Paint.Image == NULL)
  {
    const char *error_msg = "ERROR:No screen data available\n";
    HAL_UART_Transmit(&huart1, (uint8_t *)error_msg, strlen(error_msg), 1000);
    osMutexRelease(UartMutexHandle);
    return;
  }

  __HAL_UART_FLUSH_DRREGISTER(&huart1);

  const char *header = "\n<<SCREEN_START>>\nSIZE:128x64\nFORMAT:PAINT_IMAGE\n";
  HAL_StatusTypeDef status = HAL_UART_Transmit(&huart1, (uint8_t *)header, strlen(header), 1000);

  if (status != HAL_OK)
  {
    osMutexRelease(UartMutexHandle);
    return;
  }

  osDelay(3);

  uint16_t image_size = (OLED_1in3_C_WIDTH * OLED_1in3_C_HEIGHT) / 8;

  uint32_t checksum = 0;
  for (uint16_t i = 0; i < image_size; i++)
  {
    checksum += Paint.Image[i];
  }

  char checksum_header[32];
  snprintf(checksum_header, sizeof(checksum_header), "CHECKSUM:%08lX\n", checksum);
  HAL_UART_Transmit(&huart1, (uint8_t *)checksum_header, strlen(checksum_header), 1000);

  const char *data_marker = "<<DATA_START>>\n";
  HAL_UART_Transmit(&huart1, (uint8_t *)data_marker, strlen(data_marker), 1000);

  status = HAL_UART_Transmit(&huart1, Paint.Image, image_size, 3000);
  if (status != HAL_OK)
  {
    const char *error_marker = "\n<<TRANSMISSION_ERROR>>\n";
    HAL_UART_Transmit(&huart1, (uint8_t *)error_marker, strlen(error_marker), 1000);
    osMutexRelease(UartMutexHandle);
    return;
  }

  osDelay(3);

  const char *data_end_marker = "\n<<DATA_END>>\n";
  HAL_UART_Transmit(&huart1, (uint8_t *)data_end_marker, strlen(data_end_marker), 1000);

  const char *footer = "<<SCREEN_END>>\n\n";
  HAL_UART_Transmit(&huart1, (uint8_t *)footer, strlen(footer), 1000);

  osMutexRelease(UartMutexHandle);

  osDelay(1);
  UART_SendStatusData();
}

__attribute__((optimize("O0"))) void UART_SendStatusData(void)
{
  osStatus_t mutex_status = osMutexAcquire(UartMutexHandle, 100);
  osDelay(1);
  if (mutex_status != osOK)
  {
    return;
  }

  char status_buffer[256];

  float battery_percent_float = Battery_Get_Percentage_Float(&Battery_Monitor);
  float battery_voltage = Battery_Get_Voltage(&Battery_Monitor);
  
  if (battery_percent_float > 100.0f)
  {
    battery_percent_float = 100.0f;
  }
  else if (battery_percent_float < 0.0f)
  {
    battery_percent_float = 0.0f;
  }

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

  uint8_t l1_connected = (Adc_State.LED1_State != LED_STATE_MIDDLE) ? 1 : 0;
  uint8_t l2_connected = (Adc_State.LED2_State != LED_STATE_MIDDLE) ? 1 : 0;

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

  snprintf(status_buffer, sizeof(status_buffer),
           "STATUS:BAT:%0.2f%%,TIMER:%02d:%02d,STATUS:%s,L1:%d,L2:%d,BAT_ADC:%d,BAT_VOLT:%0.2f\n",
           battery_percent_float, timer_minutes, timer_seconds, status_str, l1_connected, l2_connected, Adc_State.VBat_ADC_Value, battery_voltage);

  HAL_UART_Transmit(&huart1, (uint8_t *)status_buffer, strlen(status_buffer), 1000);

  osMutexRelease(UartMutexHandle);
}

void UART_SendResponse(const char *response)
{
  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 500);
}

void UART_ProcessTimerSet(const char *time_str)
{
  int minutes, seconds;
  if (sscanf(time_str, "%d:%d", &minutes, &seconds) == 2)
  {
    if (minutes >= 0 && minutes <= 99 && seconds >= 0 && seconds <= 59)
    {
      Button_State.Timer_Value = minutes;
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

void UART_ProcessTimerStart(void)
{
  if (!Button_State.is_Start_Timer && !Button_State.is_start_to_cooling)
  {
    Button_State.is_Start_Timer = true;
    Button_State.minute_count = Button_State.Timer_Value;
    Button_State.second_count = 0;

    osTimerStart(MainTimerHandle, 1000);
    HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_SET);

    UART_SendResponse("OK:Timer started\n");
  }
  else
  {
    UART_SendResponse("ERROR:Timer already running\n");
  }
}

void UART_ProcessTimerStop(void)
{
  if (Button_State.is_Start_Timer)
  {
    Button_State.is_Start_Timer = false;

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

void UART_ProcessReset(void)
{
  Button_State.is_Start_Timer = false;
  Button_State.is_start_to_cooling = false;
  Button_State.Current_Button_State = BUTTON_STATE_STANDBY;

  osTimerStop(MainTimerHandle);
  HAL_GPIO_WritePin(FAN_ONOFF_GPIO_Port, FAN_ONOFF_Pin, GPIO_PIN_RESET);

  UART_State.monitoring_enabled = 0;

  UART_SendResponse("OK:System reset\n");
}

void UART_ProcessUpdateMode(const char *mode_str)
{
  char mode[32];
  int interval_ms = 100;

  if (sscanf(mode_str, "%31[^,],%d", mode, &interval_ms) >= 1)
  {
    if (strcmp(mode, "REQUEST_RESPONSE") == 0)
    {
      UART_State.monitoring_enabled = 1;

      if (interval_ms < 50)
        interval_ms = 50;
      if (interval_ms > 5000)
        interval_ms = 5000;

      UART_SendResponse("OK:Request-Response mode set\n");
    }
    else if (strcmp(mode, "AUTO") == 0)
    {
      UART_State.monitoring_enabled = 1;
      UART_SendResponse("OK:Request-Response mode set\n");
    }
    else if (strcmp(mode, "MANUAL") == 0)
    {
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
