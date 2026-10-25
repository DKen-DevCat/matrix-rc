// 機体のファームウェア（Phase 1-a：Wi-Fi モデル）。設計書① 4〜6章。
// 判断（受け付け規則・300ms 停止・モーター配分・ジャンプ・電池）は lib/core の Vehicle に任せ、
// ここではハードの入出力と送受信だけを行う。
#include <Arduino.h>
#include <WiFi.h>
#include <driver/i2s.h>
#include <esp_camera.h>
#include <lwip/sockets.h>

#include <utility>

#include "secrets.h"
#include "vehicle.h"

using namespace mrc;

static_assert(sizeof(MRC_TOKEN) - 1 >= 8 && sizeof(MRC_TOKEN) - 1 <= TOKEN_LEN, "MRC_TOKEN は 8〜16 バイト");

// ---- ピン（設計書① 4章。全モデル共通）----
constexpr int PIN_VBAT = 1;     // D0  電池電圧（100kΩ×2 で半分に分圧）
constexpr int PIN_AIN1 = 2;     // D1  DRV8833 左モーター
constexpr int PIN_AIN2 = 3;     // D2
constexpr int PIN_BIN1 = 4;     // D3  DRV8833 右モーター
constexpr int PIN_BIN2 = 5;     // D4
constexpr int PIN_JUMP = 6;     // D5  ジャンプ用モーターの MOSFET
// D6(43)/D7(44) は LTE、D8(7) は GPS 用に予約（Phase 1-b）
constexpr int PIN_CAM_SW = 8;   // D9  カム位置スイッチ（押されると GND）
constexpr int PIN_LED = 9;      // D10 WS2812B（330Ω 直列）

// ---- 調整値 ----
constexpr float MAX_DUTY = 0.8f;          // 速度の上限
constexpr int PWM_FREQ = 20000;           // 可聴域の外にしてモーターのうなりを減らす
constexpr int PWM_BITS = 10;
// LEDC のチャンネル 0 はカメラの XCLK が使う（タイマー 0）。モーターは 2〜5（タイマー 1・2）を使う。
constexpr int CH_AIN1 = 2, CH_AIN2 = 3, CH_BIN1 = 4, CH_BIN2 = 5;
constexpr uint32_t STEP_MS = 10;          // 制御の周期（100Hz）
constexpr uint32_t TELEMETRY_MS = 100;    // 10Hz
constexpr uint32_t HELLO_MS = 1000;
constexpr uint32_t FRAME_MIN_MS = 66;     // 映像は最大 15fps
constexpr int MIC_GAIN = 4;               // PDM マイクの音が小さいので持ち上げる
constexpr int AUDIO_SAMPLES = CHUNK_MAX / 2;  // 120 サンプル＝7.5ms

static Vehicle car(DEVICE_ID, MAX_DUTY);
static int sock = -1;
static sockaddr_in server{};
static SemaphoreHandle_t sendLock;
static volatile bool cameraOn = false;

// ---- 送受信 ----

static void sendPacket(const uint8_t* b, size_t n) {
  xSemaphoreTake(sendLock, portMAX_DELAY);
  // 映像の断片を続けて送ると送信待ちがあふれることがある。少し待って 1 回だけやり直す。
  if (sendto(sock, b, n, 0, (sockaddr*)&server, sizeof server) < 0 && errno == ENOMEM) {
    vTaskDelay(1);
    sendto(sock, b, n, 0, (sockaddr*)&server, sizeof server);
  }
  xSemaphoreGive(sendLock);
}

static void receivePackets(uint32_t now) {
  uint8_t buf[64];
  sockaddr_in from{};
  socklen_t fl = sizeof from;
  int n;
  while ((n = recvfrom(sock, buf, sizeof buf, MSG_DONTWAIT, (sockaddr*)&from, &fl)) > 0) {
    // サーバ以外からのパケットは捨てる（機体は外からの接続を受け付けない）
    if (from.sin_addr.s_addr != server.sin_addr.s_addr || from.sin_port != server.sin_port) continue;
    car.onPacket(buf, size_t(n), now);
  }
}

// ---- モーター ----

static void driveOne(int ch1, int ch2, float v) {
  int duty = int(fabsf(v) * ((1 << PWM_BITS) - 1));
  // DRV8833：IN1 に PWM・IN2 を LOW で正転、逆にすると逆転、両方 LOW で惰性停止
  ledcWrite(ch1, v > 0 ? duty : 0);
  ledcWrite(ch2, v < 0 ? duty : 0);
}

static void setupMotors() {
  const std::pair<int, int> pwm[] = {{PIN_AIN1, CH_AIN1}, {PIN_AIN2, CH_AIN2}, {PIN_BIN1, CH_BIN1}, {PIN_BIN2, CH_BIN2}};
  for (auto [pin, ch] : pwm) {
    ledcSetup(ch, PWM_FREQ, PWM_BITS);
    ledcAttachPin(pin, ch);
    ledcWrite(ch, 0);
  }
  pinMode(PIN_JUMP, OUTPUT);
  digitalWrite(PIN_JUMP, LOW);
}

// ブザーの代わりに走行モーターを可聴域の周波数で短く鳴らす（車輪はほとんど動かない程度の出力）
static void motorBeep(int freq, int ms) {
  for (int ch : {CH_AIN1, CH_BIN1}) ledcSetup(ch, freq, PWM_BITS);
  ledcWrite(CH_AIN1, 80);
  ledcWrite(CH_BIN1, 80);
  delay(ms);
  ledcWrite(CH_AIN1, 0);
  ledcWrite(CH_BIN1, 0);
  for (int ch : {CH_AIN1, CH_BIN1}) ledcSetup(ch, PWM_FREQ, PWM_BITS);
}

// ---- LED（点いている間は撮影中。色で状態を示す）----

static void showLed(uint32_t now) {
  const Telemetry t = car.telemetry(now, 0, cameraOn);
  bool blink = (now / 250) % 2;
  uint8_t r = 0, g = 0, b = 0;
  if (WiFi.status() != WL_CONNECTED) { r = 40; g = 30; }                    // 黄：Wi-Fi 接続待ち
  else if (t.flags & FLAG_LOW_BATT_CUTOFF) { r = blink ? 60 : 0; }          // 赤の点滅：低電圧で停止
  else if (t.flags & FLAG_JUMP_FAULT) { r = 60; b = blink ? 40 : 0; }       // 赤紫：ジャンプ機構の異常
  else if (t.flags & FLAG_LOW_BATT_WARN) { r = 60; g = 20; }                // 橙：電池残量に注意
  else if (t.flags & FLAG_STOPPED) { g = 30; }                              // 緑：待機中
  else { g = 30; b = 50; }                                                  // 水色：操作中
  if (!cameraOn && !(r || g || b)) b = 10;
  neopixelWrite(PIN_LED, r, g, b);
}

// ---- カメラ（XIAO ESP32S3 Sense の配線。基板内で固定）----

static bool setupCamera() {
  camera_config_t c{};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 15; c.pin_d1 = 17; c.pin_d2 = 18; c.pin_d3 = 16;
  c.pin_d4 = 14; c.pin_d5 = 12; c.pin_d6 = 11; c.pin_d7 = 48;
  c.pin_xclk = 10; c.pin_pclk = 13; c.pin_vsync = 38; c.pin_href = 47;
  c.pin_sccb_sda = 40; c.pin_sccb_scl = 39;
  c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_QVGA;  // 320×240
  c.jpeg_quality = 14;            // 数字が大きいほど軽い。1 フレーム 5〜10KB 程度
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;  // 古いフレームを溜めない
  return esp_camera_init(&c) == ESP_OK;
}

static void videoTask(void*) {
  uint16_t frameId = 0;
  uint8_t pkt[CHUNK_HEADER_LEN + CHUNK_MAX];
  uint32_t last = 0;
  for (;;) {
    uint32_t wait = FRAME_MIN_MS - min<uint32_t>(FRAME_MIN_MS, millis() - last);
    if (wait) vTaskDelay(pdMS_TO_TICKS(wait));
    last = millis();
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) continue;
    if (WiFi.status() == WL_CONNECTED && fb->len > 0 && fb->len <= 255 * CHUNK_MAX) {
      uint8_t count = chunkCount(fb->len);
      for (uint8_t i = 0; i < count; i++) {
        size_t off = size_t(i) * CHUNK_MAX;
        size_t len = min(CHUNK_MAX, fb->len - off);
        sendPacket(pkt, encodeVideoChunk(DEVICE_ID, frameId, i, count, fb->buf + off, len, pkt));
      }
      frameId++;
    }
    esp_camera_fb_return(fb);
  }
}

// ---- マイク（PDM。CLK=GPIO42、DATA=GPIO41）。録音はしない。送るだけ ----

static bool setupMic() {
  i2s_config_t cfg{};
  cfg.mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM);
  cfg.sample_rate = 16000;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;  // 無音なら ONLY_RIGHT に替えて試す
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.dma_buf_count = 4;
  cfg.dma_buf_len = AUDIO_SAMPLES;
  if (i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr) != ESP_OK) return false;
  i2s_pin_config_t pins{};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = I2S_PIN_NO_CHANGE;
  pins.ws_io_num = 42;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = 41;
  return i2s_set_pin(I2S_NUM_0, &pins) == ESP_OK;
}

static void audioTask(void*) {
  int16_t pcm[AUDIO_SAMPLES];
  uint8_t pkt[CHUNK_HEADER_LEN + CHUNK_MAX];
  uint16_t seq = 0;
  for (;;) {
    size_t got = 0;
    i2s_read(I2S_NUM_0, pcm, sizeof pcm, &got, portMAX_DELAY);
    size_t n = got / 2;
    for (size_t i = 0; i < n; i++) pcm[i] = int16_t(constrain(int32_t(pcm[i]) * MIC_GAIN, -32768, 32767));
    if (n && WiFi.status() == WL_CONNECTED) sendPacket(pkt, encodeAudio(DEVICE_ID, seq++, pcm, n, pkt));
  }
}

// ---- 起動と制御ループ ----

void setup() {
  Serial.begin(115200);
  setupMotors();
  pinMode(PIN_CAM_SW, INPUT_PULLUP);
  neopixelWrite(PIN_LED, 0, 0, 40);
  sendLock = xSemaphoreCreateMutex();

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // 省電力の待ちで遅延が数十〜数百 ms 増えるのを避ける
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  sock = socket(AF_INET, SOCK_DGRAM, 0);
  server.sin_family = AF_INET;
  server.sin_port = htons(SERVER_PORT);
  inet_pton(AF_INET, SERVER_IP, &server.sin_addr);

  cameraOn = setupCamera();
  if (cameraOn) xTaskCreatePinnedToCore(videoTask, "video", 6144, nullptr, 2, nullptr, 0);
  else Serial.println("カメラの初期化に失敗");
  if (setupMic()) xTaskCreatePinnedToCore(audioTask, "audio", 4096, nullptr, 3, nullptr, 0);
  else Serial.println("マイクの初期化に失敗");

  motorBeep(2000, 120);
  motorBeep(2600, 120);
}

void loop() {
  static uint32_t lastStep = 0, lastTelem = 0, lastHello = 0;
  uint32_t now = millis();
  receivePackets(now);

  if (now - lastStep >= STEP_MS) {
    lastStep = now;
    int vbat = analogReadMilliVolts(PIN_VBAT) * 2;
    Outputs o = car.step(now, digitalRead(PIN_CAM_SW) == LOW, vbat);
    driveOne(CH_AIN1, CH_AIN2, o.drive.left);
    driveOne(CH_BIN1, CH_BIN2, o.drive.right);
    digitalWrite(PIN_JUMP, o.jumpMotor ? HIGH : LOW);
    showLed(now);
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (now - lastHello >= HELLO_MS) {
      lastHello = now;
      uint8_t b[HELLO_LEN];
      sendPacket(b, encodeHello(DEVICE_ID, MRC_TOKEN, b));
    }
    if (now - lastTelem >= TELEMETRY_MS) {
      lastTelem = now;
      uint8_t b[TELEMETRY_LEN];
      sendPacket(b, encodeTelemetry(car.telemetry(now, int8_t(WiFi.RSSI()), cameraOn), b));
    }
  }
  delay(1);
}
