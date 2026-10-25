// 操作パケットの受け付け規則と、300ms 途絶えたときの停止（docs/protocol.md「機体の受け付け規則」）。
#pragma once
#include "protocol.h"

namespace mrc {

constexpr uint32_t FAILSAFE_MS = 300;

struct AcceptResult {
  bool accepted;
  bool newJump;  // 前回と違う 0 以外のジャンプID（1 回だけ実行する）
};

class ControlFilter {
 public:
  explicit ControlFilter(uint8_t deviceId) : deviceId_(deviceId) {}

  AcceptResult accept(const Control& c, uint32_t now) {
    if (c.deviceId != deviceId_ || c.sessionId == 0) return {false, false};
    if (hasSession_ && c.sessionId == sessionId_) {
      if (int32_t(c.seq - seq_) <= 0) return {false, false};
    } else {
      // 別のセッションは停止中のときだけ受け入れる（走行中の割り込みを防ぐ）
      if (hasSession_ && active(now)) return {false, false};
      hasSession_ = true;
      sessionId_ = c.sessionId;
      lastJumpId_ = 0;
    }
    seq_ = c.seq;
    sentAt_ = c.sentAt;
    keys_ = c.keys;
    lastAcceptMs_ = now;
    hasAccepted_ = true;
    bool newJump = c.jumpId != 0 && c.jumpId != lastJumpId_;
    if (newJump) lastJumpId_ = c.jumpId;
    return {true, newJump};
  }

  bool active(uint32_t now) const { return hasAccepted_ && now - lastAcceptMs_ < FAILSAFE_MS; }
  uint8_t keys(uint32_t now) const { return active(now) ? keys_ : 0; }
  uint32_t sessionId() const { return sessionId_; }
  uint32_t lastSeq() const { return seq_; }
  uint32_t lastSentAt() const { return sentAt_; }
  uint16_t lastJumpId() const { return lastJumpId_; }
  uint32_t msSinceAccept(uint32_t now) const { return hasAccepted_ ? now - lastAcceptMs_ : 0; }

 private:
  uint8_t deviceId_;
  bool hasSession_ = false;
  bool hasAccepted_ = false;
  uint32_t sessionId_ = 0;
  uint32_t seq_ = 0;
  uint32_t sentAt_ = 0;
  uint8_t keys_ = 0;
  uint16_t lastJumpId_ = 0;
  uint32_t lastAcceptMs_ = 0;
};

}  // namespace mrc
