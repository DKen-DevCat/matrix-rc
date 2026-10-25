// 通信プロトコル v1。仕様は docs/protocol.md。ブラウザとサーバが共用する。
// 機体側の実装は firmware/lib/core/protocol.h。

export const MAGIC = 0x4d;
export const VERSION = 1;
export const TYPE = { CONTROL: 1, TELEMETRY: 2, HELLO: 3, VIDEO: 4, AUDIO: 5 };
export const KEY = { W: 1, A: 2, S: 4, D: 8, SPACE: 16 };
export const FLAG = {
  STOPPED: 1, CHARGED: 2, LOW_BATT_WARN: 4, LOW_BATT_CUTOFF: 8, JUMP_FAULT: 16, CAMERA_ON: 32,
};
export const JUMP_STATE = ['不明', 'チャージ中', 'チャージ済み', '発射中', '異常'];

export const HEADER_LEN = 4;
export const CONTROL_LEN = 20;
export const TELEMETRY_LEN = 28;
export const HELLO_LEN = 20;
export const TOKEN_LEN = 16;
export const CHUNK_HEADER_LEN = 8;
export const CHUNK_MAX = 240;

function header(buf, type, deviceId) {
  buf[0] = MAGIC;
  buf[1] = VERSION;
  buf[2] = type;
  buf[3] = deviceId;
  return new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
}

function view(buf) {
  return new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
}

// 共通ヘッダだけを読む。壊れていれば null。
export function decodeHeader(buf) {
  if (!buf || buf.length < HEADER_LEN || buf[0] !== MAGIC || buf[1] !== VERSION) return null;
  return { type: buf[2], deviceId: buf[3] };
}

function check(buf, type, len) {
  const h = decodeHeader(buf);
  if (!h || h.type !== type) return null;
  if (len !== undefined && buf.length !== len) return null;
  return h;
}

const u32 = (n) => Math.floor(n) >>> 0;

export function encodeControl({ deviceId, sessionId, seq, sentAt, keys, jumpId }) {
  const buf = new Uint8Array(CONTROL_LEN);
  const v = header(buf, TYPE.CONTROL, deviceId);
  v.setUint32(4, u32(sessionId), true);
  v.setUint32(8, u32(seq), true);
  v.setUint32(12, u32(sentAt % 2 ** 32), true);
  v.setUint8(16, keys & 0x1f);
  v.setUint16(18, jumpId, true);
  return buf;
}

export function decodeControl(buf) {
  const h = check(buf, TYPE.CONTROL, CONTROL_LEN);
  if (!h) return null;
  const v = view(buf);
  return {
    deviceId: h.deviceId,
    sessionId: v.getUint32(4, true),
    seq: v.getUint32(8, true),
    sentAt: v.getUint32(12, true),
    keys: v.getUint8(16) & 0x1f,
    jumpId: v.getUint16(18, true),
  };
}

export function encodeTelemetry(t) {
  const buf = new Uint8Array(TELEMETRY_LEN);
  const v = header(buf, TYPE.TELEMETRY, t.deviceId);
  v.setUint32(4, u32(t.sessionId), true);
  v.setUint32(8, u32(t.seq), true);
  v.setUint32(12, u32(t.sentAt), true);
  v.setUint16(16, t.vbatMv, true);
  v.setUint8(18, t.flags);
  v.setInt8(19, t.rssi);
  v.setUint16(20, t.lastJumpId, true);
  v.setUint8(22, t.jumpState);
  v.setUint8(23, Math.min(255, Math.max(0, Math.floor(t.holdMs ?? 0))));
  v.setUint32(24, u32(t.uptimeMs), true);
  return buf;
}

export function decodeTelemetry(buf) {
  const h = check(buf, TYPE.TELEMETRY, TELEMETRY_LEN);
  if (!h) return null;
  const v = view(buf);
  return {
    deviceId: h.deviceId,
    sessionId: v.getUint32(4, true),
    seq: v.getUint32(8, true),
    sentAt: v.getUint32(12, true),
    vbatMv: v.getUint16(16, true),
    flags: v.getUint8(18),
    rssi: v.getInt8(19),
    lastJumpId: v.getUint16(20, true),
    jumpState: v.getUint8(22),
    holdMs: v.getUint8(23),
    uptimeMs: v.getUint32(24, true),
  };
}

export function encodeHello({ deviceId, token }) {
  const bytes = new TextEncoder().encode(token);
  if (bytes.length > TOKEN_LEN) throw new Error(`token は ${TOKEN_LEN} バイト以内`);
  const buf = new Uint8Array(HELLO_LEN);
  header(buf, TYPE.HELLO, deviceId);
  buf.set(bytes, HEADER_LEN);
  return buf;
}

export function decodeHello(buf) {
  const h = check(buf, TYPE.HELLO, HELLO_LEN);
  if (!h) return null;
  const raw = buf.subarray(HEADER_LEN, HEADER_LEN + TOKEN_LEN);
  const end = raw.indexOf(0);
  const token = new TextDecoder().decode(end < 0 ? raw : raw.subarray(0, end));
  return { deviceId: h.deviceId, token };
}

export function encodeVideoChunks({ deviceId, frameId, jpeg }) {
  const count = Math.ceil(jpeg.length / CHUNK_MAX);
  if (count > 255) throw new Error('フレームが大きすぎる');
  const chunks = [];
  for (let i = 0; i < count; i++) {
    const part = jpeg.subarray(i * CHUNK_MAX, (i + 1) * CHUNK_MAX);
    const buf = new Uint8Array(CHUNK_HEADER_LEN + part.length);
    const v = header(buf, TYPE.VIDEO, deviceId);
    v.setUint16(4, frameId & 0xffff, true);
    v.setUint8(6, i);
    v.setUint8(7, count);
    buf.set(part, CHUNK_HEADER_LEN);
    chunks.push(buf);
  }
  return chunks;
}

export function decodeVideoChunk(buf) {
  const h = check(buf, TYPE.VIDEO);
  if (!h || buf.length <= CHUNK_HEADER_LEN || buf.length > CHUNK_HEADER_LEN + CHUNK_MAX) return null;
  const v = view(buf);
  const index = v.getUint8(6);
  const count = v.getUint8(7);
  if (count === 0 || index >= count) return null;
  return { deviceId: h.deviceId, frameId: v.getUint16(4, true), index, count, data: buf.subarray(CHUNK_HEADER_LEN) };
}

export function decodeAudio(buf) {
  const h = check(buf, TYPE.AUDIO);
  if (!h || buf.length <= CHUNK_HEADER_LEN || (buf.length - CHUNK_HEADER_LEN) % 2 !== 0) return null;
  const v = view(buf);
  const pcm = new Int16Array((buf.length - CHUNK_HEADER_LEN) / 2);
  for (let i = 0; i < pcm.length; i++) pcm[i] = v.getInt16(CHUNK_HEADER_LEN + i * 2, true);
  return { deviceId: h.deviceId, audioSeq: v.getUint16(4, true), pcm };
}

// 16 ビットの連番で a が b より新しいか（一周しても判定できるよう差の符号で見る）
export function newer16(a, b) {
  const d = (a - b) & 0xffff;
  return d !== 0 && d < 0x8000;
}

// JPEG の断片を組み立てる。そろったフレームだけを返し、溜めない。
export class FrameAssembler {
  constructor() {
    this.frameId = null;
    this.parts = null;
    this.received = 0;
    this.dropped = 0;
  }

  push(chunk) {
    if (!chunk) return null;
    if (this.frameId === null || newer16(chunk.frameId, this.frameId)) {
      if (this.parts && this.received < this.parts.length) this.dropped++;
      this.frameId = chunk.frameId;
      this.parts = new Array(chunk.count);
      this.received = 0;
    } else if (chunk.frameId !== this.frameId || chunk.count !== this.parts.length) {
      return null; // 古いフレームの断片
    }
    if (this.parts[chunk.index]) return null;
    this.parts[chunk.index] = chunk.data;
    this.received++;
    if (this.received < this.parts.length) return null;
    const total = this.parts.reduce((n, p) => n + p.length, 0);
    const jpeg = new Uint8Array(total);
    let off = 0;
    for (const p of this.parts) { jpeg.set(p, off); off += p.length; }
    this.parts = [];
    this.received = 0;
    return { frameId: this.frameId, jpeg };
  }
}
