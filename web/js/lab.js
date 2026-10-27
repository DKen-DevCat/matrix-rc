// 高画質化の実験ページ（設計書④-E1 5章）。手元の画像を 320×240 の JPEG に落とし、各モードで処理して指標と時間を出す。
import { Pipeline, MODES, DEFAULTS } from './enhance/pipeline.js';
import { toGray, psnr, ssim } from './enhance/metrics.js';

const $ = (id) => document.getElementById(id);
const SRC_W = 320;
const SRC_H = 240;
const RUNS = 20;

const storage = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* 使えなくても動く */ } },
};

// 処理用の canvas（画面には出さない）
const work = document.createElement('canvas');
let pipeline = null;
try {
  pipeline = new Pipeline(work);
} catch (err) {
  $('msg').textContent = `WebGL2 が使えません: ${err.message}`;
}

let file = null;

// スライダの値の表示と、変更時の再処理
for (const id of ['quality', 'sharpness', 'alpha', 'beta']) {
  const el = $(id);
  const show = () => { $(`${id}Out`).textContent = Number(el.value).toFixed(2); };
  el.addEventListener('input', show);
  el.addEventListener('change', () => run());
  show();
}
$('scale').addEventListener('change', () => run());
$('asis').addEventListener('change', () => run());
$('actual').addEventListener('change', () => $('cards').classList.toggle('actual', $('actual').checked));
$('file').addEventListener('change', () => { file = $('file').files[0] ?? null; $('run').disabled = !file; run(); });
$('run').addEventListener('click', () => run());

function params() {
  return {
    scale: Number($('scale').value),
    sharpness: Number($('sharpness').value),
    alpha: Number($('alpha').value),
    beta: Number($('beta').value),
  };
}

// 操作画面（app.js）が起動時に読む
$('apply').addEventListener('click', () => {
  storage.set('mrc.enhance.params', JSON.stringify(params()));
  $('msg').textContent = '操作画面の設定を保存しました（次に操作画面を開いたときから）。';
});

// 元画像を 4:3 に切り抜いて w×h に縮める
function cover(bitmap, w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const ctx = c.getContext('2d');
  const s = Math.max(w / bitmap.width, h / bitmap.height);
  const sw = w / s;
  const sh = h / s;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(bitmap, (bitmap.width - sw) / 2, (bitmap.height - sh) / 2, sw, sh, 0, 0, w, h);
  return c;
}

function card(title) {
  const el = document.createElement('div');
  el.className = 'card';
  el.innerHTML = '<h2></h2><canvas></canvas><p class="m">—</p>';
  el.querySelector('h2').textContent = title;
  $('cards').append(el);
  return { canvas: el.querySelector('canvas'), m: el.querySelector('.m') };
}

function showPixels(canvas, rgba, w, h) {
  canvas.width = w;
  canvas.height = h;
  canvas.getContext('2d').putImageData(new ImageData(rgba, w, h), 0, 0);
}

function metrics(rgba, truth, w, h) {
  if (!truth) return '元画像なし';
  const p = psnr(rgba, truth.rgba);
  const s = ssim(toGray(rgba, w, h), truth.gray, w, h);
  return `PSNR ${Number.isFinite(p) ? p.toFixed(2) : '∞'} dB・SSIM ${s.toFixed(4)}`;
}

let running = false;
let again = false;
async function run() {
  if (!file || !pipeline) return;
  if (running) { again = true; return; }
  running = true;
  $('msg').textContent = '処理中…';
  try {
    const p = params();
    const outW = SRC_W * p.scale;
    const outH = SRC_H * p.scale;
    const src = await createImageBitmap(file);

    // 入力の JPEG と、比較の基準（元画像を出力サイズに縮めたもの）
    let jpegBlob;
    let truth = null;
    if ($('asis').checked) {
      jpegBlob = file;
    } else {
      const small = cover(src, SRC_W, SRC_H);
      jpegBlob = await new Promise((r) => small.toBlob(r, 'image/jpeg', Number($('quality').value)));
      const t = cover(src, outW, outH).getContext('2d').getImageData(0, 0, outW, outH).data;
      truth = { rgba: t, gray: toGray(t, outW, outH) };
    }
    src.close();
    const bmp = await createImageBitmap(jpegBlob);
    if (bmp.width !== SRC_W || bmp.height !== SRC_H) {
      $('msg').textContent = `入力は ${SRC_W}×${SRC_H} の JPEG にしてください（${bmp.width}×${bmp.height}）`;
      return;
    }

    $('cards').replaceChildren();
    const inKB = (jpegBlob.size / 1024).toFixed(1);

    if (truth) {
      const c = card(`元画像（${outW}×${outH} に縮小）`);
      showPixels(c.canvas, truth.rgba, outW, outH);
      c.m.textContent = '比較の基準';
    }
    {
      const c = card(`入力の JPEG（${SRC_W}×${SRC_H}、${inKB} KB）`);
      c.canvas.width = SRC_W;
      c.canvas.height = SRC_H;
      c.canvas.getContext('2d').drawImage(bmp, 0, 0);
      c.m.textContent = '機体から届くもの';
    }
    {
      // オフ＝ブラウザの線形補間で出力サイズへ（CSS の拡大と同じ）
      const c = card('オフ（線形補間）');
      const t = document.createElement('canvas');
      t.width = outW;
      t.height = outH;
      const ctx = t.getContext('2d');
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'low';
      ctx.drawImage(bmp, 0, 0, outW, outH);
      const rgba = ctx.getImageData(0, 0, outW, outH).data;
      showPixels(c.canvas, rgba, outW, outH);
      c.m.textContent = metrics(rgba, truth, outW, outH);
    }
    for (const mode of MODES.filter((m) => m.id !== 'off')) {
      const c = card(mode.label);
      pipeline.setMode(mode.id);
      pipeline.setParams(p);
      pipeline.draw(bmp); // 1 回目はシェーダの準備が入るので時間に数えない
      const t0 = performance.now();
      for (let i = 0; i < RUNS; i++) pipeline.draw(bmp);
      const ms = (performance.now() - t0) / RUNS;
      const rgba = pipeline.readPixels();
      showPixels(c.canvas, rgba, outW, outH);
      c.m.textContent = `${metrics(rgba, truth, outW, outH)}・${ms.toFixed(2)} ms／枚`;
      await new Promise((r) => setTimeout(r)); // 画面を更新させる
    }
    bmp.close();
    $('apply').disabled = false;
    $('msg').textContent = `完了（RCAS ${p.sharpness}、α ${p.alpha}、β ${p.beta}、${p.scale} 倍）`;
  } catch (err) {
    $('msg').textContent = `失敗: ${err.message}`;
  } finally {
    running = false;
    if (again) { again = false; run(); }
  }
}

// 既定値をスライダに反映
$('sharpness').value = DEFAULTS.sharpness;
$('alpha').value = DEFAULTS.alpha;
$('beta').value = DEFAULTS.beta;
for (const id of ['sharpness', 'alpha', 'beta']) $(`${id}Out`).textContent = Number($(id).value).toFixed(2);
