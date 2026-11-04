// AMD FidelityFX Super Resolution 1.0（EASU＋RCAS）の GLSL ES 3.0 移植（設計書④-E1 4.1）。
// 元は ffx_a.h／ffx_fsr1.h（MIT License, Copyright (c) 2021 Advanced Micro Devices, Inc.）。
// 近似の逆数・逆平方根は正確な除算に置き換え、0 除算になる所は小さな値で守っている。
// 入力は sRGB のまま（FSR 1.0 は知覚空間の入力を前提にしている）。

// 輝度（×2 相当）。FSR と同じ重み
const LUMA = `float luma(vec3 c) { return c.b * 0.5 + (c.r * 0.5 + c.g); }`;

// ---- EASU（Edge Adaptive Spatial Upsampling）: 周囲 12 点を見て輪郭の向きに沿って拡大する ----
//    b c
//  e f g h
//  i j k l
//    n o
export const EASU_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uSrc;
uniform ivec2 uInSize;
uniform vec4 uCon0; // (inW/outW, inH/outH, 0.5*inW/outW-0.5, 0.5*inH/outH-0.5)
out vec4 oColor;
${LUMA}
vec3 tap(ivec2 p) { return texelFetch(uSrc, clamp(p, ivec2(0), uInSize - 1), 0).rgb; }

// '+' の形の 5 点から向きと輪郭の強さを足し込む（w は双線形の重み）
//    a
//  b c d
//    e
void easuSet(inout vec2 dir, inout float len, float w, float lA, float lB, float lC, float lD, float lE) {
  float dc = lD - lC;
  float cb = lC - lB;
  float lenX = 1.0 / max(max(abs(dc), abs(cb)), 1e-6);
  float dirX = lD - lB;
  dir.x += dirX * w;
  lenX = clamp(abs(dirX) * lenX, 0.0, 1.0);
  lenX *= lenX;
  len += lenX * w;
  float ec = lE - lC;
  float ca = lC - lA;
  float lenY = 1.0 / max(max(abs(ec), abs(ca)), 1e-6);
  float dirY = lE - lA;
  dir.y += dirY * w;
  lenY = clamp(abs(dirY) * lenY, 0.0, 1.0);
  lenY *= lenY;
  len += lenY * w;
}

// 1 点分の重み付き加算。向きに合わせて回し、輪郭の強さに応じて窓を伸縮した lanczos2 近似
void easuTap(inout vec3 aC, inout float aW, vec2 off, vec2 dir, vec2 len, float lob, float clp, vec3 c) {
  vec2 v = vec2(off.x * dir.x + off.y * dir.y, off.x * -dir.y + off.y * dir.x);
  v *= len;
  float d2 = min(dot(v, v), clp);
  float wB = 2.0 / 5.0 * d2 - 1.0;
  float wA = lob * d2 - 1.0;
  wB *= wB;
  wA *= wA;
  wB = 25.0 / 16.0 * wB - (25.0 / 16.0 - 1.0);
  float w = wB * wA;
  aC += c * w;
  aW += w;
}

void main() {
  vec2 pp = floor(gl_FragCoord.xy) * uCon0.xy + uCon0.zw;
  vec2 fp = floor(pp);
  pp -= fp;
  ivec2 f0 = ivec2(fp);
  vec3 b = tap(f0 + ivec2(0, -1)), c = tap(f0 + ivec2(1, -1));
  vec3 e = tap(f0 + ivec2(-1, 0)), f = tap(f0), g = tap(f0 + ivec2(1, 0)), h = tap(f0 + ivec2(2, 0));
  vec3 i = tap(f0 + ivec2(-1, 1)), j = tap(f0 + ivec2(0, 1)), k = tap(f0 + ivec2(1, 1)), l = tap(f0 + ivec2(2, 1));
  vec3 n = tap(f0 + ivec2(0, 2)), o = tap(f0 + ivec2(1, 2));
  float bL = luma(b), cL = luma(c), eL = luma(e), fL = luma(f), gL = luma(g), hL = luma(h);
  float iL = luma(i), jL = luma(j), kL = luma(k), lL = luma(l), nL = luma(n), oL = luma(o);

  vec2 dir = vec2(0.0);
  float len = 0.0;
  easuSet(dir, len, (1.0 - pp.x) * (1.0 - pp.y), bL, eL, fL, gL, jL);
  easuSet(dir, len, pp.x * (1.0 - pp.y), cL, fL, gL, hL, kL);
  easuSet(dir, len, (1.0 - pp.x) * pp.y, fL, iL, jL, kL, nL);
  easuSet(dir, len, pp.x * pp.y, gL, jL, kL, lL, oL);

  float dirR = dot(dir, dir);
  bool zro = dirR < 1.0 / 32768.0;
  dirR = zro ? 1.0 : inversesqrt(dirR);
  dir.x = zro ? 1.0 : dir.x;
  dir *= dirR;
  len = len * 0.5;
  len *= len;
  // 窓を縦横 1.0 から斜め sqrt(2) まで伸ばす
  float stretch = dot(dir, dir) / max(abs(dir.x), abs(dir.y));
  vec2 len2 = vec2(1.0 + (stretch - 1.0) * len, 1.0 - 0.5 * len);
  float lob = 0.5 + ((1.0 / 4.0 - 0.04) - 0.5) * len;
  float clp = 1.0 / lob;

  vec3 min4 = min(min(f, g), min(j, k));
  vec3 max4 = max(max(f, g), max(j, k));
  vec3 aC = vec3(0.0);
  float aW = 0.0;
  easuTap(aC, aW, vec2( 0.0, -1.0) - pp, dir, len2, lob, clp, b);
  easuTap(aC, aW, vec2( 1.0, -1.0) - pp, dir, len2, lob, clp, c);
  easuTap(aC, aW, vec2(-1.0,  1.0) - pp, dir, len2, lob, clp, i);
  easuTap(aC, aW, vec2( 0.0,  1.0) - pp, dir, len2, lob, clp, j);
  easuTap(aC, aW, vec2( 0.0,  0.0) - pp, dir, len2, lob, clp, f);
  easuTap(aC, aW, vec2(-1.0,  0.0) - pp, dir, len2, lob, clp, e);
  easuTap(aC, aW, vec2( 1.0,  1.0) - pp, dir, len2, lob, clp, k);
  easuTap(aC, aW, vec2( 2.0,  1.0) - pp, dir, len2, lob, clp, l);
  easuTap(aC, aW, vec2( 2.0,  0.0) - pp, dir, len2, lob, clp, h);
  easuTap(aC, aW, vec2( 1.0,  0.0) - pp, dir, len2, lob, clp, g);
  easuTap(aC, aW, vec2( 1.0,  2.0) - pp, dir, len2, lob, clp, o);
  easuTap(aC, aW, vec2( 0.0,  2.0) - pp, dir, len2, lob, clp, n);
  // 近い 4 点の範囲に収めてリンギングを抑える
  oColor = vec4(min(max4, max(min4, aC / aW)), 1.0);
}`;

// EASU の定数 con0。出力画素の中心を入力画素の座標に写す
export function easuCon0(inW, inH, outW, outH) {
  return [inW / outW, inH / outH, 0.5 * inW / outW - 0.5, 0.5 * inH / outH - 0.5];
}

// ---- RCAS（Robust Contrast Adaptive Sharpening）: 拡大後に輪郭を立てる。ノイズ除去あり ----
//    b
//  d e f
//    h
export const RCAS_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uSrc;
uniform ivec2 uSize;
uniform float uSharp; // exp2(-sharpness)。1.0 が最強
out vec4 oColor;
${LUMA}
vec3 tap(ivec2 p) { return texelFetch(uSrc, clamp(p, ivec2(0), uSize - 1), 0).rgb; }

void main() {
  ivec2 ip = ivec2(gl_FragCoord.xy);
  vec3 b = tap(ip + ivec2(0, -1));
  vec3 d = tap(ip + ivec2(-1, 0));
  vec3 e = tap(ip);
  vec3 f = tap(ip + ivec2(1, 0));
  vec3 h = tap(ip + ivec2(0, 1));
  float bL = luma(b), dL = luma(d), eL = luma(e), fL = luma(f), hL = luma(h);
  // ノイズの検出（周囲の平均と中心の差を、周囲の幅で割る）
  float nz = 0.25 * bL + 0.25 * dL + 0.25 * fL + 0.25 * hL - eL;
  float mx = max(max(max(bL, dL), eL), max(fL, hL));
  float mn = min(min(min(bL, dL), eL), min(fL, hL));
  nz = clamp(abs(nz) / max(mx - mn, 1e-6), 0.0, 1.0);
  nz = -0.5 * nz + 1.0;
  // 周囲 4 点の最小・最大から、はみ出さない範囲で負のローブを決める
  vec3 mn4 = min(min(b, d), min(f, h));
  vec3 mx4 = max(max(b, d), max(f, h));
  vec3 hitMin = mn4 / max(4.0 * mx4, 1e-6);
  vec3 hitMax = (1.0 - mx4) / min(4.0 * mn4 - 4.0, -1e-6);
  vec3 lobeRGB = max(-hitMin, hitMax);
  float lobe = max(-(0.25 - 1.0 / 16.0), min(max(max(lobeRGB.r, lobeRGB.g), lobeRGB.b), 0.0)) * uSharp;
  lobe *= nz;
  float rcpL = 1.0 / (4.0 * lobe + 1.0);
  oColor = vec4((lobe * (b + d + f + h) + e) * rcpL, 1.0);
}`;

// RCAS の強さ。sharpness は 0.0 が最強、1.0 で半分、2.0 でほぼ無効
export function rcasSharp(sharpness) {
  return 2 ** -sharpness;
}
