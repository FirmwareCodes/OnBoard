#include "hw.h"

uint32_t millis(void) { return HAL_GetTick(); }

#pragma region USER DELAY FUNCTION
/**
 * USER Delay Function
 * @param tick: 지연 시간 (1Tick = 1us)
 * 최종 조정: 15개 NOP로 설정하여 Delay_us(100) = 100.44us
 * 1ms = 1.00414ms
 * 10ms = 10.0367ms
 * 100ms 100.36276ms
 * 주의 : __attribute__((optimize("O0"))) 삭제 금지 최적화시 타이밍이 달라짐
 */
__attribute__((optimize("O0"))) void delay_us(uint32_t us)
{
    for (uint32_t i = 0; i < us; i++)
    {
        for (uint32_t j = 0; j < 5; j++)
        {
            __asm("nop");
            __asm("nop");
            __asm("nop");
        }
    }
}

__attribute__((optimize("O0"))) void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0; i < ms; i++)
    {
        delay_us(1000);
    }
}

__attribute__((optimize("O0"))) void delay_s(uint32_t s)
{
    for (uint32_t i = 0; i < s; i++)
    {
        delay_ms(1000);
    }
}
#pragma endregion USER DELAY FUNCTION