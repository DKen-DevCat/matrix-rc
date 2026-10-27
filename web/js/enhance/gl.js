// WebGL2 の小さな道具。シェーダのコンパイル、画面いっぱいの三角形、描画先（テクスチャ＋FBO）。
// 高画質化の各パス（EASU・RCAS・表示）はこれの上に書く。

// 頂点バッファなしで画面いっぱいの三角形を出す（gl_VertexID 0,1,2）
const VERT = `#version 300 es
void main() {
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

function compileShader(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(`シェーダ: ${gl.getShaderInfoLog(sh)}`);
  return sh;
}

// 1 パス＝1 つのフラグメントシェーダ。uniform は名前と型を調べておき、run() で値を渡すだけにする。
export class Pass {
  constructor(gl, frag) {
    this.gl = gl;
    const prog = gl.createProgram();
    gl.attachShader(prog, compileShader(gl, gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compileShader(gl, gl.FRAGMENT_SHADER, frag));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(`リンク: ${gl.getProgramInfoLog(prog)}`);
    this.prog = prog;
    this.uniforms = new Map();
    const n = gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const u = gl.getActiveUniform(prog, i);
      this.uniforms.set(u.name, { type: u.type, loc: gl.getUniformLocation(prog, u.name) });
    }
  }

  // values: { 名前: 数値 | 配列 | WebGLTexture }。target: Target か null（画面）
  run(values, target) {
    const gl = this.gl;
    gl.useProgram(this.prog);
    let unit = 0;
    for (const [name, v] of Object.entries(values)) {
      const u = this.uniforms.get(name);
      if (!u) continue; // 最適化で消えた uniform は無視
      switch (u.type) {
        case gl.SAMPLER_2D:
          gl.activeTexture(gl.TEXTURE0 + unit);
          gl.bindTexture(gl.TEXTURE_2D, v);
          gl.uniform1i(u.loc, unit++);
          break;
        case gl.FLOAT: gl.uniform1f(u.loc, v); break;
        case gl.FLOAT_VEC2: gl.uniform2fv(u.loc, v); break;
        case gl.FLOAT_VEC3: gl.uniform3fv(u.loc, v); break;
        case gl.FLOAT_VEC4: gl.uniform4fv(u.loc, v); break;
        case gl.INT: case gl.BOOL: gl.uniform1i(u.loc, v); break;
        case gl.INT_VEC2: gl.uniform2iv(u.loc, v); break;
        default: throw new Error(`uniform ${name} の型 ${u.type} は未対応`);
      }
    }
    if (target) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo);
      gl.viewport(0, 0, target.width, target.height);
    } else {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
}

// 端はクランプ。filter は gl.LINEAR か gl.NEAREST
export function createTexture(gl, filter) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return tex;
}

// 描画先。パスの出力を次のパスの入力にするためのテクスチャと FBO。サイズが変わったときだけ作り直す。
export class Target {
  constructor(gl) {
    this.gl = gl;
    this.tex = createTexture(gl, gl.LINEAR);
    this.fbo = gl.createFramebuffer();
    this.width = 0;
    this.height = 0;
  }

  resize(width, height) {
    if (this.width === width && this.height === height) return;
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.tex, 0);
    this.width = width;
    this.height = height;
  }
}
