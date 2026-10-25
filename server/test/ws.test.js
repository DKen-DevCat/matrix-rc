import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { attachWebSocket } from '../src/ws.js';

async function withServer(onConnection, fn) {
  const http = createServer((_, res) => res.end('ok'));
  attachWebSocket(http, '/ws', onConnection);
  await new Promise((r) => http.listen(0, '127.0.0.1', r));
  const url = `ws://127.0.0.1:${http.address().port}/ws`;
  try { await fn(url); } finally { http.closeAllConnections(); http.close(); }
}

const open = (url) => new Promise((resolve, reject) => {
  const ws = new WebSocket(url);
  ws.binaryType = 'arraybuffer';
  ws.onopen = () => resolve(ws);
  ws.onerror = reject;
});
const next = (ws) => new Promise((r) => { ws.onmessage = (e) => r(e.data); });

test('テキストとバイナリを往復できる', async () => {
  await withServer((conn) => {
    conn.onText = (t) => conn.send(`echo:${t}`);
    conn.onBinary = (b) => conn.send(Uint8Array.from(b, (x) => x + 1));
  }, async (url) => {
    const ws = await open(url);
    ws.send('hello');
    assert.equal(await next(ws), 'echo:hello');
    ws.send(new Uint8Array([1, 2, 3]));
    assert.deepEqual([...new Uint8Array(await next(ws))], [2, 3, 4]);
    ws.close();
  });
});

test('126 バイト以上と 65536 バイト以上の長さを扱える', async () => {
  await withServer((conn) => { conn.onBinary = (b) => conn.send(b); }, async (url) => {
    const ws = await open(url);
    for (const n of [200, 70000]) {
      const data = Uint8Array.from({ length: n }, (_, i) => i & 0xff);
      ws.send(data);
      assert.deepEqual(new Uint8Array(await next(ws)), data);
    }
    ws.close();
  });
});

test('サーバから閉じるとブラウザ側に close が届き、onClose が呼ばれる', async () => {
  let closed = false;
  await withServer((conn) => {
    conn.onClose = () => { closed = true; };
    conn.onText = () => conn.close();
  }, async (url) => {
    const ws = await open(url);
    const done = new Promise((r) => { ws.onclose = r; });
    ws.send('bye');
    await done;
  });
  assert.equal(closed, true);
});

test('パスが違う接続は拒否する', async () => {
  await withServer(() => {}, async (url) => {
    await assert.rejects(open(url.replace('/ws', '/other')));
  });
});

test('上限を超える大きさのフレームは切断する', async () => {
  await withServer((conn) => { conn.onBinary = () => {}; }, async (url) => {
    const ws = await open(url);
    const done = new Promise((r) => { ws.onclose = (e) => r(e.code); });
    ws.send(new Uint8Array(2 * 1024 * 1024));
    assert.equal(await done, 1009);
  });
});

// ---- ブラウザでは作れない形の接続は、生の TCP で確かめる ----
import { connect as tcpConnect } from 'node:net';

function handshake(port, extraHeaders = '') {
  return 'GET /ws HTTP/1.1\r\n'
    + `Host: 127.0.0.1:${port}\r\n`
    + 'Upgrade: websocket\r\nConnection: Upgrade\r\n'
    + 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n'
    + extraHeaders + '\r\n';
}

// マスク付きのテキストフレーム（クライアント→サーバの形）
function maskedText(text) {
  const payload = Buffer.from(text);
  const mask = Buffer.from([1, 2, 3, 4]);
  const out = Buffer.alloc(2 + 4 + payload.length);
  out[0] = 0x81; out[1] = 0x80 | payload.length;
  mask.copy(out, 2);
  for (let i = 0; i < payload.length; i++) out[6 + i] = payload[i] ^ mask[i & 3];
  return out;
}

const rawSession = (url, send) => new Promise((resolve) => {
  const port = Number(new URL(url).port);
  const sock = tcpConnect(port, '127.0.0.1', () => sock.write(send(port)));
  const chunks = [];
  sock.on('data', (d) => chunks.push(d));
  sock.on('close', () => resolve(Buffer.concat(chunks).toString('latin1')));
  setTimeout(() => sock.destroy(), 300).unref();
});

test('ハンドシェイクと同じセグメントに入っていた最初のフレームも取りこぼさない', async () => {
  const got = [];
  await withServer((conn) => { conn.onText = (t) => { got.push(t); conn.close(); }; }, async (url) => {
    const res = await rawSession(url, (port) => Buffer.concat([Buffer.from(handshake(port)), maskedText('first')]));
    assert.match(res, /^HTTP\/1\.1 101/);
  });
  assert.deepEqual(got, ['first']);
});

test('別のサイト（Origin が違う）からの接続は拒否する。同じホストなら受け付ける', async () => {
  let connections = 0;
  await withServer(() => { connections++; }, async (url) => {
    const bad = await rawSession(url, (port) => handshake(port, 'Origin: http://evil.example\r\n'));
    assert.match(bad, /^HTTP\/1\.1 403/);
    const good = await rawSession(url, (port) => handshake(port, `Origin: http://127.0.0.1:${port}\r\n`));
    assert.match(good, /^HTTP\/1\.1 101/);
  });
  assert.equal(connections, 1);
});

test('Sec-WebSocket-Version が 13 でなければ拒否する', async () => {
  await withServer(() => {}, async (url) => {
    const res = await rawSession(url, (port) => handshake(port).replace('Version: 13', 'Version: 8'));
    assert.match(res, /^HTTP\/1\.1 400/);
  });
});

test('メッセージの処理で例外が出ても、その接続を閉じるだけでサーバは生きている', async () => {
  await withServer((conn) => { conn.onText = () => { throw new Error('boom'); }; }, async (url) => {
    const a = await open(url);
    const closed = new Promise((r) => { a.onclose = (e) => r(e.code); });
    a.send('x');
    assert.equal(await closed, 1011);
    const b = await open(url);  // まだ接続できる
    b.close();
  });
});
