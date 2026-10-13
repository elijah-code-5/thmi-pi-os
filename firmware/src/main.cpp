// T-HMI handheld client for the Pi brain (portrait 240x320, pins/touch from LilyGO's official examples).
// Screens: Home, Files (microSD), Music (SD -> Pi -> Bluetooth), Notes (finger drawing),
// Stream (video/games from the Pi), Robot, Settings.
#include <Arduino.h>
#include <SD_MMC.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <xpt2046.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include "pins.h"

TFT_eSPI tft;
TFT_eSprite page(&tft);
XPT2046 touch(SPI, TOUCHSCREEN_CS_PIN, TOUCHSCREEN_IRQ_PIN);
Preferences prefs;

String piHost = "thmi-hub.local";
const int PORT = 80;                 // hub answers on 80 and 8765
enum Screen { HOME, FILES, MUSIC, NOTES, STREAM, ROBOT, SETTINGS };
Screen cur = HOME;
bool sdOk = false, wifiOk = false, streaming = false, safeMode = false, pageOk = false;
const int W = 240, H = 320, BAR = 28, TOOL = 28;

struct Btn { int x, y, w, h; const char* label; Screen target; };
Btn homeBtns[] = {
  {8, 40, 110, 60, "Files", FILES},     {122, 40, 110, 60, "Music", MUSIC},
  {8, 110, 110, 60, "Notes", NOTES},    {122, 110, 110, 60, "Stream", STREAM},
  {8, 180, 110, 60, "Robot", ROBOT},    {122, 180, 110, 60, "Settings", SETTINGS},
};

String base() { return "http://" + piHost + ":" + String(PORT); }
bool hit(int x, int y, int bx, int by, int bw, int bh) { return x >= bx && x < bx + bw && y >= by && y < by + bh; }

void header(const char* t) {
  tft.fillScreen(TFT_BLACK);
  tft.fillRect(0, 0, W, BAR, TFT_NAVY);
  tft.setTextColor(TFT_WHITE, TFT_NAVY);
  tft.drawString(t, 8, 5, 4);
  tft.drawString("<", 220, 5, 4);
}

void drawHome() {
  header("T-HMI Hub");
  for (auto& b : homeBtns) {
    tft.fillRoundRect(b.x, b.y, b.w, b.h, 8, TFT_DARKGREEN);
    tft.setTextColor(TFT_WHITE, TFT_DARKGREEN);
    tft.drawCentreString(b.label, b.x + b.w / 2, b.y + 20, 4);
  }
  tft.setTextColor(sdOk ? TFT_GREEN : TFT_RED, TFT_BLACK);
  tft.drawString(sdOk ? "SD ok" : "No SD", 8, 270, 2);
  tft.setTextColor(wifiOk ? TFT_GREEN : TFT_RED, TFT_BLACK);
  tft.drawString(wifiOk ? "Wi-Fi ok" : "No Wi-Fi", 8, 292, 2);
  if (safeMode) { tft.setTextColor(TFT_YELLOW, TFT_BLACK); tft.drawString("Safe mode", 120, 292, 2); }
}

// ---------- Files ----------
void drawFiles() {
  header("Files (SD)");
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  if (!sdOk) { tft.drawString("No SD card", 8, 50, 4); return; }
  File root = SD_MMC.open("/");
  int y = 36;
  for (File f = root.openNextFile(); f && y < 300; f = root.openNextFile()) {
    tft.setTextColor(f.isDirectory() ? TFT_YELLOW : TFT_WHITE, TFT_BLACK);
    tft.drawString(String(f.name()) + (f.isDirectory() ? "/" : ""), 8, y, 2);
    y += 18;
  }
}

// ---------- Music: send the SD file to the Pi, which plays it to Bluetooth headphones ----------
String musicFiles[32]; int musicN = 0;
void scanMusic() {
  musicN = 0;
  if (!sdOk) return;
  File root = SD_MMC.open("/");
  for (File f = root.openNextFile(); f && musicN < 32; f = root.openNextFile()) {
    String n = f.name(); String l = n; l.toLowerCase();
    if (!f.isDirectory() && (l.endsWith(".mp3") || l.endsWith(".wav") || l.endsWith(".flac") || l.endsWith(".ogg")))
      musicFiles[musicN++] = n;
  }
}
void drawMusic() {
  header("Music");
  scanMusic();
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  if (!musicN) tft.drawString(sdOk ? "No music files on SD" : "No SD card", 8, 40, 2);
  for (int i = 0; i < musicN && i < 10; i++) tft.drawString(musicFiles[i], 8, 36 + i * 24, 2);
  tft.fillRoundRect(8, 288, 100, 26, 4, TFT_RED);   tft.setTextColor(TFT_WHITE, TFT_RED);   tft.drawString("Stop", 36, 293, 2);
  tft.fillRoundRect(122, 288, 110, 26, 4, TFT_BLUE); tft.setTextColor(TFT_WHITE, TFT_BLUE); tft.drawString("Pair BT", 142, 293, 2);
}
void piPost(const String& p) {
  if (!wifiOk) return;
  HTTPClient h; h.setTimeout(3000); h.begin(base() + p); h.POST(""); h.end();
}
void playOnPi(const String& name) {
  if (!wifiOk) return;
  File f = SD_MMC.open("/" + name);
  if (!f) return;
  HTTPClient http; http.setTimeout(30000);
  http.begin(base() + "/api/play/upload?name=" + name);
  http.sendRequest("POST", &f, f.size());
  http.end(); f.close();
}

// ---------- Notes: finger drawing, kept in a PSRAM sprite, saved to SD ----------
int penX = -1, penY = -1, notePage = 0;
void drawNotes() {
  header("Notes");
  tft.fillRect(0, BAR, W, TOOL, TFT_LIGHTGREY);
  tft.setTextColor(TFT_BLACK, TFT_LIGHTGREY);
  tft.drawString("Clear", 12, BAR + 6, 2);
  tft.drawString("Save", 100, BAR + 6, 2);
  tft.fillRect(0, BAR + TOOL, W, H - BAR - TOOL, TFT_WHITE);
  if (!pageOk) {
    page.setColorDepth(16);
    pageOk = page.createSprite(W, H - BAR - TOOL) != nullptr;
  }
  if (pageOk) page.fillSprite(TFT_WHITE);
  penX = penY = -1;
}
void saveNote() {
  if (!sdOk || !pageOk) return;
  SD_MMC.mkdir("/notes");
  File f = SD_MMC.open("/notes/page" + String(notePage++) + ".raw", FILE_WRITE);
  if (f) { f.write((uint8_t*)page.getPointer(), W * (H - BAR - TOOL) * 2); f.close(); }
  tft.fillRect(170, BAR + 6, 70, 16, TFT_LIGHTGREY);
  tft.setTextColor(TFT_DARKGREEN, TFT_LIGHTGREY); tft.drawString("Saved", 180, BAR + 6, 2);
}

// ---------- Stream: the Pi sends raw RGB565 240x320 frames ----------
void drawStream() { header("Stream"); tft.setTextColor(TFT_WHITE, TFT_BLACK); tft.drawString(wifiOk ? "Tap to start" : "No Wi-Fi", 8, 50, 4); }
void streamFrame() {
  if (!wifiOk) return;
  const size_t need = (size_t)W * H * 2;
  uint8_t* buf = (uint8_t*)ps_malloc(need);
  if (!buf) return;
  HTTPClient http; http.setTimeout(3000);
  http.begin(base() + "/stream/frame");
  if (http.GET() == 200) {
    WiFiClient* s = http.getStreamPtr();
    size_t got = 0; uint32_t t0 = millis();
    while (http.connected() && got < need && millis() - t0 < 3000) got += s->readBytes(buf + got, need - got);
    if (got >= need) tft.pushImage(0, 0, W, H, (uint16_t*)buf);
  }
  http.end(); free(buf);
}

// ---------- Robot ----------
void drawRobot() {
  header("Robot");
  struct { const char* l; int x, y, w, h; uint16_t c; } b[] = {
    {"Fwd", 80, 40, 80, 60, TFT_DARKCYAN}, {"Left", 8, 110, 70, 60, TFT_DARKCYAN}, {"Stop", 85, 110, 70, 60, TFT_RED},
    {"Right", 162, 110, 70, 60, TFT_DARKCYAN}, {"Back", 80, 180, 80, 60, TFT_DARKCYAN}};
  for (auto& x : b) {
    tft.fillRoundRect(x.x, x.y, x.w, x.h, 8, x.c);
    tft.setTextColor(TFT_WHITE, x.c); tft.drawCentreString(x.l, x.x + x.w / 2, x.y + 20, 4);
  }
}

// ---------- Settings ----------
void drawSettings() {
  header("Settings");
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Pi: " + piHost, 8, 40, 2);
  tft.drawString("IP: " + WiFi.localIP().toString(), 8, 62, 2);
  tft.fillRoundRect(8, 100, 224, 36, 6, TFT_ORANGE);
  tft.setTextColor(TFT_BLACK, TFT_ORANGE); tft.drawString("Reset Wi-Fi setup", 20, 110, 2);
}

void go(Screen s) {
  cur = s; streaming = false;
  switch (s) {
    case HOME: drawHome(); break;     case FILES: drawFiles(); break;
    case MUSIC: drawMusic(); break;   case NOTES: drawNotes(); break;
    case STREAM: drawStream(); break; case ROBOT: drawRobot(); break;
    case SETTINGS: drawSettings(); break;
  }
}

void setup() {
  // Power first (LilyGO: GPIO10 for battery, GPIO14 for the 5V connector).
  pinMode(PWR_EN_PIN, OUTPUT); digitalWrite(PWR_EN_PIN, HIGH);
  pinMode(PWR_ON_PIN, OUTPUT); digitalWrite(PWR_ON_PIN, HIGH);
  pinMode(BK_LIGHT_PIN, OUTPUT); digitalWrite(BK_LIGHT_PIN, HIGH);
  pinMode(BUTTON1_PIN, INPUT_PULLUP);
  Serial.begin(115200);
  delay(300);
  Serial.println("T-HMI Hub boot");

  tft.begin(); tft.setRotation(0); tft.setSwapBytes(true);
  tft.fillScreen(TFT_BLACK); tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("T-HMI Hub starting...", 8, 8, 2);
  Serial.println("display ok");

  SPI.begin(TOUCHSCREEN_SCLK_PIN, TOUCHSCREEN_MISO_PIN, TOUCHSCREEN_MOSI_PIN);
  touch.begin(W, H);
  touch.setCal(1788, 285, 1877, 311, W, H);   // LilyGO's default calibration
  touch.setRotation(0);
  Serial.println("touch ok");

  safeMode = digitalRead(BUTTON1_PIN) == LOW;   // hold BOOT while powering on to skip SD and Wi-Fi
  if (safeMode) { tft.drawString("Safe mode: no SD / Wi-Fi", 8, 30, 2); delay(1500); go(HOME); return; }

  SD_MMC.setPins(SD_SCLK_PIN, SD_CMD_PIN, SD_D0_PIN);
  sdOk = SD_MMC.begin("/sdcard", true);
  Serial.println(sdOk ? "sd ok" : "no sd");

  prefs.begin("hub", false);
  piHost = prefs.getString("pi", piHost);
  tft.drawString("On your phone join the", 8, 60, 2);
  tft.drawString("Wi-Fi  THMI-Setup  to", 8, 80, 2);
  tft.drawString("connect this device.", 8, 100, 2);
  WiFiManager wm;
  wm.setConfigPortalTimeout(120);
  wifiOk = wm.autoConnect("THMI-Setup");
  Serial.println(wifiOk ? "wifi ok" : "no wifi");
  go(HOME);
}

void loop() {
  if (streaming) streamFrame();
  if (!touch.pressed()) { penX = penY = -1; delay(10); return; }
  int x = touch.X(), y = touch.Y();
  if (hit(x, y, 196, 0, 44, BAR)) { go(HOME); delay(300); return; }
  switch (cur) {
    case HOME:
      for (auto& b : homeBtns) if (hit(x, y, b.x, b.y, b.w, b.h)) { go(b.target); delay(300); break; }
      break;
    case MUSIC:
      for (int i = 0; i < musicN && i < 10; i++) if (hit(x, y, 0, 34 + i * 24, W, 24)) { playOnPi(musicFiles[i]); delay(300); }
      if (hit(x, y, 8, 288, 100, 26)) piPost("/api/play/stop");
      if (hit(x, y, 122, 288, 110, 26)) piPost("/api/bluetooth/pair");
      break;
    case NOTES:
      if (hit(x, y, 0, BAR, 80, TOOL)) drawNotes();
      else if (hit(x, y, 80, BAR, 80, TOOL)) { saveNote(); delay(300); }
      else if (y >= BAR + TOOL) {
        if (penX >= 0) {
          tft.drawLine(penX, penY, x, y, TFT_BLACK);
          if (pageOk) page.drawLine(penX, penY - BAR - TOOL, x, y - BAR - TOOL, TFT_BLACK);
        }
        penX = x; penY = y;
      }
      break;
    case STREAM: streaming = wifiOk; break;
    case ROBOT:
      if (hit(x, y, 80, 40, 80, 60)) piPost("/api/robot/forward");
      else if (hit(x, y, 8, 110, 70, 60)) piPost("/api/robot/left");
      else if (hit(x, y, 85, 110, 70, 60)) piPost("/api/robot/stop");
      else if (hit(x, y, 162, 110, 70, 60)) piPost("/api/robot/right");
      else if (hit(x, y, 80, 180, 80, 60)) piPost("/api/robot/back");
      delay(120);
      break;
    case SETTINGS:
      if (hit(x, y, 8, 100, 224, 36)) { WiFiManager wm; wm.resetSettings(); ESP.restart(); }
      break;
    default: break;
  }
}
