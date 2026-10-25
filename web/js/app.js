// 操作画面。キー状態を 50Hz で送り、映像・音声・テレメトリを表示する（設計書① 6章）。
import {
  TYPE, FLAG, JUMP_STATE, decodeHeader, decodeTelemetry, decodeVideoChunk, decodeAudio, FrameAssembler,
} from './protocol.js';
import { ControlSender, rttMs } from './control.js';

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

// ---- 接続 ----

$('token').value = storage.get('mrc.token') ?? '';
$('login').addEventListener('submit', (e) => {
  e.preventDefault();
  storage.set('mrc.token', $('token').value);
  connect($('token').value, Number($('device').value));
});
$('claim').addEventListener('click', () => ws?.send(JSON.stringify({ type: 'claim' })));

function setStatus(text, cls) {
  $('status').textContent = text;
  $('status').className = `pill ${cls ?? ''}`;
}

function connect(token, deviceId) {
  ws?.close();
  ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  ws.binaryType = 'arraybuffer';
  // 接続ごとに新しいセッションID（機体は停止中にだけ新しいセッションを受け入れる）
  sender = new ControlSender({ deviceId });
  setStatus('接続中…');
  ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token, deviceId }));
  ws.onclose = () => {
    stopSending();
    setStatus('切断', 'bad');
    $('claim').hidden = true;
  };
  ws.onmessage = (e) => (typeof e.data === 'string' ? onStatus(JSON.parse(e.data)) : onBinary(new Uint8Array(e.data)));
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
  sendTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(sender.build(performance.now()));
  }, 1000 / SEND_HZ);
}

function stopSending() {
  clearInterval(sendTimer);
  sendTimer = null;
}

function showKey(code, on) {
  document.querySelector(`kbd[data-k="${code}"]`)?.classList.toggle('on', on);
}

addEventListener('keydown', (e) => {
  if (e.target instanceof HTMLInputElement || !sender) return;
  if (sender.keyDown(e.code)) { e.preventDefault(); showKey(e.code, true); }
});
addEventListener('keyup', (e) => {
  if (!sender) return;
  if (sender.keyUp(e.code)) { e.preventDefault(); showKey(e.code, false); }
});
addEventListener('blur', () => {
  sender?.releaseAll();
  document.querySelectorAll('kbd.on').forEach((k) => k.classList.remove('on'));
});

// ---- 受信 ----

const canvas = $('video');
const ctx2d = canvas.getContext('2d');
const assembler = new FrameAssembler();
let frames = 0;
let decoding = false;
let rtts = [];

function onBinary(buf) {
  const h = decodeHeader(buf);
  if (!h) return;
  if (h.type === TYPE.TELEMETRY) onTelemetry(decodeTelemetry(buf));
  else if (h.type === TYPE.VIDEO) onVideo(decodeVideoChunk(buf));
  else if (h.type === TYPE.AUDIO) audio.push(decodeAudio(buf));
}

function onVideo(chunk) {
  const frame = assembler.push(chunk);
  // 前のフレームを描いている途中なら捨てる（溜めない）
  if (!frame || decoding) return;
  decoding = true;
  createImageBitmap(new Blob([frame.jpeg], { type: 'image/jpeg' }))
    .then((bmp) => {
      if (canvas.width !== bmp.width) { canvas.width = bmp.width; canvas.height = bmp.height; }
      ctx2d.drawImage(bmp, 0, 0);
      bmp.close();
      frames++;
      $('overlay').classList.add('hidden');
    })
    .catch(() => {})
    .finally(() => { decoding = false; });
}

function onTelemetry(t) {
  if (!t) return;
  if (sender && t.sessionId === sender.sessionId) rtts.push(rttMs(performance.now(), t.sentAt, t.holdMs));
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
  $('fps').textContent = `${frames} fps（欠け ${assembler.dropped}）`;
  frames = 0;
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
