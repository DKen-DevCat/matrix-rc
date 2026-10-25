import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Relay } from '../src/relay.js';
import {
  encodeHello, encodeControl, encodeTelemetry, encodeVideoChunks, KEY,
} from '../../web/js/protocol.js';

const TOKEN = 'secret-token-123';
const DEV = { address: '192.168.1.50', port: 4210 };

function setup() {
  let now = 1000;
  const udp = [];
  const logs = [];
  const relay = new Relay({
    token: TOKEN,
    sendUdp: (buf, addr) => udp.push({ buf, addr }),
    now: () => now,
    log: (o) => logs.push(o),
  });
  return { relay, udp, logs, tick: (ms) => { now += ms; relay.tick(); }, at: () => now };
}

function client() {
  const c = { sent: [], closed: false };
  c.send = (m) => c.sent.push(m);
  c.close = () => { c.closed = true; };
  c.json = () => c.sent.filter((m) => typeof m === 'string').map((m) => JSON.parse(m));
  c.bin = () => c.sent.filter((m) => typeof m !== 'string');
  return c;
}

function auth(relay, c, token = TOKEN) {
  const h = relay.addClient(c);
  h.onText(JSON.stringify({ type: 'auth', token, deviceId: 1 }));
  return h;
}

const control = (over = {}) => encodeControl({
  deviceId: 1, sessionId: 5, seq: 1, sentAt: 0, keys: KEY.W, jumpId: 0, ...over,
});

test('正しいトークンの HELLO で機体を登録する', () => {
  const { relay } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  assert.equal(relay.deviceOnline(1), true);
});

test('トークンが違う HELLO は無視する', () => {
  const { relay, logs } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: 'wrong' }), DEV);
  assert.equal(relay.deviceOnline(1), false);
  assert.ok(logs.some((l) => l.event === 'hello_rejected'));
});

test('認証前のブラウザからの CONTROL は機体へ送らない', () => {
  const { relay, udp } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const h = relay.addClient(client());
  h.onBinary(control());
  assert.equal(udp.length, 0);
});

test('トークンが違うブラウザは切断する', () => {
  const { relay } = setup();
  const c = client();
  auth(relay, c, 'wrong');
  assert.equal(c.closed, true);
});

test('操作者の CONTROL はバイト列を変えずに機体へ送る（補完しない）', () => {
  const { relay, udp } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const h = auth(relay, client());
  const pkt = control({ seq: 9, jumpId: 2 });
  h.onBinary(pkt);
  assert.equal(udp.length, 1);
  assert.deepEqual(udp[0].buf, pkt);
  assert.deepEqual(udp[0].addr, DEV);
});

test('サーバは自分から CONTROL を作らない（ブラウザが止まれば何も送らない）', () => {
  const { relay, udp, tick } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const h = auth(relay, client());
  h.onBinary(control());
  for (let i = 0; i < 50; i++) tick(20);
  assert.equal(udp.length, 1);
});

test('1台を操作できるのは1人だけ。2人目は見るだけ', () => {
  const { relay, udp } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const a = client(); const b = client();
  auth(relay, a);
  const hb = auth(relay, b);
  assert.equal(a.json().at(-1).role, 'operator');
  assert.equal(b.json().at(-1).role, 'viewer');
  hb.onBinary(control());
  assert.equal(udp.length, 0);
});

test('操作者が抜けたら、別のブラウザが操作権を取れる', () => {
  const { relay, udp } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const a = client(); const b = client();
  const ha = auth(relay, a);
  const hb = auth(relay, b);
  hb.onText(JSON.stringify({ type: 'claim' }));
  assert.equal(b.json().at(-1).role, 'viewer');
  ha.onClose();
  hb.onText(JSON.stringify({ type: 'claim' }));
  assert.equal(b.json().at(-1).role, 'operator');
  hb.onBinary(control());
  assert.equal(udp.length, 1);
});

test('別の機体ID宛ての CONTROL は送らない', () => {
  const { relay, udp } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  relay.onUdp(encodeHello({ deviceId: 2, token: TOKEN }), { address: '192.168.1.51', port: 4210 });
  const h = auth(relay, client());
  h.onBinary(control({ deviceId: 2 }));
  assert.equal(udp.length, 0);
});

test('長さや種別がおかしいバイナリは送らない', () => {
  const { relay, udp } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const h = auth(relay, client());
  h.onBinary(control().subarray(0, 10));
  h.onBinary(encodeTelemetry({ deviceId: 1, sessionId: 0, seq: 0, sentAt: 0, vbatMv: 0, flags: 0, rssi: 0, lastJumpId: 0, jumpState: 0, holdMs: 0, uptimeMs: 0 }));
  assert.equal(udp.length, 0);
});

test('機体からのパケットは、登録したアドレスから来たものだけ全ブラウザへ流す', () => {
  const { relay } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const a = client(); const b = client();
  auth(relay, a); auth(relay, b);
  const [chunk] = encodeVideoChunks({ deviceId: 1, frameId: 1, jpeg: new Uint8Array(10) });
  relay.onUdp(chunk, DEV);
  relay.onUdp(chunk, { address: '10.0.0.9', port: 4210 }); // なりすまし
  assert.equal(a.bin().length, 1);
  assert.equal(b.bin().length, 1);
});

test('テレメトリが返した seq から、サーバ⇄機体の往復遅延をログに残す', () => {
  const { relay, logs, tick } = setup();
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  const h = auth(relay, client());
  h.onBinary(control({ seq: 42 }));
  tick(18);
  relay.onUdp(encodeTelemetry({ deviceId: 1, sessionId: 5, seq: 42, sentAt: 0, vbatMv: 3900, flags: 0, rssi: -50, lastJumpId: 0, jumpState: 0, holdMs: 0, uptimeMs: 1 }), DEV);
  const rtt = logs.find((l) => l.event === 'rtt');
  assert.equal(rtt.ms, 18);
  assert.equal(rtt.seq, 42);
});

test('HELLO が 3 秒途絶えたら機体はオフライン扱いになり、ブラウザに知らせる', () => {
  const { relay, tick } = setup();
  const c = client();
  auth(relay, c);
  relay.onUdp(encodeHello({ deviceId: 1, token: TOKEN }), DEV);
  assert.equal(c.json().at(-1).deviceOnline, true);
  tick(3100);
  assert.equal(relay.deviceOnline(1), false);
  assert.equal(c.json().at(-1).deviceOnline, false);
});

test('認証しないまま 2 秒たったブラウザは切断する', () => {
  const { relay, tick } = setup();
  const c = client();
  relay.addClient(c);
  tick(2100);
  assert.equal(c.closed, true);
});

test('JSON としては正しいが物でないテキスト（null など）が来てもサーバは落ちない', () => {
  const { relay } = setup();
  const c = client();
  const h = relay.addClient(c);
  for (const text of ['null', '123', '"auth"', 'true', '{broken']) h.onText(text);
  h.onText(JSON.stringify({ type: 'auth', token: TOKEN, deviceId: 1 }));
  assert.equal(c.json().at(-1).role, 'operator');
});

test('機体IDが 1〜254 の整数でなければ 1 として扱う', () => {
  const { relay } = setup();
  for (const deviceId of [0, 255, -1, 1.5, 'x', undefined]) {
    const c = client();
    relay.addClient(c).onText(JSON.stringify({ type: 'auth', token: TOKEN, deviceId }));
    assert.equal(c.json().at(-1).deviceId, 1, `deviceId=${deviceId}`);
  }
});
