/**
 ******************************************************************************
 * @file    fonts.h
 * @author  MCD Application Team
 * @version V1.0.0
 * @date    18-February-2014
 * @brief   Header for fonts.c file
 ******************************************************************************
 * @attention
 *
 * <h2><center>&copy; COPYRIGHT(c) 2014 STMicroelectronics</center></h2>
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 *   1. Redistributions of source code must retain the above copyright notice,
 *      this list of conditions and the following disclaimer.
 *   2. Redistributions in binary form must reproduce the above copyright notice,
 *      this list of conditions and the following disclaimer in the documentation
 *      and/or other materials provided with the distribution.
 *   3. Neither the name of STMicroelectronics nor the names of its contributors
 *      may be used to endorse or promote products derived from this software
 *      without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 ******************************************************************************
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __FONTS_H
#define __FONTS_H

/*중문字库24 (32x41) */
#define MAX_HEIGHT_FONT 41
#define MAX_WIDTH_FONT 32
#define OFFSET_BITMAP

#ifdef __cplusplus
extern "C"
{
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

  // ASCII
  typedef struct _tFont
  {
    const uint8_t *table;
    uint16_t Width;
    uint16_t Height;

  } sFONT;

  // GB2312
  typedef struct // 中文字模数据结构
  {
    unsigned char index[2];                                  // 中文内码索引
    const char matrix[MAX_HEIGHT_FONT * MAX_WIDTH_FONT / 8]; // 点阵字模数据
  } CH_CN;

  typedef struct
  {
    const CH_CN *table;
    uint16_t size;
    uint16_t ASCII_Width;
    uint16_t Width;
    uint16_t Height;

  } cFONT;

  extern sFONT Font24;
  extern sFONT Font12;
  extern sFONT FontIcon16;  // Simple 16x16 Icon Font
  extern sFONT FontImage24; // Simple 24x24 Image Font

  extern cFONT Font12CN;
  extern cFONT Font24CN;

/* Simple Icon Font Character Mapping for FontIcon16 (128x64 OLED Optimized) */
#define ICON_SPACE ' '        // 0x20 - Empty space
#define ICON_CONNECTED '!'    // 0x21 - Connected O (큰 원)
#define ICON_DISCONNECTED '"' // 0x22 - Disconnected X (큰 X)
#define ICON_STANDBY '#'      // 0x23 - STANDBY (사각형 안 대기선)
#define ICON_TIMER_SET '$'    // 0x24 - TIMER SET (별 모양 톱니바퀴)
#define ICON_PLAY '&'         // 0x26 - PLAY (재생 삼각형)
#define ICON_STOP '\''        // 0x27 - STOP (정지 사각형)

/* Battery Icon Definitions (7 levels) */
#define ICON_BATTERY_EMPTY 44    // 0x2C - BATTERY EMPTY (빈 배터리)
#define ICON_BATTERY_VERY_LOW 45 // 0x2D - BATTERY VERY LOW (1칸 채움)
#define ICON_BATTERY_LOW 46     // 0x2D - BATTERY VERY LOW (1칸 채움)
#define ICON_BATTERY_MIDLOW 47  // 0x2E - BATTERY LOW (2칸 채움)
#define ICON_BATTERY_MID 48     // 0x2F - BATTERY MID (3칸 채움)
#define ICON_BATTERY_MIDHIGH 49 // 0x30 - BATTERY MIDHIGH (4칸 채움)
#define ICON_BATTERY_HIGH 50     // 0x31 - BATTERY HIGH (5칸 채움)
#define ICON_BATTERY_FULL 51     // 0x32 - BATTERY FULL (완전 채움)

/* Helper macros for drawing icons */
#define DRAW_ICON(x, y, icon, fg, bg) Paint_DrawChar(x, y, icon, &FontIcon16, fg, bg)

#ifdef __cplusplus
}
#endif

#endif /* __FONTS_H */

/************************ (C) COPYRIGHT STMicroelectronics *****END OF FILE****/
