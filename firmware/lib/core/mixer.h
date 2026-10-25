// キーの押下状態 → 左右モーターの出力（-1〜1）。左右の回転差で曲がる。
#pragma once
#include "protocol.h"

namespace mrc {

struct MotorCmd {
  float left;
  float right;
};

constexpr float TURN_GAIN = 0.5f;  // 旋回の強さ（その場旋回の速さ）

inline float clamp1(float v) { return v > 1 ? 1 : (v < -1 ? -1 : v); }

// maxDuty は速度の上限（0〜1）。LTE で遅延が大きいときは下げる（企画まとめ4章）。
inline MotorCmd mix(uint8_t keys, float maxDuty) {
  float throttle = float((keys & KEY_W) ? 1 : 0) - float((keys & KEY_S) ? 1 : 0);
  float turn = float((keys & KEY_D) ? 1 : 0) - float((keys & KEY_A) ? 1 : 0);
  return {clamp1(throttle + turn * TURN_GAIN) * maxDuty, clamp1(throttle - turn * TURN_GAIN) * maxDuty};
}

}  // namespace mrc
