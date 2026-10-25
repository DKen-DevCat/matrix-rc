// キーの押下状態を CONTROL パケットにする（50Hz で呼ぶ）。画面からは切り離してテストする。
import { KEY, encodeControl } from './protocol.js';

const KEYMAP = { KeyW: KEY.W, KeyA: KEY.A, KeyS: KEY.S, KeyD: KEY.D, Space: KEY.SPACE };

function randomSession() {
  const a = new Uint32Array(1);
  do crypto.getRandomValues(a); while (a[0] === 0);
  return a[0];
}

export class ControlSender {
  constructor({ deviceId, sessionId = randomSession() }) {
    this.deviceId = deviceId;
    this.sessionId = sessionId;
    this.seq = 0;
    this.keys = 0;
    this.jumpId = 0;
  }

  keyDown(code) {
    const bit = KEYMAP[code];
    if (!bit) return false;
    if (bit === KEY.SPACE && !(this.keys & KEY.SPACE)) {
      this.jumpId = this.jumpId >= 65535 ? 1 : this.jumpId + 1;
    }
    this.keys |= bit;
    return true;
  }

  keyUp(code) {
    const bit = KEYMAP[code];
    if (!bit) return false;
    this.keys &= ~bit;
    return true;
  }

  releaseAll() {
    this.keys = 0;
  }

  build(now) {
    this.seq = (this.seq + 1) >>> 0;
    return encodeControl({
      deviceId: this.deviceId, sessionId: this.sessionId, seq: this.seq,
      sentAt: now, keys: this.keys, jumpId: this.jumpId,
    });
  }
}

// テレメトリが返した送信時刻と今の時刻（どちらも performance.now() の下位 32 ビット）から往復遅延を出す。
// holdMs は機体が受け取ってからテレメトリを送るまで手元に置いていた時間で、通信の遅れではないので引く。
export function rttMs(now, echoedSentAt, holdMs = 0) {
  return ((((Math.floor(now) >>> 0) - echoedSentAt) >>> 0) - holdMs);
}
