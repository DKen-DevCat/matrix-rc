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

test('PSNR と SSIM：同じ画像で ∞ と 1、違いがあれば下がる', async () => {
  const { toGray, psnr, ssim } = await import('../../web/js/enhance/metrics.js');
  const w = 16, h = 16;
  const a = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < a.length; i += 4) { a[i] = (i / 4) % w * 16; a[i + 1] = 128; a[i + 2] = 64; a[i + 3] = 255; }
  const b = new Uint8ClampedArray(a);
  assert.equal(psnr(a, b), Infinity);
  assert.ok(Math.abs(ssim(toGray(a, w, h), toGray(b, w, h), w, h) - 1) < 1e-9);
  for (let i = 0; i < b.length; i += 4) b[i] = Math.min(255, b[i] + 10); // R を 10 ずらす
  // MSE = 100/3（3 チャネル平均）→ PSNR = 10*log10(65025/33.33) ≈ 32.9
  assert.ok(Math.abs(psnr(a, b) - 10 * Math.log10(65025 / (100 / 3))) < 1e-9);
  const s = ssim(toGray(a, w, h), toGray(b, w, h), w, h);
  assert.ok(s < 1 && s > 0.9);
});
