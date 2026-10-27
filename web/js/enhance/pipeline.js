// 高画質化のパイプライン。モードごとにパスを並べ、比較（左右）表示を含めて OffscreenCanvas に描く（設計書④-E1 3章）。
import { Pass, Target, createTexture } from './gl.js';
import { EASU_FRAG, RCAS_FRAG, easuCon0, rcasSharp } from './fsr.js';
import { DEBLOCK_FRAG } from './deblock.js';

export const MODES = [
  { id: 'off', label: 'オフ（320×240 のまま）' },
  { id: 'fsr', label: 'E1-a シェーダ拡大（EASU＋RCAS）' },
  { id: 'deblock', label: 'E1-b デブロック＋シェーダ拡大' },
];

// scale は 2 か 4（4 は EASU を 2 回。FSR 1.0 の設計上の上限が 2 倍のため）
export const DEFAULTS = { scale: 2, sharpness: 0.5, alpha: 0.1, beta: 0.05 };

// 表示パス。比較のときは左半分に元画像（線形補間。CSS の拡大と同じ見た目）、右半分に処理後を出し、境界に線を引く
const PRESENT_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uProc;
uniform sampler2D uRaw;
uniform vec2 uOut;
uniform float uSplit; // 負なら比較なし。それ以外は境界の x
out vec4 oColor;
void main() {
  // テクスチャは上端が 0 行目、画面は下端が 0 行目なので上下を返す
  vec2 uv = vec2(gl_FragCoord.x, uOut.y - gl_FragCoord.y) / uOut;
  bool left = uSplit >= 0.0 && gl_FragCoord.x < uSplit;
  vec3 c = left ? texture(uRaw, uv).rgb : texture(uProc, uv).rgb;
  if (uSplit >= 0.0 && abs(gl_FragCoord.x - uSplit) < 1.0) c = vec3(1.0, 0.8, 0.2);
  oColor = vec4(c, 1.0);
}`;

export class Pipeline {
  constructor(canvas) {
    const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false, stencil: false });
    if (!gl) throw new Error('WebGL2 が使えない');
    this.canvas = canvas;
    this.gl = gl;
    // ImageBitmap の転送で UNPACK_FLIP_Y_WEBGL が効くかは環境で違う（ワーカーでは効き、メインスレッドでは無視された）ので
    // 頼らない。テクスチャの 0 行目＝画像の上端とし、画面に出すときだけ表示パスで上下を返す
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    this.raw = createTexture(gl, gl.LINEAR);
    this.easu = new Pass(gl, EASU_FRAG);
    this.rcas = new Pass(gl, RCAS_FRAG);
    this.present = new Pass(gl, PRESENT_FRAG);
    this.deblock = new Pass(gl, DEBLOCK_FRAG);
    this.db1 = new Target(gl);
    this.db2 = new Target(gl);
    this.up = new Target(gl);
    this.up2 = new Target(gl);
    this.sharp = new Target(gl);
    this.mode = 'off';
    this.compare = false;
    this.params = { ...DEFAULTS };
  }

  setMode(mode) {
    this.mode = MODES.some((m) => m.id === mode) ? mode : 'off';
  }

  setCompare(on) {
    this.compare = Boolean(on);
  }

  setParams(p) {
    for (const [k, v] of Object.entries(p ?? {})) {
      if (k in DEFAULTS && Number.isFinite(v)) this.params[k] = v;
    }
    this.params.scale = this.params.scale >= 4 ? 4 : 2;
  }

  // 最後に描いた内容を RGBA（上から下）で読み出す。実験ページの指標計算用。draw() の直後に呼ぶ
  readPixels() {
    const gl = this.gl;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const buf = new Uint8ClampedArray(w * h * 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    const out = new Uint8ClampedArray(w * h * 4);
    const row = w * 4;
    for (let y = 0; y < h; y++) out.set(buf.subarray(y * row, (y + 1) * row), (h - 1 - y) * row);
    return out;
  }

  // 1 枚描く。GPU の完了まで待つので、戻ったときには画面に出ている（処理時間の計測のため）
  draw(bitmap) {
    const gl = this.gl;
    const w = bitmap.width;
    const h = bitmap.height;
    gl.bindTexture(gl.TEXTURE_2D, this.raw);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, bitmap);

    let out = this.raw;
    let ow = w;
    let oh = h;
    if (this.mode === 'fsr' || this.mode === 'deblock') {
      const { scale, sharpness, alpha, beta } = this.params;
      let src = this.raw;
      if (this.mode === 'deblock') {
        this.db1.resize(w, h);
        this.db2.resize(w, h);
        const u = { uSize: [w, h], uAlpha: alpha, uBeta: beta, uGrid: 8 };
        this.deblock.run({ uSrc: src, uDir: [1, 0], ...u }, this.db1);
        this.deblock.run({ uSrc: this.db1.tex, uDir: [0, 1], ...u }, this.db2);
        src = this.db2.tex;
      }
      // EASU は 2 倍ずつ。4 倍は 2 回かける
      this.up.resize(w * 2, h * 2);
      this.easu.run({ uSrc: src, uInSize: [w, h], uCon0: easuCon0(w, h, w * 2, h * 2) }, this.up);
      let up = this.up;
      if (scale === 4) {
        this.up2.resize(w * 4, h * 4);
        this.easu.run({ uSrc: up.tex, uInSize: [w * 2, h * 2], uCon0: easuCon0(w * 2, h * 2, w * 4, h * 4) }, this.up2);
        up = this.up2;
      }
      ow = w * scale;
      oh = h * scale;
      this.sharp.resize(ow, oh);
      this.rcas.run({ uSrc: up.tex, uSize: [ow, oh], uSharp: rcasSharp(sharpness) }, this.sharp);
      out = this.sharp.tex;
    }
    if (this.canvas.width !== ow || this.canvas.height !== oh) {
      this.canvas.width = ow;
      this.canvas.height = oh;
    }
    this.present.run({ uProc: out, uRaw: this.raw, uOut: [ow, oh], uSplit: this.compare ? ow / 2 : -1 }, null);
    gl.finish();
    return { width: ow, height: oh };
  }
}
