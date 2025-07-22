#ifndef __UART_PROTOCOL_H
#define __UART_PROTOCOL_H

#ifdef __cplusplus
extern "C"
{
#endif

#include "main.h"
#include "stm32l4xx_hal.h"
#include "def.h"

    // UART 태스크용 전역 변수
    typedef struct
    {
        uint8_t rx_buffer[128];     // 수신 버퍼
        uint8_t tx_buffer[1200];    // 송신 버퍼 (화면 데이터용)
        uint8_t cmd_buffer[128];    // 명령어 버퍼
        uint16_t rx_index;          // 수신 인덱스
        uint16_t cmd_index;         // 명령어 인덱스
        uint8_t command_ready;      // 명령어 준비 플래그
        uint8_t monitoring_enabled; // 모니터링 활성화 플래그 (요청-응답 모드용)
    } UART_State_t;

    // UART 태스크 관련 함수 프로토타입
    void UART_ProcessCommand(void);
    void UART_SendScreenData(void);
    void UART_SendStatusData(void);
    void UART_SendResponse(const char *response);
    void UART_ProcessTimerSet(const char *time_str);
    void UART_ProcessTimerStart(void);
    void UART_ProcessTimerStop(void);
    void UART_ProcessReset(void);
    void UART_ProcessUpdateMode(const char *mode_str);

#ifdef __cplusplus
}
#endif

#endif // __UART_PROTOCOL_H
