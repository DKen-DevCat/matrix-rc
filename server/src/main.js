// 中継サーバの起動。Phase 1-a は PC 上で動かす（設計書①6章）。
//   MRC_TOKEN=xxxx npm start
// 環境変数：
//   MRC_TOKEN      共有トークン（必須、16 バイト以内。機体の secrets.h と同じ値）
//   MRC_HTTP_HOST  操作画面を出すアドレス（既定 127.0.0.1＝この PC だけ）
//   MRC_HTTP_PORT  既定 8080
//   MRC_UDP_PORT   機体からの接続を受ける UDP ポート（既定 9000。LAN 内の機体から届くよう 0.0.0.0 で待つ）
import { createServer } from 'node:http';
import { createSocket } from 'node:dgram';
import { readFile, mkdir, appendFile } from 'node:fs/promises';
import { join, normalize, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { attachWebSocket } from './ws.js';
import { Relay } from './relay.js';
import { TOKEN_LEN } from '../../web/js/protocol.js';

const here = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = normalize(join(here, '../../web'));
const LOG_DIR = join(here, '../logs');

const token = process.env.MRC_TOKEN;
if (!token || Buffer.byteLength(token) > TOKEN_LEN || Buffer.byteLength(token) < 8) {
  console.error(`MRC_TOKEN を 8〜${TOKEN_LEN} バイトで指定してください（機体の secrets.h と同じ値）`);
  process.exit(1);
}
const httpHost = process.env.MRC_HTTP_HOST ?? '127.0.0.1';
const httpPort = Number(process.env.MRC_HTTP_PORT ?? 8080);
const udpPort = Number(process.env.MRC_UDP_PORT ?? 9000);

await mkdir(LOG_DIR, { recursive: true });
const logFile = join(LOG_DIR, `${new Date().toISOString().slice(0, 10)}.jsonl`);
let logQueue = Promise.resolve();
function log(obj) {
  const line = JSON.stringify({ t: new Date().toISOString(), ...obj });
  if (obj.event !== 'rtt') console.log(line);
  logQueue = logQueue.then(() => appendFile(logFile, line + '\n')).catch(() => {});
}

const udp = createSocket('udp4');
const relay = new Relay({ token, log, sendUdp: (buf, a) => udp.send(buf, a.port, a.address) });
udp.on('message', (msg, rinfo) => relay.onUdp(new Uint8Array(msg.buffer, msg.byteOffset, msg.byteLength), rinfo));
udp.bind(udpPort, '0.0.0.0');

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8' };
const http = createServer(async (req, res) => {
  const path = new URL(req.url, 'http://x').pathname;
  const file = normalize(join(WEB_ROOT, path === '/' ? 'index.html' : path));
  if (!file.startsWith(WEB_ROOT + '/') || !MIME[extname(file)]) {
    res.writeHead(404).end();
    return;
  }
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'content-type': MIME[extname(file)], 'cache-control': 'no-store' }).end(body);
  } catch {
    res.writeHead(404).end();
  }
});
attachWebSocket(http, '/ws', (conn) => {
  const h = relay.addClient(conn);
  conn.onText = h.onText;
  conn.onBinary = h.onBinary;
  conn.onClose = h.onClose;
});
http.listen(httpPort, httpHost, () => {
  log({ event: 'start', http: `http://${httpHost}:${httpPort}/`, udp: udpPort, logFile });
});
setInterval(() => relay.tick(), 200);
