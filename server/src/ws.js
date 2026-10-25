// 依存パッケージなしの最小 WebSocket サーバ（RFC 6455 のうち、ブラウザとの通信に要る部分だけ）。
// 対応：テキスト／バイナリ、分割フレーム、ping/pong、close。拡張（圧縮など）には対応しない。
import { createHash } from 'node:crypto';

const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
const MAX_MESSAGE = 1024 * 1024;
const OP = { CONT: 0x0, TEXT: 0x1, BIN: 0x2, CLOSE: 0x8, PING: 0x9, PONG: 0xa };

function frame(opcode, payload) {
  const len = payload.length;
  let head;
  if (len < 126) {
    head = Buffer.from([0x80 | opcode, len]);
  } else if (len < 65536) {
    head = Buffer.alloc(4);
    head[0] = 0x80 | opcode; head[1] = 126; head.writeUInt16BE(len, 2);
  } else {
    head = Buffer.alloc(10);
    head[0] = 0x80 | opcode; head[1] = 127; head.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([head, payload]);
}

class Connection {
  constructor(socket, head) {
    this.socket = socket;
    this.buf = Buffer.alloc(0);
    this.parts = [];
    this.partsOp = 0;
    this.closed = false;
    this.onText = () => {};
    this.onBinary = () => {};
    this.onClose = () => {};
    socket.on('data', (d) => this.#onData(d));
    socket.on('close', () => this.#finish());
    socket.on('error', () => this.#finish());
    // ハンドシェイクと同じ TCP セグメントに最初のフレームが入っていることがある（head）。捨てずに処理する
    if (head?.length) queueMicrotask(() => this.#onData(head));
  }

  send(data) {
    if (this.closed) return;
    if (typeof data === 'string') this.socket.write(frame(OP.TEXT, Buffer.from(data)));
    else this.socket.write(frame(OP.BIN, Buffer.from(data.buffer, data.byteOffset, data.byteLength)));
  }

  close(code = 1000) {
    if (this.closed) return;
    const p = Buffer.alloc(2); p.writeUInt16BE(code);
    this.socket.end(frame(OP.CLOSE, p));
    this.#finish();
  }

  #finish() {
    if (this.closed) return;
    this.closed = true;
    this.onClose();
  }

  #onData(chunk) {
    this.buf = Buffer.concat([this.buf, chunk]);
    while (!this.closed) {
      const b = this.buf;
      if (b.length < 2) return;
      const fin = (b[0] & 0x80) !== 0;
      const opcode = b[0] & 0x0f;
      const masked = (b[1] & 0x80) !== 0;
      let len = b[1] & 0x7f;
      let off = 2;
      if (len === 126) {
        if (b.length < 4) return;
        len = b.readUInt16BE(2); off = 4;
      } else if (len === 127) {
        if (b.length < 10) return;
        const big = b.readBigUInt64BE(2);
        if (big > BigInt(MAX_MESSAGE)) return this.close(1009);
        len = Number(big); off = 10;
      }
      if (!masked) return this.close(1002); // ブラウザからのフレームは必ずマスクされる
      if (len > MAX_MESSAGE) return this.close(1009);
      if (b.length < off + 4 + len) return;
      const mask = b.subarray(off, off + 4);
      const payload = Buffer.from(b.subarray(off + 4, off + 4 + len));
      for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i & 3];
      this.buf = b.subarray(off + 4 + len);
      this.#onFrame(fin, opcode, payload);
    }
  }

  #onFrame(fin, opcode, payload) {
    if (opcode === OP.PING) return this.socket.write(frame(OP.PONG, payload));
    if (opcode === OP.PONG) return;
    if (opcode === OP.CLOSE) return this.close();
    if (opcode === OP.TEXT || opcode === OP.BIN) {
      this.partsOp = opcode;
      this.parts = [payload];
    } else if (opcode === OP.CONT && this.parts.length) {
      this.parts.push(payload);
    } else {
      return this.close(1002);
    }
    const size = this.parts.reduce((n, p) => n + p.length, 0);
    if (size > MAX_MESSAGE) return this.close(1009);
    if (!fin) return;
    const msg = Buffer.concat(this.parts);
    this.parts = [];
    // 受け手の例外で中継サーバ全体が落ちないよう、その接続だけを閉じる
    try {
      if (this.partsOp === OP.TEXT) this.onText(msg.toString('utf8'));
      else this.onBinary(new Uint8Array(msg.buffer, msg.byteOffset, msg.byteLength));
    } catch (e) {
      console.error('WebSocket メッセージの処理に失敗', e);
      this.close(1011);
    }
  }
}

// Origin が付いていれば、操作画面を配った同じホストからの接続だけを受ける
// （別のサイトを開いたブラウザから、このサーバの WebSocket を勝手に使われないように）。
// Origin を付けない接続（ブラウザ以外）はトークンの照合だけに任せる。
function originAllowed(req) {
  const origin = req.headers.origin;
  if (!origin) return true;
  try { return new URL(origin).host === req.headers.host; } catch { return false; }
}

// http サーバの path に WebSocket を受け付ける。接続ごとに onConnection(conn, req) を呼ぶ。
export function attachWebSocket(server, path, onConnection) {
  server.on('upgrade', (req, socket, head) => {
    const url = new URL(req.url, 'http://x');
    const key = req.headers['sec-websocket-key'];
    if (url.pathname !== path || req.headers.upgrade?.toLowerCase() !== 'websocket' || !key
        || req.headers['sec-websocket-version'] !== '13') {
      socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
      return;
    }
    if (!originAllowed(req)) {
      socket.end('HTTP/1.1 403 Forbidden\r\n\r\n');
      return;
    }
    const accept = createHash('sha1').update(key + GUID).digest('base64');
    socket.write(
      'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
      + `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
    );
    socket.setNoDelay(true);
    onConnection(new Connection(socket, head), req);
  });
}
