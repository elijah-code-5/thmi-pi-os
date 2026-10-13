#pragma once
// Pin map copied from LilyGO's official T-HMI examples (examples/factory/pins.h).
#define PWR_EN_PIN   10   // HIGH keeps power on when running from battery
#define PWR_ON_PIN   14   // HIGH when powered from the 5V connector
#define BAT_ADC_PIN  5
#define BUTTON1_PIN  0    // BOOT button
#define BUTTON2_PIN  21

#define BK_LIGHT_PIN 38   // display backlight (display data pins are set in platformio.ini)

#define TOUCHSCREEN_SCLK_PIN 1
#define TOUCHSCREEN_MISO_PIN 4
#define TOUCHSCREEN_MOSI_PIN 3
#define TOUCHSCREEN_CS_PIN   2
#define TOUCHSCREEN_IRQ_PIN  9

#define SD_SCLK_PIN 12
#define SD_CMD_PIN  11
#define SD_D0_PIN   13
