import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ControlSender, rttMs } from '../../web/js/control.js';
import { decodeControl, KEY } from '../../web/js/protocol.js';

const make = () => new ControlSender({ deviceId: 1, sessionId: 77 });

test('押しているキーの状態をビットにして送る', () => {
  const s = make();
  s.keyDown('KeyW'); s.keyDown('KeyD');
  const p = decodeControl(s.build(1000));
  assert.equal(p.keys, KEY.W | KEY.D);
  assert.equal(p.sessionId, 77);
  assert.equal(p.sentAt, 1000);
  s.keyUp('KeyW');
  assert.equal(decodeControl(s.build(1020)).keys, KEY.D);
});

test('関係ないキーは無視し、扱ったかどうかを返す', () => {
  const s = make();
  assert.equal(s.keyDown('KeyQ'), false);
  assert.equal(s.keyDown('KeyA'), true);
  assert.equal(decodeControl(s.build(0)).keys, KEY.A);
});

test('送るたびに seq が 1 ずつ増える', () => {
  const s = make();
  assert.equal(decodeControl(s.build(0)).seq, 1);
  assert.equal(decodeControl(s.build(20)).seq, 2);
});

test('Space を押すたびにジャンプIDが増え、押しっぱなしの自動リピートでは増えない', () => {
  const s = make();
  assert.equal(decodeControl(s.build(0)).jumpId, 0);
  s.keyDown('Space');
  s.keyDown('Space'); // 自動リピート
  assert.equal(decodeControl(s.build(20)).jumpId, 1);
  s.keyUp('Space');
  s.keyDown('Space');
  assert.equal(decodeControl(s.build(40)).jumpId, 2);
});

test('ジャンプIDは 65535 の次に 0 を飛ばして 1 になる', () => {
  const s = make();
  s.jumpId = 65535;
  s.keyDown('Space');
  assert.equal(decodeControl(s.build(0)).jumpId, 1);
});

test('ウィンドウからフォーカスが外れたら全キーを離したことにする', () => {
  const s = make();
  s.keyDown('KeyW'); s.keyDown('Space');
  s.releaseAll();
  assert.equal(decodeControl(s.build(0)).keys, 0);
});

test('往復遅延は 32 ビットで一周しても正しく計算する', () => {
  assert.equal(rttMs(1050, 1000), 50);
  assert.equal(rttMs(10, 2 ** 32 - 20), 30);
});

test('往復遅延から、機体が受け取ってからテレメトリを送るまでの待ち時間を引く', () => {
  assert.equal(rttMs(1050, 1000, 15), 35);
});

test('セッションIDを指定しなければ 0 以外の乱数になる', () => {
  for (let i = 0; i < 20; i++) assert.notEqual(new ControlSender({ deviceId: 1 }).sessionId, 0);
});
