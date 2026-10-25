#include "check.h"
#include "protocol.h"
#include "control.h"
#include "mixer.h"
#include "jump.h"
#include "battery.h"
#include "vehicle.h"

using namespace mrc;

// ---- プロトコル（docs/protocol.md のテストベクタ。web/js/protocol.js のテストと同じ値）----

TEST(control_decodes_test_vector) {
  const uint8_t v[] = {0x4d,0x01,0x01,0x01,0x44,0x33,0x22,0x11,0x07,0x00,0x00,0x00,0xe8,0x03,0x00,0x00,0x09,0x00,0x03,0x00};
  Control c;
  CHECK(decodeControl(v, sizeof v, c));
  CHECK_EQ(c.deviceId, 1);
  CHECK_EQ(c.sessionId, 0x11223344u);
  CHECK_EQ(c.seq, 7u);
  CHECK_EQ(c.sentAt, 1000u);
  CHECK_EQ(c.keys, KEY_W | KEY_D);
  CHECK_EQ(c.jumpId, 3);
}

TEST(control_rejects_broken_packets) {
  uint8_t v[] = {0x4d,0x01,0x01,0x01,0x44,0x33,0x22,0x11,0x07,0x00,0x00,0x00,0xe8,0x03,0x00,0x00,0x09,0x00,0x03,0x00};
  Control c;
  CHECK(!decodeControl(v, 19, c));
  v[0] = 0; CHECK(!decodeControl(v, sizeof v, c)); v[0] = 0x4d;
  v[1] = 2; CHECK(!decodeControl(v, sizeof v, c)); v[1] = 1;
  v[2] = TYPE_TELEMETRY; CHECK(!decodeControl(v, sizeof v, c));
}

TEST(telemetry_layout_matches_spec) {
  Telemetry t{};
  t.deviceId = 1; t.sessionId = 0x11223344; t.seq = 7; t.sentAt = 1000;
  t.vbatMv = 3912; t.flags = FLAG_CHARGED; t.rssi = -61; t.lastJumpId = 3; t.jumpState = 2; t.holdMs = 17; t.uptimeMs = 0x01020304;
  uint8_t b[TELEMETRY_LEN];
  CHECK_EQ(encodeTelemetry(t, b), TELEMETRY_LEN);
  CHECK_EQ(b[0], 0x4d); CHECK_EQ(b[2], TYPE_TELEMETRY);
  CHECK_EQ(b[4], 0x44); CHECK_EQ(b[7], 0x11);
  CHECK_EQ(b[16] | (b[17] << 8), 3912);
  CHECK_EQ((int8_t)b[19], -61);
  CHECK_EQ(b[23], 17);
  CHECK_EQ(b[24], 0x04); CHECK_EQ(b[27], 0x01);
}

TEST(hello_pads_token) {
  uint8_t b[HELLO_LEN];
  CHECK_EQ(encodeHello(3, "abc", b), HELLO_LEN);
  CHECK_EQ(b[2], TYPE_HELLO); CHECK_EQ(b[3], 3);
  CHECK_EQ(b[4], 'a'); CHECK_EQ(b[6], 'c'); CHECK_EQ(b[7], 0); CHECK_EQ(b[19], 0);
}

TEST(video_chunk_header) {
  uint8_t jpeg[500]; for (int i = 0; i < 500; i++) jpeg[i] = i & 0xff;
  uint8_t b[CHUNK_HEADER_LEN + CHUNK_MAX];
  CHECK_EQ(chunkCount(500), 3);
  size_t n = encodeVideoChunk(1, 0xabcd, 2, 3, jpeg + 480, 20, b);
  CHECK_EQ(n, CHUNK_HEADER_LEN + 20);
  CHECK_EQ(b[2], TYPE_VIDEO); CHECK_EQ(b[4], 0xcd); CHECK_EQ(b[5], 0xab);
  CHECK_EQ(b[6], 2); CHECK_EQ(b[7], 3); CHECK_EQ(b[8], 480 & 0xff);
}

// ---- 受け付け規則と 300ms 停止 ----

static Control ctl(uint32_t session, uint32_t seq, uint8_t keys = KEY_W, uint16_t jump = 0) {
  Control c{}; c.deviceId = 1; c.sessionId = session; c.seq = seq; c.keys = keys; c.jumpId = jump; return c;
}

TEST(filter_accepts_only_newer_seq_in_same_session) {
  ControlFilter f(1);
  CHECK(f.accept(ctl(5, 10), 0).accepted);
  CHECK(!f.accept(ctl(5, 10), 1).accepted);  // 重複
  CHECK(!f.accept(ctl(5, 9), 2).accepted);   // 古い
  CHECK(f.accept(ctl(5, 11), 3).accepted);
  CHECK_EQ(f.lastSeq(), 11u);
}

TEST(filter_rejects_other_device_id) {
  ControlFilter f(1);
  Control c = ctl(5, 1); c.deviceId = 2;
  CHECK(!f.accept(c, 0).accepted);
}

TEST(filter_stops_after_300ms_without_valid_packet) {
  ControlFilter f(1);
  f.accept(ctl(5, 1), 1000);
  CHECK(f.active(1299));
  CHECK(!f.active(1300));
  // 古いパケットや重複では延命しない
  f.accept(ctl(5, 1), 1200);
  CHECK(!f.active(1300));
}

TEST(filter_new_session_only_while_stopped) {
  ControlFilter f(1);
  f.accept(ctl(5, 100), 0);
  CHECK(!f.accept(ctl(6, 1), 100).accepted);  // 走行中は割り込めない
  CHECK(f.accept(ctl(6, 1), 400).accepted);   // 停止後なら切り替わる（再読込で seq が巻き戻っても動く）
  CHECK_EQ(f.sessionId(), 6u);
  CHECK(!f.accept(ctl(5, 101), 410).accepted);  // 古いセッションは受け付けない
}

TEST(filter_session_zero_is_invalid) {
  ControlFilter f(1);
  CHECK(!f.accept(ctl(0, 1), 0).accepted);
}

TEST(jump_fires_once_per_id) {
  ControlFilter f(1);
  CHECK(!f.accept(ctl(5, 1, 0, 0), 0).newJump);
  CHECK(f.accept(ctl(5, 2, 0, 1), 20).newJump);
  CHECK(!f.accept(ctl(5, 3, 0, 1), 40).newJump);  // 同じIDの再送では跳ばない
  CHECK(f.accept(ctl(5, 4, 0, 2), 60).newJump);
  CHECK_EQ(f.lastJumpId(), 2);
}

TEST(jump_id_resets_with_session) {
  ControlFilter f(1);
  f.accept(ctl(5, 1, 0, 7), 0);
  // 新しいセッションの最初のパケットが前と同じジャンプIDでも、そのセッションでは初めてなので実行する
  CHECK(f.accept(ctl(6, 1, 0, 7), 400).newJump);
}

TEST(seq_wraparound_is_newer) {
  ControlFilter f(1);
  f.accept(ctl(5, 0xffffffffu), 0);
  CHECK(f.accept(ctl(5, 0), 20).accepted);
}

// ---- モーター配分 ----

TEST(mixer_forward_back_spin) {
  MotorCmd m = mix(KEY_W, 1.0f);
  CHECK_NEAR(m.left, 1); CHECK_NEAR(m.right, 1);
  m = mix(KEY_S, 1.0f);
  CHECK_NEAR(m.left, -1); CHECK_NEAR(m.right, -1);
  m = mix(KEY_D, 1.0f);  // その場で右旋回
  CHECK_NEAR(m.left, 0.5); CHECK_NEAR(m.right, -0.5);
  m = mix(KEY_A, 1.0f);
  CHECK_NEAR(m.left, -0.5); CHECK_NEAR(m.right, 0.5);
}

TEST(mixer_curve_and_limits) {
  MotorCmd m = mix(KEY_W | KEY_D, 1.0f);  // 前進しながら右へ
  CHECK_NEAR(m.left, 1); CHECK_NEAR(m.right, 0.5);
  m = mix(KEY_W | KEY_S, 1.0f);  // 打ち消し
  CHECK_NEAR(m.left, 0); CHECK_NEAR(m.right, 0);
  m = mix(KEY_W, 0.6f);  // 速度の上限
  CHECK_NEAR(m.left, 0.6); CHECK_NEAR(m.right, 0.6);
  m = mix(KEY_SPACE, 1.0f);  // Space は走行に関係しない
  CHECK_NEAR(m.left, 0); CHECK_NEAR(m.right, 0);
}

// ---- ジャンプ（渦巻きカム）----
// カム位置スイッチは「ばねが縮みきった（チャージ済み）」ときに押される。

TEST(jump_charges_when_requested_from_unknown) {
  JumpMachine j;
  CHECK(!j.update(0, false));
  CHECK_EQ(j.state(), JUMP_UNKNOWN);
  j.request();
  CHECK(j.update(10, false));            // チャージのためにモーターを回す
  CHECK_EQ(j.state(), JUMP_CHARGING);
  CHECK(j.update(2000, true));           // スイッチが押されても、安定するまでは回す
  CHECK(!j.update(2000 + JumpMachine::DEBOUNCE_MS, true));
  CHECK_EQ(j.state(), JUMP_CHARGED);
}

TEST(jump_from_charged_releases_and_recharges) {
  JumpMachine j;
  j.update(0, true); j.update(JumpMachine::DEBOUNCE_MS, true);
  CHECK_EQ(j.state(), JUMP_CHARGED);
  j.request();
  CHECK(j.update(110, true));
  CHECK_EQ(j.state(), JUMP_FIRING);
  CHECK(j.update(200, false));           // カムの段差を越えてばねが開放された
  CHECK(j.update(200 + JumpMachine::DEBOUNCE_MS, false));
  CHECK_EQ(j.state(), JUMP_CHARGING);    // 続けて次のチャージへ（1回転）
  CHECK(j.update(3000, true));
  CHECK(!j.update(3000 + JumpMachine::DEBOUNCE_MS, true));
  CHECK_EQ(j.state(), JUMP_CHARGED);
}

TEST(jump_ignores_switch_bounce) {
  JumpMachine j;
  j.update(0, true); j.update(JumpMachine::DEBOUNCE_MS, true);
  j.request();
  j.update(110, true);
  j.update(120, false);   // チャタリング
  j.update(125, true);
  j.update(130, false);
  CHECK_EQ(j.state(), JUMP_FIRING);
}

TEST(jump_fault_on_timeout) {
  JumpMachine j;
  j.request();
  j.update(0, false);
  CHECK(j.update(JumpMachine::CHARGE_TIMEOUT_MS - 1, false));
  CHECK(!j.update(JumpMachine::CHARGE_TIMEOUT_MS, false));  // スイッチが反応しない → 止めて異常
  CHECK_EQ(j.state(), JUMP_FAULT);
  j.request();                      // 異常のあいだは回さない
  CHECK(!j.update(10010, false));
}

TEST(jump_release_timeout_is_fault) {
  JumpMachine j;
  j.update(0, true); j.update(JumpMachine::DEBOUNCE_MS, true);
  j.request();
  j.update(100, true);
  CHECK(!j.update(100 + JumpMachine::RELEASE_TIMEOUT_MS, true));  // カムが空回り・引っかかり
  CHECK_EQ(j.state(), JUMP_FAULT);
}

TEST(jump_abort_stops_motor) {
  JumpMachine j;
  j.request();
  CHECK(j.update(10, false));
  j.abort();
  CHECK(!j.update(20, false));
  CHECK_EQ(j.state(), JUMP_UNKNOWN);
}

TEST(jump_request_while_busy_is_ignored) {
  JumpMachine j;
  j.request();
  j.update(10, false);
  j.request();  // チャージ中の再要求は無視（溜めの最中は跳ばない）
  j.update(2000, true); j.update(2000 + JumpMachine::DEBOUNCE_MS, true);
  CHECK_EQ(j.state(), JUMP_CHARGED);
}

// ---- 電池 ----

TEST(battery_warn_and_cutoff_with_hysteresis) {
  BatteryMonitor b;
  uint32_t t = 0;
  auto feed = [&](int mv, int ms) { for (int i = 0; i < ms; i += 10) b.update(mv, t += 10); };
  feed(3900, 1000);
  CHECK(!b.warn()); CHECK(!b.cutoff());
  feed(3450, 2000);
  CHECK(b.warn()); CHECK(!b.cutoff());
  feed(3250, 2000);
  CHECK(b.cutoff());
  feed(3400, 2000);  // 少し戻っただけでは解除しない
  CHECK(b.cutoff());
  feed(3600, 3000);
  CHECK(!b.cutoff()); CHECK(!b.warn());
}

TEST(battery_ignores_short_dips) {
  BatteryMonitor b;
  uint32_t t = 0;
  for (int i = 0; i < 100; i++) b.update(3900, t += 10);
  for (int i = 0; i < 5; i++) b.update(3000, t += 10);  // モーター起動時の 50ms の落ち込み
  CHECK(!b.cutoff());
}

// ---- 組み立て（Vehicle）----

static void send(Vehicle& v, uint32_t session, uint32_t seq, uint8_t keys, uint16_t jump, uint32_t now) {
  const uint8_t b[] = {0x4d, 1, TYPE_CONTROL, 1,
    uint8_t(session), uint8_t(session >> 8), uint8_t(session >> 16), uint8_t(session >> 24),
    uint8_t(seq), uint8_t(seq >> 8), uint8_t(seq >> 16), uint8_t(seq >> 24),
    uint8_t(now), uint8_t(now >> 8), 0, 0, keys, 0, uint8_t(jump), uint8_t(jump >> 8)};
  v.onPacket(b, sizeof b, now);
}

TEST(vehicle_drives_then_stops_after_300ms) {
  Vehicle v(1, 0.8f);
  send(v, 5, 1, KEY_W, 0, 1000);
  Outputs o = v.step(1010, false, 3900);
  CHECK_NEAR(o.drive.left, 0.8);
  o = v.step(1300, false, 3900);
  CHECK_NEAR(o.drive.left, 0); CHECK_NEAR(o.drive.right, 0);
  CHECK(v.telemetry(1300, -50, true).flags & FLAG_STOPPED);
}

TEST(vehicle_ignores_garbage) {
  Vehicle v(1, 1.0f);
  const uint8_t junk[] = {1, 2, 3};
  v.onPacket(junk, sizeof junk, 0);
  CHECK_NEAR(v.step(10, false, 3900).drive.left, 0);
}

TEST(vehicle_jump_runs_motor_once) {
  Vehicle v(1, 1.0f);
  uint32_t t = 0;
  send(v, 5, 1, 0, 0, t);
  v.step(t, true, 3900); v.step(t += 30, true, 3900);  // 起動時からチャージ済み
  send(v, 5, 2, KEY_SPACE, 1, t += 10);
  CHECK(v.step(t, true, 3900).jumpMotor);
  send(v, 5, 3, KEY_SPACE, 1, t += 10);  // 同じジャンプIDの再送
  v.step(t, false, 3900); v.step(t += 30, false, 3900);  // 開放
  for (int i = 0; i < 10; i++) { send(v, 5, 4 + i, 0, 1, t += 20); v.step(t, false, 3900); }
  v.step(t, true, 3900); 
  send(v, 5, 20, 0, 1, t += 25);
  CHECK(!v.step(t, true, 3900).jumpMotor);  // 再チャージで止まる。再送では次のジャンプをしない
  CHECK_EQ(v.telemetry(t, 0, true).lastJumpId, 1);
  CHECK(v.telemetry(t, 0, true).flags & FLAG_CHARGED);
}

TEST(vehicle_stops_jump_motor_when_link_lost) {
  Vehicle v(1, 1.0f);
  send(v, 5, 1, 0, 1, 0);
  CHECK(v.step(10, false, 3900).jumpMotor);  // チャージ開始
  CHECK(!v.step(400, false, 3900).jumpMotor);
}

TEST(vehicle_low_battery_cuts_drive_and_jump) {
  Vehicle v(1, 1.0f);
  uint32_t t = 0;
  for (uint32_t i = 1; i < 200; i++) { send(v, 5, i, KEY_W, 0, t); v.step(t, false, 3200); t += 10; }
  send(v, 5, 300, KEY_W, 1, t);
  Outputs o = v.step(t, false, 3200);
  CHECK_NEAR(o.drive.left, 0);
  CHECK(!o.jumpMotor);
  CHECK(v.telemetry(t, 0, true).flags & FLAG_LOW_BATT_CUTOFF);
}

TEST(vehicle_telemetry_echoes_last_accepted) {
  Vehicle v(1, 1.0f);
  send(v, 0x11223344, 7, KEY_W, 0, 1234);
  Telemetry tm = v.telemetry(1240, -61, true);
  CHECK_EQ(tm.sessionId, 0x11223344u);
  CHECK_EQ(tm.seq, 7u);
  CHECK_EQ(tm.sentAt, 1234u & 0xffff);
  CHECK_EQ(tm.rssi, -61);
  CHECK_EQ(tm.holdMs, 6);  // 1234 に受け取り、1240 に送る
  CHECK_EQ(v.telemetry(1234 + 1000, 0, true).holdMs, 255);
  CHECK(tm.flags & FLAG_CAMERA_ON);
}

TEST(vehicle_new_session_clears_jump_fault) {
  Vehicle v(1, 1.0f);
  send(v, 5, 1, 0, 1, 0);
  uint32_t t = 0;
  for (; t < JumpMachine::CHARGE_TIMEOUT_MS + 100; t += 50) { send(v, 5, 2 + t, 0, 1, t); v.step(t, false, 3900); }
  CHECK(v.telemetry(t, 0, true).flags & FLAG_JUMP_FAULT);
  t += 400;
  send(v, 6, 1, 0, 0, t);
  v.step(t, false, 3900);
  CHECK(!(v.telemetry(t, 0, true).flags & FLAG_JUMP_FAULT));
}

int main() { return runAll(); }
