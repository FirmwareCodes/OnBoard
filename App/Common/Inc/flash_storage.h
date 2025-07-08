#ifndef __FLASH_STORAGE_H
#define __FLASH_STORAGE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "stm32l4xx_hal.h"

/* Defines -------------------------------------------------------------------*/
// STM32L412의 플래시 메모리 설정
#define FLASH_PAGE_SIZE         ((uint32_t)0x800)    // 2KB per page
#define FLASH_STORAGE_PAGE      31                    // 마지막 페이지 사용 (페이지 31)
#define FLASH_STORAGE_ADDR      (FLASH_BASE + (FLASH_STORAGE_PAGE * FLASH_PAGE_SIZE))

// 저장할 데이터 구조체 정의
#define FLASH_MAGIC_NUMBER      0xABCD2111           // 유효한 데이터 확인용 매직 넘버
#define FLASH_VERSION           0x0001               // 데이터 버전

/* Structures ----------------------------------------------------------------*/
typedef struct {
    uint32_t magic;                 // 매직 넘버 (데이터 유효성 확인)
    uint16_t version;               // 버전 정보
    uint16_t reserved;              // 예약 필드
    uint32_t timer_value;           // 저장할 타이머 값 (초 단위)
    uint8_t battery_percentage;     // 배터리 잔량 퍼센트
    uint8_t battery_status;         // 배터리 상태
    uint16_t last_battery_adc;      // 마지막 배터리 ADC 값
    uint32_t checksum;              // 체크섬
} FlashData_t;

/* Function prototypes -------------------------------------------------------*/
HAL_StatusTypeDef Flash_EraseStoragePage(void);
HAL_StatusTypeDef Flash_WriteTimerValue(uint32_t timer_value);
HAL_StatusTypeDef Flash_ReadTimerValue(uint32_t *timer_value);
HAL_StatusTypeDef Flash_WriteBatteryData(uint8_t percentage, uint8_t status, uint16_t adc_value);
HAL_StatusTypeDef Flash_ReadBatteryData(uint8_t *percentage, uint8_t *status, uint16_t *adc_value);
uint32_t Flash_CalculateChecksum(const FlashData_t *data);
uint8_t Flash_IsDataValid(void);

#ifdef __cplusplus
}
#endif

#endif /* __FLASH_STORAGE_H */ 