// 高画質化のパイプライン。モードごとにパスを並べ、比較（左右）表示を含めて OffscreenCanvas に描く（設計書④-E1 3章）。
import { Pass, Target, createTexture } from './gl.js';
import { EASU_FRAG, RCAS_FRAG, easuCon0, rcasSharp } from './fsr.js';

export const MODES = [
  { id: 'off', label: 'オフ（320×240 のまま）' },
  { id: 'fsr', label: 'E1-a シェーダ拡大（EASU＋RCAS）' },
];

export const DEFAULTS = { scale: 2, sharpness: 0.5 };

// 表示パス。比較のときは左半分に元画像（線形補間。CSS の拡大と同じ見た目）、右半分に処理後を出し、境界に線を引く
const PRESENT_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uProc;
uniform sampler2D uRaw;
uniform vec2 uOut;
uniform float uSplit; // 負なら比較なし。それ以外は境界の x
out vec4 oColor;
void main() {
  vec2 uv = gl_FragCoord.xy / uOut;
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
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    this.raw = createTexture(gl, gl.LINEAR);
    this.easu = new Pass(gl, EASU_FRAG);
    this.rcas = new Pass(gl, RCAS_FRAG);
    this.present = new Pass(gl, PRESENT_FRAG);
    this.up = new Target(gl);
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
    Object.assign(this.params, p);
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
    if (this.mode === 'fsr') {
      ow = w * this.params.scale;
      oh = h * this.params.scale;
      this.up.resize(ow, oh);
      this.sharp.resize(ow, oh);
      this.easu.run({ uSrc: this.raw, uInSize: [w, h], uCon0: easuCon0(w, h, ow, oh) }, this.up);
      this.rcas.run({ uSrc: this.up.tex, uSize: [ow, oh], uSharp: rcasSharp(this.params.sharpness) }, this.sharp);
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
