/* Includes ------------------------------------------------------------------*/
#include "flash_storage.h"
#include <string.h>

/* Private functions ---------------------------------------------------------*/

/**
 * @brief  체크섬을 계산합니다
 * @param  data: 체크섬을 계산할 데이터 구조체
 * @retval 계산된 체크섬
 */
uint32_t Flash_CalculateChecksum(const FlashData_t *data)
{
    uint32_t checksum = 0;
    uint8_t *ptr = (uint8_t *)data;
    
    // checksum 필드를 제외한 모든 바이트를 합산
    for (int i = 0; i < (int)(sizeof(FlashData_t) - sizeof(data->checksum)); i++)
    {
        checksum += ptr[i];
    }
    
    return checksum;
}

/**
 * @brief  플래시 메모리의 데이터가 유효한지 확인합니다
 * @retval 1: 유효한 데이터, 0: 유효하지 않은 데이터
 */
uint8_t Flash_IsDataValid(void)
{
    FlashData_t *flash_data = (FlashData_t *)FLASH_STORAGE_ADDR;
    
    // 매직 넘버 확인
    if (flash_data->magic != FLASH_MAGIC_NUMBER)
    {
        return 0;
    }
    
    // 버전 확인
    if (flash_data->version != FLASH_VERSION)
    {
        return 0;
    }
    
    // 체크섬 확인
    uint32_t calculated_checksum = Flash_CalculateChecksum(flash_data);
    if (flash_data->checksum != calculated_checksum)
    {
        return 0;
    }
    
    return 1;
}

/**
 * @brief  저장용 플래시 페이지를 지웁니다
 * @retval HAL status
 */
HAL_StatusTypeDef Flash_EraseStoragePage(void)
{
    HAL_StatusTypeDef status = HAL_OK;
    FLASH_EraseInitTypeDef erase_init;
    uint32_t page_error = 0;
    
    // 플래시 언락
    status = HAL_FLASH_Unlock();
    if (status != HAL_OK)
    {
        return status;
    }
    
    // 페이지 지우기 설정
    erase_init.TypeErase = FLASH_TYPEERASE_PAGES;
    erase_init.Banks = FLASH_BANK_1;
    erase_init.Page = FLASH_STORAGE_PAGE;
    erase_init.NbPages = 1;
    
    // 페이지 지우기 실행
    status = HAL_FLASHEx_Erase(&erase_init, &page_error);
    
    // 플래시 락
    HAL_FLASH_Lock();
    
    return status;
}

/**
 * @brief  타이머 값을 플래시 메모리에 저장합니다
 * @param  timer_value: 저장할 타이머 값 (초 단위)
 * @retval HAL status
 */
HAL_StatusTypeDef Flash_WriteTimerValue(uint32_t timer_value)
{
    HAL_StatusTypeDef status = HAL_OK;
    FlashData_t flash_data;
    uint64_t *data_ptr = (uint64_t *)&flash_data;
    uint32_t write_addr = FLASH_STORAGE_ADDR;
    
    // 기존 데이터 읽기 (배터리 데이터 보존)
    if (Flash_IsDataValid())
    {
        FlashData_t *existing_data = (FlashData_t *)FLASH_STORAGE_ADDR;
        flash_data = *existing_data;
    }
    else
    {
        // 새로운 데이터 구조체 초기화
        memset(&flash_data, 0, sizeof(FlashData_t));
        flash_data.magic = FLASH_MAGIC_NUMBER;
        flash_data.version = FLASH_VERSION;
        flash_data.reserved = 0;
        flash_data.battery_percentage = 50;  // 기본값
        flash_data.battery_status = 0;       // BATTERY_STATUS_NORMAL
        flash_data.last_battery_adc = 3300;  // 기본 ADC 값
    }
    
    // 타이머 값 업데이트
    flash_data.timer_value = timer_value;
    flash_data.checksum = Flash_CalculateChecksum(&flash_data);
    
    // 페이지 지우기
    status = Flash_EraseStoragePage();
    if (status != HAL_OK)
    {
        return status;
    }
    
    // 플래시 언락
    status = HAL_FLASH_Unlock();
    if (status != HAL_OK)
    {
        return status;
    }
    
    // 데이터를 8바이트 단위로 쓰기 (STM32L4는 더블워드 단위 쓰기)
    int data_size = sizeof(FlashData_t);
    int write_count = (data_size + 7) / 8; // 8바이트 단위로 올림
    
    for (int i = 0; i < write_count; i++)
    {
        uint64_t write_data = 0;
        
        // 8바이트씩 복사 (마지막은 부족할 수 있음)
        if (i < write_count - 1 || (data_size % 8) == 0)
        {
            write_data = data_ptr[i];
        }
        else
        {
            // 마지막 부분이 8바이트보다 작은 경우
            memcpy(&write_data, &data_ptr[i], data_size % 8);
        }
        
        status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, 
                                   write_addr + (i * 8), 
                                   write_data);
        if (status != HAL_OK)
        {
            break;
        }
    }
    
    // 플래시 락
    HAL_FLASH_Lock();
    
    return status;
}

/**
 * @brief  배터리 데이터를 플래시 메모리에 저장합니다
 * @param  percentage: 배터리 잔량 퍼센트
 * @param  status: 배터리 상태
 * @param  adc_value: 배터리 ADC 값
 * @retval HAL status
 */
HAL_StatusTypeDef Flash_WriteBatteryData(uint8_t percentage, uint8_t status, uint16_t adc_value)
{
    HAL_StatusTypeDef hal_status = HAL_OK;
    FlashData_t flash_data;
    uint64_t *data_ptr = (uint64_t *)&flash_data;
    uint32_t write_addr = FLASH_STORAGE_ADDR;
    
    // 기존 데이터 읽기 (타이머 데이터 보존)
    if (Flash_IsDataValid())
    {
        FlashData_t *existing_data = (FlashData_t *)FLASH_STORAGE_ADDR;
        flash_data = *existing_data;
    }
    else
    {
        // 새로운 데이터 구조체 초기화
        memset(&flash_data, 0, sizeof(FlashData_t));
        flash_data.magic = FLASH_MAGIC_NUMBER;
        flash_data.version = FLASH_VERSION;
        flash_data.reserved = 0;
        flash_data.timer_value = 10;  // 기본 타이머 값
    }
    
    // 배터리 데이터 업데이트
    flash_data.battery_percentage = percentage;
    flash_data.battery_status = status;
    flash_data.last_battery_adc = adc_value;
    flash_data.checksum = Flash_CalculateChecksum(&flash_data);
    
    // 페이지 지우기
    hal_status = Flash_EraseStoragePage();
    if (hal_status != HAL_OK)
    {
        return hal_status;
    }
    
    // 플래시 언락
    hal_status = HAL_FLASH_Unlock();
    if (hal_status != HAL_OK)
    {
        return hal_status;
    }
    
    // 데이터를 8바이트 단위로 쓰기
    int data_size = sizeof(FlashData_t);
    int write_count = (data_size + 7) / 8;
    
    for (int i = 0; i < write_count; i++)
    {
        uint64_t write_data = 0;
        
        if (i < write_count - 1 || (data_size % 8) == 0)
        {
            write_data = data_ptr[i];
        }
        else
        {
            memcpy(&write_data, &data_ptr[i], data_size % 8);
        }
        
        hal_status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, 
                                       write_addr + (i * 8), 
                                       write_data);
        if (hal_status != HAL_OK)
        {
            break;
        }
    }
    
    // 플래시 락
    HAL_FLASH_Lock();
    
    return hal_status;
}

/**
 * @brief  플래시 메모리에서 타이머 값을 읽습니다
 * @param  timer_value: 읽은 타이머 값을 저장할 포인터
 * @retval HAL status
 */
HAL_StatusTypeDef Flash_ReadTimerValue(uint32_t *timer_value)
{
    if (timer_value == NULL)
    {
        return HAL_ERROR;
    }
    
    // 데이터 유효성 확인
    if (!Flash_IsDataValid())
    {
        // 유효하지 않은 데이터인 경우 기본값 설정
        *timer_value = 10; // 기본 타이머 값: 10초
        return HAL_ERROR;
    }
    
    // 유효한 데이터에서 타이머 값 읽기
    FlashData_t *flash_data = (FlashData_t *)FLASH_STORAGE_ADDR;
    *timer_value = flash_data->timer_value;
    
    return HAL_OK;
}

/**
 * @brief  플래시 메모리에서 배터리 데이터를 읽습니다
 * @param  percentage: 배터리 잔량 퍼센트를 저장할 포인터
 * @param  status: 배터리 상태를 저장할 포인터
 * @param  adc_value: 배터리 ADC 값을 저장할 포인터
 * @retval HAL status
 */
HAL_StatusTypeDef Flash_ReadBatteryData(uint8_t *percentage, uint8_t *status, uint16_t *adc_value)
{
    if (percentage == NULL || status == NULL || adc_value == NULL)
    {
        return HAL_ERROR;
    }
    
    // 데이터 유효성 확인
    if (!Flash_IsDataValid())
    {
        // 유효하지 않은 데이터인 경우 기본값 설정
        *percentage = 50;  // 기본 배터리 잔량: 50%
        *status = 0;       // BATTERY_STATUS_NORMAL
        *adc_value = 3300; // 기본 ADC 값 (약 22.5V)
        return HAL_ERROR;
    }
    
    // 유효한 데이터에서 배터리 정보 읽기
    FlashData_t *flash_data = (FlashData_t *)FLASH_STORAGE_ADDR;
    *percentage = flash_data->battery_percentage;
    *status = flash_data->battery_status;
    *adc_value = flash_data->last_battery_adc;
    
    return HAL_OK;
} 