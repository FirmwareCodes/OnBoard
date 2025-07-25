/******************************************************************************
**************************Hardware interface layer*****************************
* | file      		:	DEV_Config.c
* |	version			:	V1.0
* | date			:	2020-06-17
* | function		:	Provide the hardware underlying interface
******************************************************************************/
#include "DEV_Config.h"

#include "stm32L4xx_hal_spi.h"

// #include "usart.h"
#include <stdio.h> //printf()
#include <string.h>
#include <stdlib.h>

extern SPI_HandleTypeDef hspi1;

/********************************************************************************
function:	System Init
note:
	Initialize the communication method
********************************************************************************/
uint8_t System_Init(void)
{
#if USE_SPI_4W
	// printf("USE_SPI_4W\r\n");
#elif USE_IIC
	printf("USE_IIC\r\n");
	OLED_CS_0;
	OLED_DC_0; // DC = 0,1 >> Address = 0x3c,0x3d
#elif USE_IIC_SOFT
	printf("USEI_IIC_SOFT\r\n");
	OLED_CS_0;
	OLED_DC_0;
#endif
	return 0;
}

void System_Exit(void)
{
}
/********************************************************************************
function:	Hardware interface
note:
	SPI4W_Write_Byte(value) :
		HAL library hardware SPI
		Register hardware SPI
		Gpio analog SPI
	I2C_Write_Byte(value, cmd):
		HAL library hardware I2C
********************************************************************************/
uint8_t SPI4W_Write_Byte(uint8_t value)
{
	return HAL_SPI_Transmit(&hspi1, &value, 1, 10);
	
}

/********************************************************************************
function:	Delay function
note:
	Driver_Delay_ms(xms) : Delay x ms
	Driver_Delay_us(xus) : Delay x us
********************************************************************************/
void Driver_Delay_ms(uint32_t xms)
{
	HAL_Delay(xms);
}

void Driver_Delay_us(uint32_t xus)
{
	int j;
	for (j = xus; j > 0; j--)
		;
}
