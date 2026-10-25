// ジャンプ機構（渦巻きカム）の状態遷移。設計書② 7章／C4。
// 高減速 N20 でカムを一方向に回してばねを縮め、カムの段差で一気に開放する。
// カム位置スイッチは「ばねが縮みきった（チャージ済み）」位置で押される。
//   不明 ──要求──▶ チャージ中 ──押された──▶ チャージ済み
//   チャージ済み ──要求──▶ 発射中 ──離れた（開放）──▶ チャージ中 ──押された──▶ チャージ済み（1回転）
// どの区間も時間切れなら止めて異常にする（スイッチ外れ・カムの引っかかり・電池切れでモーターを焼かない）。
#pragma once
#include <cstdint>

namespace mrc {

enum JumpState : uint8_t { JUMP_UNKNOWN = 0, JUMP_CHARGING = 1, JUMP_CHARGED = 2, JUMP_FIRING = 3, JUMP_FAULT = 4 };

class JumpMachine {
 public:
  static constexpr uint32_t DEBOUNCE_MS = 20;
  static constexpr uint32_t CHARGE_TIMEOUT_MS = 6000;  // チャージは約3〜4秒の見込み
  static constexpr uint32_t RELEASE_TIMEOUT_MS = 1500;

  void request() { requested_ = true; }


  // 異常からの復帰や通信途絶時に止める。位置は分からなくなるので「不明」に戻す。
  void abort() {
    state_ = JUMP_UNKNOWN;
    requested_ = false;
  }

  // 戻り値：ジャンプ用モーターを回すか
  bool update(uint32_t now, bool switchRaw) {
    debounce(now, switchRaw);
    switch (state_) {
      case JUMP_UNKNOWN:
        if (stableValid_ && pressed_) {
          state_ = JUMP_CHARGED;
        } else if (takeRequest()) {
          enter(JUMP_CHARGING, now);
        }
        break;
      case JUMP_CHARGED:
        if (stableValid_ && !pressed_) {
          state_ = JUMP_UNKNOWN;  // 手で動かされた等
        } else if (takeRequest()) {
          enter(JUMP_FIRING, now);
        }
        break;
      case JUMP_FIRING:
        if (stableValid_ && !pressed_) enter(JUMP_CHARGING, now);
        else if (now - enteredMs_ >= RELEASE_TIMEOUT_MS) state_ = JUMP_FAULT;
        break;
      case JUMP_CHARGING:
        if (stableValid_ && pressed_ && pressedSince_ >= enteredMs_) state_ = JUMP_CHARGED;
        else if (now - enteredMs_ >= CHARGE_TIMEOUT_MS) state_ = JUMP_FAULT;
        break;
      case JUMP_FAULT:
        requested_ = false;
        break;
    }
    requested_ = false;  // 回せない状態で来た要求は持ち越さない（溜めの最中に押しても跳ばない）
    return state_ == JUMP_CHARGING || state_ == JUMP_FIRING;
  }

  JumpState state() const { return state_; }
  bool charged() const { return state_ == JUMP_CHARGED; }

 private:
  bool takeRequest() {
    bool r = requested_;
    requested_ = false;
    return r;
  }

  void enter(JumpState s, uint32_t now) {
    state_ = s;
    enteredMs_ = now;
  }

  void debounce(uint32_t now, bool raw) {
    if (!rawValid_ || raw != raw_) {
      raw_ = raw;
      rawValid_ = true;
      rawSince_ = now;
    }
    if (now - rawSince_ >= DEBOUNCE_MS && (!stableValid_ || pressed_ != raw_)) {
      pressed_ = raw_;
      stableValid_ = true;
      pressedSince_ = rawSince_;
    }
  }

  JumpState state_ = JUMP_UNKNOWN;
  bool requested_ = false;
  uint32_t enteredMs_ = 0;
  bool raw_ = false;
  bool rawValid_ = false;
  uint32_t rawSince_ = 0;
  bool pressed_ = false;
  bool stableValid_ = false;
  uint32_t pressedSince_ = 0;
};

}  // namespace mrc
