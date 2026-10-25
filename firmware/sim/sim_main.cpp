// PC 上で動く機体シミュレータ。実機と同じ lib/core の判断ロジックを使い、
// モーターの代わりに出力を表示する。部品が届く前にブラウザ⇄サーバ⇄機体を通しで試すためのもの。
//   make sim && ./build/sim --server 127.0.0.1:9000 --token xxxx [--jpeg photo.jpg] [--loss 0.1]
#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <random>
#include <string>
#include <thread>
#include <vector>

#include "vehicle.h"

using namespace mrc;

static uint32_t millisNow() {
  using namespace std::chrono;
  static auto t0 = steady_clock::now();
  return uint32_t(duration_cast<milliseconds>(steady_clock::now() - t0).count());
}

// 渦巻きカムの模型：モーターが回っている間だけ位置が進む。1 周 3.5 秒。
// 0.95〜1.0 の位置で「縮みきった」のでスイッチが押され、1.0 を越えるとばねが開放される。
struct CamModel {
  double pos = 0.97;
  int jumps = 0;
  void advance(bool motorOn, double dtMs) {
    if (!motorOn) return;
    pos += dtMs / 3500.0;
    if (pos >= 1.0) { pos -= 1.0; jumps++; std::printf("\n*** ジャンプ！（%d 回目）***\n", jumps); }
  }
  bool pressed() const { return pos >= 0.95; }
};

int main(int argc, char** argv) {
  std::string server = "127.0.0.1:9000", token, jpegPath;
  int deviceId = 1;
  double loss = 0;
  for (int i = 1; i + 1 < argc; i += 2) {
    std::string k = argv[i], v = argv[i + 1];
    if (k == "--server") server = v;
    else if (k == "--token") token = v;
    else if (k == "--jpeg") jpegPath = v;
    else if (k == "--device") deviceId = std::atoi(v.c_str());
    else if (k == "--loss") loss = std::atof(v.c_str());
  }
  if (token.empty()) { std::fprintf(stderr, "--token が必要です\n"); return 1; }

  std::vector<uint8_t> jpeg;
  if (!jpegPath.empty()) {
    std::ifstream f(jpegPath, std::ios::binary);
    jpeg.assign(std::istreambuf_iterator<char>(f), {});
    if (jpeg.empty() || chunkCount(jpeg.size()) > 255) { std::fprintf(stderr, "JPEG を読めないか大きすぎます\n"); return 1; }
  }

  auto colon = server.rfind(':');
  sockaddr_in srv{};
  srv.sin_family = AF_INET;
  srv.sin_port = htons(uint16_t(std::atoi(server.substr(colon + 1).c_str())));
  inet_pton(AF_INET, server.substr(0, colon).c_str(), &srv.sin_addr);

  int sock = socket(AF_INET, SOCK_DGRAM, 0);
  fcntl(sock, F_SETFL, O_NONBLOCK);
  auto sendBuf = [&](const uint8_t* b, size_t n) { sendto(sock, b, n, 0, (sockaddr*)&srv, sizeof srv); };

  Vehicle car(uint8_t(deviceId), 0.8f);
  CamModel cam;
  std::mt19937 rng(42);
  std::uniform_real_distribution<double> uni(0, 1);
  uint32_t lastHello = 0, lastTelem = 0, lastFrame = 0, lastStep = millisNow();
  uint16_t frameId = 0;
  std::printf("シミュレータ起動：サーバ %s、機体ID %d、パケット損失 %.0f%%\n", server.c_str(), deviceId, loss * 100);

  for (;;) {
    uint32_t now = millisNow();
    uint8_t buf[512];
    sockaddr_in from{};
    socklen_t fl = sizeof from;
    ssize_t n;
    while ((n = recvfrom(sock, buf, sizeof buf, 0, (sockaddr*)&from, &fl)) > 0) {
      // サーバ以外からのパケットは捨てる（実機と同じ）
      if (from.sin_addr.s_addr != srv.sin_addr.s_addr || from.sin_port != srv.sin_port) continue;
      if (uni(rng) < loss) continue;
      car.onPacket(buf, size_t(n), now);
    }

    Outputs o = car.step(now, cam.pressed(), 3900);
    cam.advance(o.jumpMotor, double(now - lastStep));
    lastStep = now;

    if (now - lastHello >= 1000) {
      uint8_t h[HELLO_LEN];
      sendBuf(h, encodeHello(uint8_t(deviceId), token.c_str(), h));
      lastHello = now;
    }
    if (now - lastTelem >= 100) {
      uint8_t t[TELEMETRY_LEN];
      sendBuf(t, encodeTelemetry(car.telemetry(now, -45, !jpeg.empty()), t));
      lastTelem = now;
      std::printf("\r左 %+5.2f 右 %+5.2f ジャンプ用 %s カム %.2f %s   ", o.drive.left, o.drive.right,
                  o.jumpMotor ? "回転" : "停止", cam.pos, car.stopped() ? "[停止中]" : "[操作中]");
      std::fflush(stdout);
    }
    if (!jpeg.empty() && now - lastFrame >= 100) {
      uint8_t count = chunkCount(jpeg.size());
      for (uint8_t i = 0; i < count; i++) {
        size_t off = size_t(i) * CHUNK_MAX, len = std::min(CHUNK_MAX, jpeg.size() - off);
        uint8_t c[CHUNK_HEADER_LEN + CHUNK_MAX];
        if (uni(rng) >= loss) sendBuf(c, encodeVideoChunk(uint8_t(deviceId), frameId, i, count, jpeg.data() + off, len, c));
      }
      frameId++;
      lastFrame = now;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
}
