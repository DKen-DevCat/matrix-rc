// JPEG のブロックノイズ除去（設計書④-E1 4.2）。8×8 の境界をまたぐ段差が小さく、両側が平らなときだけならす。
// 大きい段差は本物の輪郭として残す（H.264 のループフィルタと同じ考え方の簡易版）。
// 縦の境界（uDir=(1,0)）と横の境界（uDir=(0,1)）の 2 パスで使う。テクスチャの 0 行目が画像の上端なので、格子は JPEG と同じ位置。
export const DEBLOCK_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uSrc;
uniform ivec2 uSize;
uniform ivec2 uDir;    // (1,0): 縦の境界を横に、(0,1): 横の境界を縦に
uniform float uAlpha;  // 境界の段差がこれ未満ならブロックノイズとみなす（0〜1）
uniform float uBeta;   // 境界の両側の起伏がこれ未満なら平らとみなす（0〜1）
uniform int uGrid;     // ブロックの大きさ（8）
out vec4 oColor;
vec3 tap(ivec2 p) { return texelFetch(uSrc, clamp(p, ivec2(0), uSize - 1), 0).rgb; }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

void main() {
  ivec2 ip = ivec2(gl_FragCoord.xy);
  int pos = (uDir.x == 1) ? ip.x : ip.y;
  int m = pos % uGrid;
  vec3 c = tap(ip);
  // 境界は m=7 と次の m=0 の間。対象は p1(6) p0(7) | q0(0) q1(1)
  if (m != 7 && m != 0 && m != 6 && m != 1) { oColor = vec4(c, 1.0); return; }
  bool pSide = (m == 7 || m == 6);
  bool inner = (m == 6 || m == 1);
  ivec2 d = uDir;
  ivec2 p0 = ip + d * (pSide ? (inner ? 1 : 0) : (inner ? -2 : -1));
  vec3 P2 = tap(p0 - 2 * d), P1 = tap(p0 - d), P0 = tap(p0);
  vec3 Q0 = tap(p0 + d), Q1 = tap(p0 + 2 * d), Q2 = tap(p0 + 3 * d);
  float step = abs(luma(Q0) - luma(P0));
  float bump = max(abs(luma(P1) - luma(P0)), abs(luma(Q1) - luma(Q0)));
  float w = (1.0 - smoothstep(uAlpha * 0.5, uAlpha, step)) * (1.0 - smoothstep(uBeta * 0.5, uBeta, bump));
  vec3 delta = ((Q0 - P0) * 4.0 + (P1 - Q1)) / 8.0;
  vec3 r;
  if (!inner) r = pSide ? P0 + w * delta : Q0 - w * delta;
  else if (pSide) r = P1 + w * 0.25 * (P2 + (P0 + Q0) * 0.5 - 2.0 * P1);
  else r = Q1 + w * 0.25 * (Q2 + (P0 + Q0) * 0.5 - 2.0 * Q1);
  oColor = vec4(r, 1.0);
}`;
