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
