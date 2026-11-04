// 映像の出口。ワーカー（OffscreenCanvas＋WebGL2）で描き、使えないブラウザでは今までどおりメインスレッドの 2D で描く。
// app.js からは push()・setMode()・setCompare() だけを呼ぶ。
export function createVideoOut(canvas, { mode = 'off', compare = false, onReady, onDrawn, onError } = {}) {
  if (typeof canvas.transferControlToOffscreen === 'function' && typeof Worker === 'function') {
    try {
      const offscreen = canvas.transferControlToOffscreen();
      const worker = new Worker(new URL('./video-worker.js', import.meta.url), { type: 'module' });
      const grabs = [];
      worker.onmessage = (e) => {
        const m = e.data;
        if (m.type === 'ready') onReady?.(m);
        else if (m.type === 'drawn') onDrawn?.(m);
        else if (m.type === 'error') onError?.(m.message);
        else if (m.type === 'jpeg') grabs.shift()?.(m.jpeg);
      };
      worker.onerror = (e) => onError?.(e.message);
      worker.postMessage({ type: 'init', canvas: offscreen, mode, compare }, [offscreen]);
      return {
        push(jpeg) { worker.postMessage({ type: 'frame', jpeg }, [jpeg.buffer]); },
        setMode(m) { worker.postMessage({ type: 'mode', mode: m }); },
        setCompare(on) { worker.postMessage({ type: 'compare', on }); },
        setParams(params) { worker.postMessage({ type: 'params', params }); },
        grab() { return new Promise((resolve) => { grabs.push(resolve); worker.postMessage({ type: 'grab' }); }); },
      };
    } catch { /* 下の 2D に落とす */ }
  }
  // ワーカーも OffscreenCanvas もない古いブラウザ向け。高画質化はできない
  const ctx = canvas.getContext('2d');
  let decoding = false;
  let last = null;
  queueMicrotask(() => onReady?.({ modes: [{ id: 'off', label: 'オフ（この環境では高画質化できません）' }], webgl: false }));
  return {
    push(jpeg) {
      last = jpeg;
      if (decoding) return; // 描いている途中なら捨てる（溜めない）
      decoding = true;
      const t0 = performance.now();
      createImageBitmap(new Blob([jpeg], { type: 'image/jpeg' }))
        .then((bmp) => {
          if (canvas.width !== bmp.width) { canvas.width = bmp.width; canvas.height = bmp.height; }
          ctx.drawImage(bmp, 0, 0);
          bmp.close();
          onDrawn?.({ decodeMs: performance.now() - t0, drawMs: 0, dropped: 0 });
        })
        .catch(() => {})
        .finally(() => { decoding = false; });
    },
    setMode() {},
    setCompare() {},
    setParams() {},
    grab() { return Promise.resolve(last); },
  };
}
