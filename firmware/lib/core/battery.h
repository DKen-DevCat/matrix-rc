// 電池電圧の監視。3.5V で警告、3.3V で走行とジャンプを止める（設計書①5章・②5章）。
// モーターや LTE の瞬間的な落ち込みで止まらないよう、数百 ms の平均で判定し、ヒステリシスを付ける。
#pragma once
#include <cstdint>

namespace mrc {

class BatteryMonitor {
 public:
  static constexpr int WARN_MV = 3500;
  static constexpr int WARN_CLEAR_MV = 3550;
  static constexpr int CUTOFF_MV = 3300;
  static constexpr int CUTOFF_CLEAR_MV = 3500;
  static constexpr float TAU_MS = 300.0f;  // 平均の時定数

  void update(int mv, uint32_t now) {
    if (!init_) {
      avg_ = float(mv);
      init_ = true;
    } else {
      float dt = float(now - lastMs_);
      float a = dt / (TAU_MS + dt);
      avg_ += a * (float(mv) - avg_);
    }
    lastMs_ = now;
    int v = int(avg_);
    if (v < WARN_MV) warn_ = true;
    else if (v > WARN_CLEAR_MV) warn_ = false;
    if (v < CUTOFF_MV) cutoff_ = true;
    else if (v > CUTOFF_CLEAR_MV) cutoff_ = false;
  }

  int averageMv() const { return int(avg_); }
  bool warn() const { return warn_; }
  bool cutoff() const { return cutoff_; }

 private:
  bool init_ = false;
  float avg_ = 0;
  uint32_t lastMs_ = 0;
  bool warn_ = false;
  bool cutoff_ = false;
};

}  // namespace mrc
