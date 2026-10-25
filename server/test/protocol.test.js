import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  TYPE, KEY, CONTROL_LEN, TELEMETRY_LEN, HELLO_LEN, CHUNK_MAX,
  encodeControl, decodeControl, decodeHeader,
  encodeTelemetry, decodeTelemetry,
  encodeHello, decodeHello,
  encodeVideoChunks, decodeVideoChunk, FrameAssembler,
} from '../../web/js/protocol.js';

const hex = (u8) => Buffer.from(u8).toString('hex').match(/../g).join(' ');

test('CONTROL はテストベクタと一致する（docs/protocol.md）', () => {
  const buf = encodeControl({
    deviceId: 1, sessionId: 0x11223344, seq: 7, sentAt: 1000,
    keys: KEY.W | KEY.D, jumpId: 3,
  });
  assert.equal(buf.length, CONTROL_LEN);
  assert.equal(hex(buf), '4d 01 01 01 44 33 22 11 07 00 00 00 e8 03 00 00 09 00 03 00');
});

test('CONTROL は往復で同じ値に戻る', () => {
  const v = { deviceId: 2, sessionId: 0xfffffffe, seq: 123456, sentAt: 0xffffffff, keys: 0x1f, jumpId: 65535 };
  assert.deepEqual(decodeControl(encodeControl(v)), v);
});

test('送信時刻は下位 32 ビットに丸める', () => {
  const buf = encodeControl({ deviceId: 1, sessionId: 1, seq: 1, sentAt: 2 ** 32 + 5.7, keys: 0, jumpId: 0 });
  assert.equal(decodeControl(buf).sentAt, 5);
});

test('壊れたパケットは null を返す', () => {
  const good = encodeControl({ deviceId: 1, sessionId: 1, seq: 1, sentAt: 0, keys: 0, jumpId: 0 });
  assert.equal(decodeControl(good.subarray(0, 19)), null);
  const badMagic = good.slice(); badMagic[0] = 0;
  assert.equal(decodeControl(badMagic), null);
  const badVer = good.slice(); badVer[1] = 2;
  assert.equal(decodeControl(badVer), null);
  const badType = good.slice(); badType[2] = TYPE.TELEMETRY;
  assert.equal(decodeControl(badType), null);
  assert.equal(decodeHeader(new Uint8Array(3)), null);
});

test('TELEMETRY は往復で同じ値に戻る', () => {
  const v = {
    deviceId: 1, sessionId: 9, seq: 10, sentAt: 11, vbatMv: 3912, flags: 0b100011,
    rssi: -61, lastJumpId: 4, jumpState: 2, holdMs: 17, uptimeMs: 123456,
  };
  const buf = encodeTelemetry(v);
  assert.equal(buf.length, TELEMETRY_LEN);
  assert.deepEqual(decodeTelemetry(buf), v);
});

test('TELEMETRY の経過時間は 255ms で頭打ちにする', () => {
  const t = { deviceId: 1, sessionId: 1, seq: 1, sentAt: 1, vbatMv: 0, flags: 0, rssi: 0, lastJumpId: 0, jumpState: 0, holdMs: 999, uptimeMs: 0 };
  assert.equal(decodeTelemetry(encodeTelemetry(t)).holdMs, 255);
});

test('HELLO はトークンを 16 バイトに 0 埋めし、長すぎるトークンは拒否する', () => {
  const buf = encodeHello({ deviceId: 3, token: 'abc' });
  assert.equal(buf.length, HELLO_LEN);
  assert.deepEqual(decodeHello(buf), { deviceId: 3, token: 'abc' });
  assert.throws(() => encodeHello({ deviceId: 3, token: 'x'.repeat(17) }));
});

test('VIDEO は 240 バイトずつに分割され、組み立てると元に戻る', () => {
  const jpeg = Uint8Array.from({ length: 1000 }, (_, i) => i & 0xff);
  const chunks = encodeVideoChunks({ deviceId: 1, frameId: 42, jpeg });
  assert.equal(chunks.length, Math.ceil(1000 / CHUNK_MAX));
  assert.ok(chunks.every((c) => c.length <= 8 + CHUNK_MAX));
  const asm = new FrameAssembler();
  let out = null;
  // 順不同で届いても組み立てられる
  for (const c of [...chunks].reverse()) out = asm.push(decodeVideoChunk(c)) ?? out;
  assert.deepEqual(out.jpeg, jpeg);
  assert.equal(out.frameId, 42);
});

test('新しいフレームの断片が来たら、そろっていない古いフレームは捨てる', () => {
  const a = encodeVideoChunks({ deviceId: 1, frameId: 1, jpeg: new Uint8Array(500) });
  const b = encodeVideoChunks({ deviceId: 1, frameId: 2, jpeg: new Uint8Array(300) });
  const asm = new FrameAssembler();
  asm.push(decodeVideoChunk(a[0]));
  assert.equal(asm.push(decodeVideoChunk(b[0])), null);
  // 古いフレームの残りが遅れて届いても表示しない
  for (const c of a.slice(1)) assert.equal(asm.push(decodeVideoChunk(c)), null);
  const done = asm.push(decodeVideoChunk(b[1]));
  assert.equal(done.frameId, 2);
  assert.equal(asm.dropped, 1);
});

test('フレーム番号が 65535 から 0 に戻っても新しいものとして扱う', () => {
  const asm = new FrameAssembler();
  const last = encodeVideoChunks({ deviceId: 1, frameId: 65535, jpeg: new Uint8Array(10) });
  assert.ok(asm.push(decodeVideoChunk(last[0])));
  const next = encodeVideoChunks({ deviceId: 1, frameId: 0, jpeg: new Uint8Array(10) });
  assert.ok(asm.push(decodeVideoChunk(next[0])));
});
