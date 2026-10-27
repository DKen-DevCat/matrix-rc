// 映像ワーカー。JPEG を受け取り、デコードして高画質化し、OffscreenCanvas に描く（設計書④-E1 2章）。
// 「次の 1 枚」だけを持ち、溜めない。操作の 50Hz 送信があるメインスレッドを塞がないためにワーカーで動かす。
import { Pipeline, MODES } from './enhance/pipeline.js';
import { LatestSlot } from './enhance/latest.js';

let pipeline = null;   // WebGL2 のパイプライン。使えなければ null で、2D 描画に落とす
let ctx2d = null;
let canvas = null;
const slot = new LatestSlot();
let busy = false;
let lastJpeg = null;   // モード切替時の再描画と、机上用の 1 枚保存に使う

onmessage = (e) => {
  const m = e.data;
  switch (m.type) {
    case 'init': init(m); break;
    case 'frame': slot.put(m.jpeg); lastJpeg = m.jpeg; schedule(); break;
    case 'mode': pipeline?.setMode(m.mode); redraw(); break;
    case 'compare': pipeline?.setCompare(m.on); redraw(); break;
    case 'params': pipeline?.setParams(m.params); redraw(); break;
    case 'grab': postMessage({ type: 'jpeg', jpeg: lastJpeg }); break;
  }
};

function init(m) {
  canvas = m.canvas;
  try {
    pipeline = new Pipeline(canvas);
    pipeline.setMode(m.mode);
    pipeline.setCompare(m.compare);
    postMessage({ type: 'ready', modes: MODES, webgl: true });
  } catch (err) {
    ctx2d = canvas.getContext('2d');
    postMessage({ type: 'ready', modes: [MODES[0]], webgl: false, reason: String(err?.message ?? err) });
  }
}

function redraw() {
  if (lastJpeg && slot.empty) { slot.put(lastJpeg); schedule(); }
}

async function schedule() {
  if (busy || slot.empty) return;
  busy = true;
  const jpeg = slot.take();
  const t0 = performance.now();
  try {
    const bmp = await createImageBitmap(new Blob([jpeg], { type: 'image/jpeg' }));
    const t1 = performance.now();
    if (pipeline) {
      pipeline.draw(bmp);
    } else {
      if (canvas.width !== bmp.width) { canvas.width = bmp.width; canvas.height = bmp.height; }
      ctx2d.drawImage(bmp, 0, 0);
    }
    bmp.close();
    const t2 = performance.now();
    postMessage({ type: 'drawn', decodeMs: t1 - t0, drawMs: t2 - t1, dropped: slot.dropped });
  } catch (err) {
    postMessage({ type: 'error', message: String(err?.message ?? err) });
  }
  busy = false;
  if (!slot.empty) schedule();
}
