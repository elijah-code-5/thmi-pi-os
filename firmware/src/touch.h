#pragma once
#include <SPI.h>
#include "pins.h"

// Minimal XPT2046 reader on its own SPI bus. Calibration constants are rough defaults.
static SPIClass touchSPI(HSPI);
static bool streaming = false;

static inline void touchBegin() {
  touchSPI.begin(PIN_TOUCH_SCK, PIN_TOUCH_MISO, PIN_TOUCH_MOSI, PIN_TOUCH_CS);
  pinMode(PIN_TOUCH_CS, OUTPUT);
  digitalWrite(PIN_TOUCH_CS, HIGH);
}

static uint16_t xptRead(uint8_t cmd) {
  touchSPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_TOUCH_CS, LOW);
  touchSPI.transfer(cmd);
  uint16_t v = touchSPI.transfer16(0) >> 3;
  digitalWrite(PIN_TOUCH_CS, HIGH);
  touchSPI.endTransaction();
  return v;
}

static inline bool touchPoint(int& x, int& y) {
  if (xptRead(0xB1) < 400) return false;       // pressure too low = no touch
  uint16_t rx = xptRead(0xD1), ry = xptRead(0x91);
  x = constrain(map(ry, 200, 3900, 0, 320), 0, 319);
  y = constrain(map(rx, 200, 3900, 0, 240), 0, 239);
  return true;
}
