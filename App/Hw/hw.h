#ifndef HW_H_
#define HW_H_

#ifndef __cplusplus

#include "..\Common\def.h"

#pragma region F401_INCLUDES
#pragma endregion

uint32_t millis(void);

void delay_us(uint32_t us);
void delay_ms(uint32_t ms);
void delay_s(uint32_t s);
#endif

#endif
