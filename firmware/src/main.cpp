// T-HMI handheld client for the Pi brain.
// Screens: Home, Files (microSD), Music (SD -> Pi -> Bluetooth), Notes (finger drawing),
// Stream (video/games from Pi as MJPEG, touch sent back), Robot, Settings.
#include <Arduino.h>
#include <SD_MMC.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "pins.h"
#include "touch.h"

TFT_eSPI tft;
Preferences prefs;
String piHost = "thmi-hub.local";   // Pi advertises this name; Settings can override
const int PORT = 8765;

enum Screen { HOME, FILES, MUSIC, NOTES, STREAM, ROBOT, SETTINGS };
Screen cur = HOME;
bool sdOk = false;

struct Btn { int x, y, w, h; const char* label; Screen target; };
Btn homeBtns[] = {
  {10, 40, 145, 50, "Files", FILES},  {165, 40, 145, 50, "Music", MUSIC},
  {10, 100, 145, 50, "Notes", NOTES}, {165, 100, 145, 50, "Stream", STREAM},
  {10, 160, 145, 50, "Robot", ROBOT}, {165, 160, 145, 50, "Settings", SETTINGS},
};

String base() { return "http://" + piHost + ":" + String(PORT); }

void header(const char* t) {
  tft.fillScreen(TFT_BLACK);
  tft.fillRect(0, 0, 320, 28, TFT_NAVY);
  tft.setTextColor(TFT_WHITE, TFT_NAVY);
  tft.drawString(t, 8, 6, 4);
  tft.drawString("<", 296, 6, 4);
}

void drawHome() {
  header("T-HMI Hub");
  for (auto& b : homeBtns) {
    tft.fillRoundRect(b.x, b.y, b.w, b.h, 8, TFT_DARKGREEN);
    tft.setTextColor(TFT_WHITE, TFT_DARKGREEN);
    tft.drawCentreString(b.label, b.x + b.w / 2, b.y + 14, 4);
  }
  tft.setTextColor(sdOk ? TFT_GREEN : TFT_RED, TFT_BLACK);
  tft.drawString(sdOk ? "SD ok" : "No SD", 8, 222, 2);
  tft.setTextColor(WiFi.isConnected() ? TFT_GREEN : TFT_RED, TFT_BLACK);
  tft.drawString(WiFi.isConnected() ? "Wi-Fi ok" : "No Wi-Fi", 100, 222, 2);
}

// ---------- Files ----------
void drawFiles() {
  header("Files (SD)");
  if (!sdOk) { tft.drawString("No SD card", 8, 50, 4); return; }
  File root = SD_MMC.open("/");
  int y = 36;
  for (File f = root.openNextFile(); f && y < 220; f = root.openNextFile()) {
    tft.setTextColor(f.isDirectory() ? TFT_YELLOW : TFT_WHITE, TFT_BLACK);
    tft.drawString(String(f.name()) + (f.isDirectory() ? "/" : ""), 8, y, 2);
    y += 18;
  }
}

// ---------- Music: upload SD file to Pi, Pi plays through Bluetooth headphones ----------
String musicFiles[32]; int musicN = 0;
void scanMusic() {
  musicN = 0;
  if (!sdOk) return;
  File root = SD_MMC.open("/");
  for (File f = root.openNextFile(); f && musicN < 32; f = root.openNextFile()) {
    String n = f.name(); n.toLowerCase();
    if (!f.isDirectory() && (n.endsWith(".mp3") || n.endsWith(".wav") || n.endsWith(".flac") || n.endsWith(".ogg")))
      musicFiles[musicN++] = String("/") + f.name();
  }
}
void drawMusic() {
  header("Music -> Pi BT");
  scanMusic();
  for (int i = 0; i < musicN && i < 8; i++) {
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString(musicFiles[i], 8, 36 + i * 22, 2);
  }
  tft.fillRoundRect(8, 215, 70, 22, 4, TFT_RED);   tft.drawString("Stop", 22, 218, 2);
  tft.fillRoundRect(90, 215, 70, 22, 4, TFT_BLUE); tft.drawString("Pair", 104, 218, 2);
}
void playOnPi(const String& path) {
  File f = SD_MMC.open(path);
  if (!f) return;
  HTTPClient http;
  http.begin(base() + "/api/play/upload?name=" + f.name());
  http.sendRequest("POST", &f, f.size());
  http.end(); f.close();
}
void piPost(const String& p) { HTTPClient h; h.begin(base() + p); h.POST(""); h.end(); }

// ---------- Notes: finger drawing, saved to SD ----------
int penX = -1, penY = -1; int page = 0;
void drawNotes() {
  header("Notes");
  tft.fillRect(0, 28, 320, 212, TFT_WHITE);
  tft.setTextColor(TFT_BLACK, TFT_WHITE);
  tft.drawString("Clear", 8, 32, 2);
  tft.drawString("Save", 70, 32, 2);
  penX = penY = -1;
}
void saveNote() {
  if (!sdOk) return;
  SD_MMC.mkdir("/notes");
  File f = SD_MMC.open("/notes/page" + String(page++) + ".raw", FILE_WRITE);
  uint16_t line[320];
  for (int y = 28; y < 240; y++) { tft.readRect(0, y, 320, 1, line); f.write((uint8_t*)line, 640); }
  f.close();
}

// ---------- Stream: Pi sends MJPEG frames; we draw them into PSRAM then push ----------
void drawStream() {
  header("Stream");
  tft.drawString("Tap to start", 8, 50, 4);
}
void streamLoop() {
  HTTPClient http;
  http.begin(base() + "/stream/frame");
  int code = http.GET();
  if (code == 200) {
    int len = http.getSize();
    uint8_t* buf = (uint8_t*)ps_malloc(len > 0 ? len : 40000);
    WiFiClient* s = http.getStreamPtr();
    int got = 0;
    while (http.connected() && got < len) got += s->readBytes(buf + got, len - got);
    // Pi sends raw RGB565 320x240 frames to avoid a JPEG decoder dependency
    if (got >= 320 * 240 * 2) tft.pushImage(0, 0, 320, 240, (uint16_t*)buf);
    free(buf);
  }
  http.end();
}

// ---------- Robot ----------
void drawRobot() {
  header("Robot");
  const char* l[] = {"Fwd", "Back", "Left", "Right", "Stop"};
  int xs[] = {120, 120, 20, 220, 120}, ys[] = {40, 160, 100, 100, 100};
  for (int i = 0; i < 5; i++) {
    tft.fillRoundRect(xs[i], ys[i], 80, 50, 8, i == 4 ? TFT_RED : TFT_DARKCYAN);
    tft.drawCentreString(l[i], xs[i] + 40, ys[i] + 14, 4);
  }
}
void robotCmd(const char* c) { piPost(String("/api/robot/") + c); }

// ---------- Settings ----------
void drawSettings() {
  header("Settings");
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Pi: " + piHost, 8, 40, 2);
  tft.drawString("IP: " + WiFi.localIP().toString(), 8, 62, 2);
  tft.fillRoundRect(8, 100, 200, 30, 6, TFT_ORANGE);
  tft.setTextColor(TFT_BLACK, TFT_ORANGE);
  tft.drawString("Reset Wi-Fi setup", 16, 108, 2);
}

void go(Screen s) {
  cur = s;
  switch (s) {
    case HOME: drawHome(); break; case FILES: drawFiles(); break;
    case MUSIC: drawMusic(); break; case NOTES: drawNotes(); break;
    case STREAM: drawStream(); break; case ROBOT: drawRobot(); break;
    case SETTINGS: drawSettings(); break;
  }
}

void setup() {
  pinMode(PIN_PWR_EN, OUTPUT); digitalWrite(PIN_PWR_EN, HIGH);
  pinMode(PIN_PWR_ON, OUTPUT); digitalWrite(PIN_PWR_ON, HIGH);
  delay(100);
  tft.init(); tft.setRotation(1); tft.setSwapBytes(true);
  pinMode(38, OUTPUT); digitalWrite(38, HIGH);
  tft.fillScreen(TFT_BLACK);
  tft.drawString("Starting...", 8, 8, 4);
  touchBegin();
  SD_MMC.setPins(PIN_SD_CLK, PIN_SD_CMD, PIN_SD_D0);
  sdOk = SD_MMC.begin("/sdcard", true);
  prefs.begin("hub", false);
  piHost = prefs.getString("pi", piHost);
  // Setup page appears on its own: join the "THMI-Setup" Wi-Fi from your phone.
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  tft.drawString("Wi-Fi: join THMI-Setup", 8, 40, 2);
  wm.autoConnect("THMI-Setup");
  go(HOME);
}

bool hit(int x, int y, int bx, int by, int bw, int bh) { return x >= bx && x < bx + bw && y >= by && y < by + bh; }

void loop() {
  int x, y;
  if (!touchPoint(x, y)) { penX = penY = -1; if (cur == STREAM && streaming) streamLoop(); return; }
  if (hit(x, y, 290, 0, 30, 28)) { streaming = false; go(HOME); delay(250); return; }
  switch (cur) {
    case HOME:
      for (auto& b : homeBtns) if (hit(x, y, b.x, b.y, b.w, b.h)) { go(b.target); delay(250); }
      break;
    case MUSIC:
      for (int i = 0; i < musicN && i < 8; i++) if (hit(x, y, 0, 34 + i * 22, 320, 22)) { playOnPi(musicFiles[i]); delay(300); }
      if (hit(x, y, 8, 215, 70, 22)) piPost("/api/play/stop");
      if (hit(x, y, 90, 215, 70, 22)) piPost("/api/bluetooth/pair");
      break;
    case NOTES:
      if (hit(x, y, 0, 28, 60, 24)) drawNotes();
      else if (hit(x, y, 60, 28, 60, 24)) saveNote();
      else if (y > 52) { if (penX >= 0) tft.drawLine(penX, penY, x, y, TFT_BLACK); penX = x; penY = y; }
      break;
    case STREAM: streaming = true; break;
    case ROBOT:
      if (hit(x, y, 120, 40, 80, 50)) robotCmd("forward");
      else if (hit(x, y, 120, 160, 80, 50)) robotCmd("back");
      else if (hit(x, y, 20, 100, 80, 50)) robotCmd("left");
      else if (hit(x, y, 220, 100, 80, 50)) robotCmd("right");
      else if (hit(x, y, 120, 100, 80, 50)) robotCmd("stop");
      delay(150);
      break;
    case SETTINGS:
      if (hit(x, y, 8, 100, 200, 30)) { WiFiManager wm; wm.resetSettings(); ESP.restart(); }
      break;
    default: break;
  }
}
