// 高画質化の、ブラウザなしで確かめられる部分（設計書④-E1）。シェーダ本体はブラウザで目視する。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LatestSlot } from '../../web/js/enhance/latest.js';
import { easuCon0, rcasSharp } from '../../web/js/enhance/fsr.js';

test('LatestSlot は最新の 1 枚だけを持ち、追いつかない分は捨てて数える', () => {
  const s = new LatestSlot();
  assert.equal(s.empty, true);
  assert.equal(s.take(), null);
  s.put('a');
  s.put('b');
  s.put('c');
  assert.equal(s.dropped, 2);
  assert.equal(s.take(), 'c');
  assert.equal(s.empty, true);
  s.put('d');
  assert.equal(s.dropped, 2);
  assert.equal(s.take(), 'd');
});

test('EASU の定数は 2 倍拡大で出力画素の中心を入力画素に写す', () => {
  const [sx, sy, ox, oy] = easuCon0(320, 240, 640, 480);
  assert.equal(sx, 0.5);
  assert.equal(sy, 0.5);
  assert.equal(ox, -0.25);
  assert.equal(oy, -0.25);
  // 出力画素 (0,0) → 入力 -0.25（f=0 の手前）、出力 (639,479) → 入力 319.25
  assert.equal(639 * sx + ox, 319.25);
});

test('RCAS の強さは 0 が最強で、1 増えるごとに半分', () => {
  assert.equal(rcasSharp(0), 1);
  assert.equal(rcasSharp(1), 0.5);
  assert.equal(rcasSharp(2), 0.25);
});
