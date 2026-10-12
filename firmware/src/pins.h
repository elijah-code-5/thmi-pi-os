#pragma once
// LilyGO T-HMI pin map.
// IMPORTANT: written from memory of the T-HMI schematic and NOT yet verified on hardware.
// If something does not respond (touch, SD, backlight), compare these against the official
// LilyGO T-HMI pin_config.h and fix the numbers here only. Display pins live in platformio.ini.

#define PIN_PWR_EN   10   // main power enable (must be HIGH to run on battery)
#define PIN_PWR_ON   14   // peripheral power
#define PIN_BAT_ADC  5

#define PIN_TOUCH_SCK  1
#define PIN_TOUCH_MISO 4
#define PIN_TOUCH_MOSI 3
#define PIN_TOUCH_CS   2
#define PIN_TOUCH_IRQ  9

#define PIN_SD_CLK  11
#define PIN_SD_CMD  10
#define PIN_SD_D0   13
