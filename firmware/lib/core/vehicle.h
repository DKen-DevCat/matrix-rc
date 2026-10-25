// 機体の判断をまとめたもの。ハードの入出力は呼び出し側（src/main.cpp と sim/sim_main.cpp）が受け持つ。
#pragma once
#include "battery.h"
#include "control.h"
#include "jump.h"
#include "mixer.h"
#include "protocol.h"

namespace mrc {

struct Outputs {
  MotorCmd drive;
  bool jumpMotor;
};

class Vehicle {
 public:
  Vehicle(uint8_t deviceId, float maxDuty) : deviceId_(deviceId), maxDuty_(maxDuty), filter_(deviceId) {}

  void onPacket(const uint8_t* buf, size_t len, uint32_t now) {
    Control c;
    if (!decodeControl(buf, len, c)) return;
    uint32_t before = filter_.sessionId();
    AcceptResult r = filter_.accept(c, now);
    if (!r.accepted) return;
    if (filter_.sessionId() != before && jump_.state() == JUMP_FAULT) jump_.abort();  // 接続し直しで異常を解除
    if (r.newJump && !battery_.cutoff()) jump_.request();
  }

  Outputs step(uint32_t now, bool camSwitchPressed, int vbatMv) {
    battery_.update(vbatMv, now);
    bool active = filter_.active(now);
    bool allowed = active && !battery_.cutoff();
    if (!allowed && (jump_.state() == JUMP_CHARGING || jump_.state() == JUMP_FIRING)) jump_.abort();
    bool jumpMotor = jump_.update(now, camSwitchPressed);
    Outputs o{{0, 0}, false};
    if (allowed) {
      o.drive = mix(filter_.keys(now), maxDuty_);
      o.jumpMotor = jumpMotor;
    }
    stopped_ = !active;
    return o;
  }

  Telemetry telemetry(uint32_t now, int8_t rssi, bool cameraOn) const {
    Telemetry t{};
    t.deviceId = deviceId_;
    t.sessionId = filter_.sessionId();
    t.seq = filter_.lastSeq();
    t.sentAt = filter_.lastSentAt();
    t.vbatMv = uint16_t(battery_.averageMv());
    t.flags = (stopped_ ? FLAG_STOPPED : 0) | (jump_.charged() ? FLAG_CHARGED : 0) |
              (battery_.warn() ? FLAG_LOW_BATT_WARN : 0) | (battery_.cutoff() ? FLAG_LOW_BATT_CUTOFF : 0) |
              (jump_.state() == JUMP_FAULT ? FLAG_JUMP_FAULT : 0) | (cameraOn ? FLAG_CAMERA_ON : 0);
    t.rssi = rssi;
    t.lastJumpId = filter_.lastJumpId();
    t.jumpState = jump_.state();
    uint32_t hold = filter_.msSinceAccept(now);
    t.holdMs = uint8_t(hold > 255 ? 255 : hold);
    t.uptimeMs = now;
    return t;
  }

  bool stopped() const { return stopped_; }
  const BatteryMonitor& battery() const { return battery_; }

 private:
  uint8_t deviceId_;
  float maxDuty_;
  ControlFilter filter_;
  JumpMachine jump_;
  BatteryMonitor battery_;
  bool stopped_ = true;
};

}  // namespace mrc
