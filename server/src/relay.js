// ブラウザ（WebSocket）と機体（UDP）の中継。ネットワーク入出力は外から渡す。
// 方針（設計書①6章）：操作は補完せず素通しする。機体は HELLO の送信元にだけ送る。
import { timingSafeEqual } from 'node:crypto';
import {
  TYPE, CONTROL_LEN, decodeHeader, decodeHello, decodeControl, decodeTelemetry,
} from '../../web/js/protocol.js';

const DEVICE_TIMEOUT_MS = 3000;
const AUTH_TIMEOUT_MS = 2000;
const SEQ_HISTORY = 64;

function sameToken(a, b) {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

export class Relay {
  constructor({ token, sendUdp, now = Date.now, log = () => {} }) {
    this.token = token;
    this.sendUdp = sendUdp;
    this.now = now;
    this.log = log;
    this.devices = new Map(); // deviceId → { addr, lastSeen, sent: Map(seq → 時刻) }
    this.clients = new Set();
    this.operators = new Map(); // deviceId → client
  }

  deviceOnline(id) {
    const d = this.devices.get(id);
    return !!d && this.now() - d.lastSeen < DEVICE_TIMEOUT_MS;
  }

  onUdp(buf, rinfo) {
    const h = decodeHeader(buf);
    if (!h) return;
    const addr = { address: rinfo.address, port: rinfo.port };
    if (h.type === TYPE.HELLO) return this.#onHello(buf, addr);

    const dev = this.devices.get(h.deviceId);
    if (!dev || dev.addr.address !== addr.address || dev.addr.port !== addr.port) return;
    if (h.type === TYPE.TELEMETRY) this.#onTelemetry(dev, buf);
    if (h.type === TYPE.TELEMETRY || h.type === TYPE.VIDEO || h.type === TYPE.AUDIO) {
      for (const c of this.clients) if (c.authed && c.deviceId === h.deviceId) c.ws.send(buf);
    }
  }

  #onHello(buf, addr) {
    const hello = decodeHello(buf);
    if (!hello || !sameToken(hello.token, this.token)) {
      this.log({ event: 'hello_rejected', from: `${addr.address}:${addr.port}` });
      return;
    }
    const prev = this.devices.get(hello.deviceId);
    const wasOnline = this.deviceOnline(hello.deviceId);
    const moved = prev && (prev.addr.address !== addr.address || prev.addr.port !== addr.port);
    this.devices.set(hello.deviceId, { addr, lastSeen: this.now(), sent: prev?.sent ?? new Map() });
    if (!wasOnline || moved) {
      this.log({ event: 'device_online', deviceId: hello.deviceId, from: `${addr.address}:${addr.port}` });
      this.#broadcastStatus(hello.deviceId);
    }
  }

  #onTelemetry(dev, buf) {
    const t = decodeTelemetry(buf);
    if (!t) return;
    const sentAt = dev.sent.get(t.seq);
    if (sentAt === undefined) return;
    dev.sent.delete(t.seq);
    this.log({ event: 'rtt', deviceId: t.deviceId, seq: t.seq, ms: this.now() - sentAt, vbatMv: t.vbatMv, rssi: t.rssi });
  }

  addClient(ws) {
    const c = { ws, authed: false, deviceId: null, connectedAt: this.now() };
    this.clients.add(c);
    return {
      onText: (text) => this.#onClientText(c, text),
      onBinary: (buf) => this.#onClientBinary(c, buf),
      onClose: () => this.#removeClient(c),
    };
  }

  #onClientText(c, text) {
    let msg;
    try { msg = JSON.parse(text); } catch { return; }
    if (msg.type === 'auth' && !c.authed) {
      if (typeof msg.token !== 'string' || !sameToken(msg.token, this.token)) {
        this.log({ event: 'client_rejected' });
        c.ws.close();
        this.clients.delete(c);
        return;
      }
      c.authed = true;
      c.deviceId = Number.isInteger(msg.deviceId) ? msg.deviceId : 1;
      this.#claim(c);
      this.#sendStatus(c);
    } else if (msg.type === 'claim' && c.authed) {
      this.#claim(c);
      this.#sendStatus(c);
    }
  }

  #claim(c) {
    if (this.operators.has(c.deviceId)) return;
    this.operators.set(c.deviceId, c);
    this.log({ event: 'operator', deviceId: c.deviceId });
    this.#broadcastStatus(c.deviceId);
  }

  #onClientBinary(c, buf) {
    if (!c.authed || this.operators.get(c.deviceId) !== c) return;
    if (buf.length !== CONTROL_LEN) return;
    const ctl = decodeControl(buf);
    if (!ctl || ctl.deviceId !== c.deviceId) return;
    const dev = this.devices.get(ctl.deviceId);
    if (!dev || !this.deviceOnline(ctl.deviceId)) return;
    dev.sent.set(ctl.seq, this.now());
    if (dev.sent.size > SEQ_HISTORY) dev.sent.delete(dev.sent.keys().next().value);
    this.sendUdp(buf, dev.addr);
  }

  #removeClient(c) {
    this.clients.delete(c);
    if (this.operators.get(c.deviceId) === c) {
      this.operators.delete(c.deviceId);
      this.log({ event: 'operator_left', deviceId: c.deviceId });
      this.#broadcastStatus(c.deviceId);
    }
  }

  #sendStatus(c) {
    const op = this.operators.get(c.deviceId);
    c.ws.send(JSON.stringify({
      type: 'status',
      deviceId: c.deviceId,
      deviceOnline: this.deviceOnline(c.deviceId),
      role: op === c ? 'operator' : 'viewer',
      operatorPresent: !!op,
    }));
  }

  #broadcastStatus(deviceId) {
    for (const c of this.clients) if (c.authed && c.deviceId === deviceId) this.#sendStatus(c);
  }

  // 定期的に呼ぶ（認証の期限切れと、機体のオフライン判定）
  tick() {
    const now = this.now();
    for (const c of this.clients) {
      if (!c.authed && now - c.connectedAt > AUTH_TIMEOUT_MS) {
        c.ws.close();
        this.clients.delete(c);
      }
    }
    for (const [id, d] of this.devices) {
      if (!d.offlineNotified && now - d.lastSeen >= DEVICE_TIMEOUT_MS) {
        d.offlineNotified = true;
        this.log({ event: 'device_offline', deviceId: id });
        this.#broadcastStatus(id);
      }
    }
  }
}
