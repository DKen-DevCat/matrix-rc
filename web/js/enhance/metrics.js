// 画質の指標（実験ページ用）。RGBA の画素列（上から下）どうしを比べる。
// PSNR は RGB 3 チャネルの平均二乗誤差から。SSIM は輝度（BT.601）に 7×7 の一様窓で、標準の定数（K1=0.01, K2=0.03, L=255）。

export function toGray(rgba, w, h) {
  const g = new Float32Array(w * h);
  for (let i = 0, j = 0; i < g.length; i++, j += 4) g[i] = 0.299 * rgba[j] + 0.587 * rgba[j + 1] + 0.114 * rgba[j + 2];
  return g;
}

export function psnr(a, b) {
  if (a.length !== b.length) throw new Error('大きさが違う');
  let se = 0;
  let n = 0;
  for (let i = 0; i < a.length; i += 4) {
    for (let c = 0; c < 3; c++) { const d = a[i + c] - b[i + c]; se += d * d; }
    n += 3;
  }
  if (se === 0) return Infinity;
  return 10 * Math.log10((255 * 255) / (se / n));
}

export function ssim(ga, gb, w, h, win = 7) {
  if (ga.length !== w * h || gb.length !== w * h) throw new Error('大きさが違う');
  const C1 = (0.01 * 255) ** 2;
  const C2 = (0.03 * 255) ** 2;
  const n = win * win;
  let sum = 0;
  let count = 0;
  for (let y = 0; y + win <= h; y++) {
    for (let x = 0; x + win <= w; x++) {
      let ma = 0, mb = 0, saa = 0, sbb = 0, sab = 0;
      for (let v = 0; v < win; v++) {
        let i = (y + v) * w + x;
        for (let u = 0; u < win; u++, i++) {
          const p = ga[i], q = gb[i];
          ma += p; mb += q; saa += p * p; sbb += q * q; sab += p * q;
        }
      }
      ma /= n; mb /= n;
      const va = saa / n - ma * ma;
      const vb = sbb / n - mb * mb;
      const cov = sab / n - ma * mb;
      sum += ((2 * ma * mb + C1) * (2 * cov + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2));
      count++;
    }
  }
  return count ? sum / count : 1;
}
