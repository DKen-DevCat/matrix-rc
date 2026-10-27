// 操作画面。キー状態を 50Hz で送り、映像・音声・テレメトリを表示する（設計書① 6章）。
import {
  TYPE, FLAG, JUMP_STATE, decodeHeader, decodeTelemetry, decodeVideoChunk, decodeAudio, FrameAssembler,
} from './protocol.js';
import { ControlSender, rttMs } from './control.js';
import { createVideoOut } from './video-out.js';

const SEND_HZ = 50;
const $ = (id) => document.getElementById(id);

const storage = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* 使えなくても動く */ } },
};

let ws = null;
let sender = null;
let role = 'viewer';
let sendTimer = null;
let lastSendAt = 0;
let sendGapMax = 0;

// ---- 接続 ----

$('token').value = storage.get('mrc.token') ?? '';
// ボタンやフォームにフォーカスが残ると、W や Space がボタンの操作に取られる。操作キーは画面全体で受けたいので外す
const unfocus = () => document.activeElement?.blur?.();

$('login').addEventListener('submit', (e) => {
  e.preventDefault();
  storage.set('mrc.token', $('token').value);
  connect($('token').value, Number($('device').value));
  unfocus();
});
$('claim').addEventListener('click', () => { ws?.send(JSON.stringify({ type: 'claim' })); unfocus(); });

function setStatus(text, cls) {
  $('status').textContent = text;
  $('status').className = `pill ${cls ?? ''}`;
}

function connect(token, deviceId) {
  if (ws) {
    // 前の接続の close イベントは遅れて届く。新しい接続の送信を止めないよう、先にハンドラを外す
    ws.onclose = null;
    ws.onmessage = null;
    ws.close();
  }
  stopSending();
  const sock = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  ws = sock;
  sock.binaryType = 'arraybuffer';
  // 接続ごとに新しいセッションID（機体は停止中にだけ新しいセッションを受け入れる）
  sender = new ControlSender({ deviceId });
  setStatus('接続中…');
  sock.onopen = () => sock.send(JSON.stringify({ type: 'auth', token, deviceId }));
  sock.onclose = () => {
    if (sock !== ws) return;
    stopSending();
    setStatus('切断', 'bad');
    $('claim').hidden = true;
  };
  sock.onmessage = (e) => {
    if (sock !== ws) return;
    if (typeof e.data === 'string') onStatus(JSON.parse(e.data));
    else onBinary(new Uint8Array(e.data));
  };
}

function onStatus(msg) {
  if (msg.type !== 'status') return;
  role = msg.role;
  const dev = msg.deviceOnline ? '機体オンライン' : '機体オフライン';
  if (role === 'operator') setStatus(`操作中・${dev}`, msg.deviceOnline ? 'ok' : 'warn');
  else setStatus(`見学中・${dev}`, 'warn');
  $('claim').hidden = role === 'operator' || msg.operatorPresent;
  if (role === 'operator') startSending(); else stopSending();
}

// ---- 操作の送信 ----

function startSending() {
  if (sendTimer) return;
  // 押下状態を送り続ける。サーバは補完しないので、このタブが止まれば機体は 300ms で止まる。
  lastSendAt = 0;
  sendTimer = setInterval(() => {
    const now = performance.now();
    // 送信の間隔が開いていないかを測る。映像の処理がメインスレッドを塞ぐと、ここが伸びて機体が 300ms で止まる
    if (lastSendAt) sendGapMax = Math.max(sendGapMax, now - lastSendAt);
    lastSendAt = now;
    if (ws?.readyState === WebSocket.OPEN) ws.send(sender.build(now));
  }, 1000 / SEND_HZ);
}

function stopSending() {
  clearInterval(sendTimer);
  sendTimer = null;
}

function showKey(code, on) {
  document.querySelector(`kbd[data-k="${code}"]`)?.classList.toggle('on', on);
}

const typing = (e) => e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement
  || e.target instanceof HTMLTextAreaElement;

addEventListener('keydown', (e) => {
  if (typing(e) || !sender) return;
  if (sender.keyDown(e.code)) { e.preventDefault(); showKey(e.code, true); }
});
addEventListener('keyup', (e) => {
  if (!sender) return;
  if (sender.keyUp(e.code)) { e.preventDefault(); showKey(e.code, false); }
});
// ウィンドウから外れたり、タブが隠れたりしたら全キーを離したことにする（押しっぱなしで走り続けない）
function releaseAllKeys() {
  sender?.releaseAll();
  document.querySelectorAll('kbd.on').forEach((k) => k.classList.remove('on'));
}
addEventListener('blur', releaseAllKeys);
document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAllKeys(); });

// ---- 受信・表示 ----

const assembler = new FrameAssembler();
let frames = 0;
let rtts = [];
const drawMs = { sum: 0, max: 0, n: 0, dropped: 0 };

// 映像はワーカーで描く（設計書④-E1 2章）。モードは保存しておく
const enhanceSel = $('enhance');
const compareChk = $('compare');
const videoOut = createVideoOut($('video'), {
  mode: storage.get('mrc.enhance') ?? 'off',
  compare: storage.get('mrc.compare') === '1',
  onReady({ modes, webgl, reason }) {
    enhanceSel.replaceChildren(...modes.map((m) => new Option(m.label, m.id)));
    enhanceSel.value = modes.some((m) => m.id === storage.get('mrc.enhance')) ? storage.get('mrc.enhance') : 'off';
    enhanceSel.disabled = !webgl;
    compareChk.checked = storage.get('mrc.compare') === '1';
    if (!webgl) $('enh').textContent = `使えません（${reason ?? 'WebGL2 なし'}）`;
  },
  onDrawn({ decodeMs, drawMs: d, dropped }) {
    frames++;
    drawMs.sum += decodeMs + d;
    drawMs.max = Math.max(drawMs.max, decodeMs + d);
    drawMs.n++;
    drawMs.dropped = dropped;
    $('overlay').classList.add('hidden');
  },
  onError(message) { console.warn('映像の描画:', message); },
});

function setEnhance(mode) {
  enhanceSel.value = mode;
  storage.set('mrc.enhance', mode);
  videoOut.setMode(mode);
}
enhanceSel.addEventListener('change', () => { setEnhance(enhanceSel.value); unfocus(); });
compareChk.addEventListener('change', () => {
  storage.set('mrc.compare', compareChk.checked ? '1' : '0');
  videoOut.setCompare(compareChk.checked);
  unfocus();
});
// V キーで高画質化のモードを順に切り替える（操作キーとは別）
addEventListener('keydown', (e) => {
  if (e.code !== 'KeyV' || typing(e) || e.repeat || enhanceSel.disabled) return;
  const ids = [...enhanceSel.options].map((o) => o.value);
  setEnhance(ids[(ids.indexOf(enhanceSel.value) + 1) % ids.length]);
  e.preventDefault();
});

// 机上検証用：届いた JPEG を 1 枚だけ手元に保存する（実験ページで機体のカメラの癖を見るため）。
// 録画ではない。PC 内のサーバ（Phase 1-a）につないでいるときだけ出す。E1 の検証が終わったら削除する。
if (['127.0.0.1', 'localhost'].includes(location.hostname)) {
  $('grab').hidden = false;
  $('grab').addEventListener('click', async () => {
    unfocus();
    const jpeg = await videoOut.grab();
    if (!jpeg) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([jpeg], { type: 'image/jpeg' }));
    a.download = `frame-${new Date().toISOString().replace(/[:.]/g, '-')}.jpg`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
}

function onBinary(buf) {
  const h = decodeHeader(buf);
  if (!h) return;
  if (h.type === TYPE.TELEMETRY) onTelemetry(decodeTelemetry(buf));
  else if (h.type === TYPE.VIDEO) onVideo(decodeVideoChunk(buf));
  else if (h.type === TYPE.AUDIO) audio.push(decodeAudio(buf));
}

function onVideo(chunk) {
  const frame = assembler.push(chunk);
  if (frame) videoOut.push(frame.jpeg);
}

function onTelemetry(t) {
  if (!t) return;
  // 機体側の待ち時間が 255ms で頭打ちになっているときは、最後の操作が古すぎて往復遅延にならないので数えない
  if (sender && t.sessionId === sender.sessionId && t.holdMs < 255) {
    rtts.push(rttMs(performance.now(), t.sentAt, t.holdMs));
  }
  const v = t.vbatMv / 1000;
  $('vbat').textContent = `${v.toFixed(2)} V`;
  $('vbat').className = t.flags & FLAG.LOW_BATT_CUTOFF ? 'bad' : t.flags & FLAG.LOW_BATT_WARN ? 'warn' : '';
  $('rssi').textContent = `${t.rssi} dBm`;
  $('jump').textContent = `${JUMP_STATE[t.jumpState] ?? '?'}（ID ${t.lastJumpId}）`;
  $('jump').className = t.flags & FLAG.JUMP_FAULT ? 'bad' : '';
  const f = [];
  if (t.flags & FLAG.STOPPED) f.push('停止中');
  if (t.flags & FLAG.LOW_BATT_CUTOFF) f.push('低電圧で停止');
  else if (t.flags & FLAG.LOW_BATT_WARN) f.push('電池残量に注意');
  if (t.flags & FLAG.JUMP_FAULT) f.push('ジャンプ機構の異常');
  if (t.flags & FLAG.CAMERA_ON) f.push('撮影中');
  $('flags').textContent = f.join('・') || '走行可';
}

setInterval(() => {
  $('fps').textContent = `${frames} fps（欠け ${assembler.dropped}・間引き ${drawMs.dropped}）`;
  frames = 0;
  if (drawMs.n) {
    $('enh').textContent = `${(drawMs.sum / drawMs.n).toFixed(1)} ms（最大 ${drawMs.max.toFixed(1)}）`;
    drawMs.sum = 0; drawMs.max = 0; drawMs.n = 0;
  }
  if (sendTimer) {
    $('txgap').textContent = `最大 ${sendGapMax.toFixed(0)} ms`;
    $('txgap').className = sendGapMax > 100 ? 'bad' : sendGapMax > 40 ? 'warn' : '';
    sendGapMax = 0;
  } else {
    $('txgap').textContent = '—';
  }
  if (rtts.length) {
    const avg = rtts.reduce((a, b) => a + b, 0) / rtts.length;
    $('rtt').textContent = `${avg.toFixed(0)} ms（最大 ${Math.max(...rtts)}）`;
    $('rtt').className = avg > 300 ? 'bad' : avg > 150 ? 'warn' : '';
  } else {
    $('rtt').textContent = '—';
  }
  rtts = [];
}, 1000);

// ---- 音声（録音しない。届いた分を少しだけ先に予約して再生する）----

const audio = {
  ctx: null,
  gain: null,
  playhead: 0,
  start() {
    this.ctx = new AudioContext({ sampleRate: 16000 });
    // ギアのうなりや車体の振動を落とす（部品表「マイクについて」対策1）
    const hp = new BiquadFilterNode(this.ctx, { type: 'highpass', frequency: 150 });
    this.gain = new GainNode(this.ctx, { gain: 1 });
    hp.connect(this.gain).connect(this.ctx.destination);
    this.input = hp;
  },
  push(pkt) {
    if (!this.ctx || !pkt) return;
    const b = this.ctx.createBuffer(1, pkt.pcm.length, 16000);
    const ch = b.getChannelData(0);
    for (let i = 0; i < pkt.pcm.length; i++) ch[i] = pkt.pcm[i] / 32768;
    const now = this.ctx.currentTime;
    // 遅れが 250ms を超えたら詰める（溜めない）
    if (this.playhead < now || this.playhead > now + 0.25) this.playhead = now + 0.05;
    const src = new AudioBufferSourceNode(this.ctx, { buffer: b });
    src.connect(this.input);
    src.start(this.playhead);
    this.playhead += b.duration;
    // 走行中は音量を下げる（対策3。プライバシー面でも有利）
    this.gain.gain.value = sender?.keys & 0x0f ? 0.3 : 1;
  },
};
$('audio').disabled = false;
$('audio').addEventListener('click', () => {
  unfocus();
  if (audio.ctx) return;
  audio.start();
  $('audio').textContent = '音声 再生中';
  $('audio').disabled = true;
});

// ---- 体感ラグ計測用の時計 ----

const t0 = performance.now();
(function tick() {
  $('clock').textContent = ((performance.now() - t0) / 1000).toFixed(3);
  requestAnimationFrame(tick);
})();
