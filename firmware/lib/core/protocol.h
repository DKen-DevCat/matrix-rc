// 通信プロトコル v1。仕様は docs/protocol.md、ブラウザ側は web/js/protocol.js。
#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace mrc {

constexpr uint8_t MAGIC = 0x4d;
constexpr uint8_t VERSION = 1;
enum : uint8_t { TYPE_CONTROL = 1, TYPE_TELEMETRY = 2, TYPE_HELLO = 3, TYPE_VIDEO = 4, TYPE_AUDIO = 5 };
enum : uint8_t { KEY_W = 1, KEY_A = 2, KEY_S = 4, KEY_D = 8, KEY_SPACE = 16 };
enum : uint8_t {
  FLAG_STOPPED = 1, FLAG_CHARGED = 2, FLAG_LOW_BATT_WARN = 4, FLAG_LOW_BATT_CUTOFF = 8,
  FLAG_JUMP_FAULT = 16, FLAG_CAMERA_ON = 32,
};

constexpr size_t HEADER_LEN = 4;
constexpr size_t CONTROL_LEN = 20;
constexpr size_t TELEMETRY_LEN = 28;
constexpr size_t HELLO_LEN = 20;
constexpr size_t TOKEN_LEN = 16;
constexpr size_t CHUNK_HEADER_LEN = 8;
constexpr size_t CHUNK_MAX = 240;  // Phase 2 の ESP-NOW（250 バイト）にそのまま載る大きさ

struct Control {
  uint8_t deviceId;
  uint32_t sessionId;
  uint32_t seq;
  uint32_t sentAt;
  uint8_t keys;
  uint16_t jumpId;
};

struct Telemetry {
  uint8_t deviceId;
  uint32_t sessionId;
  uint32_t seq;
  uint32_t sentAt;
  uint16_t vbatMv;
  uint8_t flags;
  int8_t rssi;
  uint16_t lastJumpId;
  uint8_t jumpState;
  uint8_t holdMs;  // 受け取ってからテレメトリを送るまでの時間（255 で頭打ち）
  uint32_t uptimeMs;
};

namespace detail {
inline uint16_t rd16(const uint8_t* p) { return uint16_t(p[0] | (p[1] << 8)); }
inline uint32_t rd32(const uint8_t* p) { return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24); }
inline void wr16(uint8_t* p, uint16_t v) { p[0] = v & 0xff; p[1] = v >> 8; }
inline void wr32(uint8_t* p, uint32_t v) { for (int i = 0; i < 4; i++) p[i] = (v >> (8 * i)) & 0xff; }
inline void header(uint8_t* b, uint8_t type, uint8_t deviceId) { b[0] = MAGIC; b[1] = VERSION; b[2] = type; b[3] = deviceId; }
}  // namespace detail

inline bool decodeControl(const uint8_t* b, size_t len, Control& c) {
  if (len != CONTROL_LEN || b[0] != MAGIC || b[1] != VERSION || b[2] != TYPE_CONTROL) return false;
  c.deviceId = b[3];
  c.sessionId = detail::rd32(b + 4);
  c.seq = detail::rd32(b + 8);
  c.sentAt = detail::rd32(b + 12);
  c.keys = b[16] & 0x1f;
  c.jumpId = detail::rd16(b + 18);
  return true;
}

inline size_t encodeTelemetry(const Telemetry& t, uint8_t* b) {
  detail::header(b, TYPE_TELEMETRY, t.deviceId);
  detail::wr32(b + 4, t.sessionId);
  detail::wr32(b + 8, t.seq);
  detail::wr32(b + 12, t.sentAt);
  detail::wr16(b + 16, t.vbatMv);
  b[18] = t.flags;
  b[19] = uint8_t(t.rssi);
  detail::wr16(b + 20, t.lastJumpId);
  b[22] = t.jumpState;
  b[23] = t.holdMs;
  detail::wr32(b + 24, t.uptimeMs);
  return TELEMETRY_LEN;
}

inline size_t encodeHello(uint8_t deviceId, const char* token, uint8_t* b) {
  detail::header(b, TYPE_HELLO, deviceId);
  std::memset(b + HEADER_LEN, 0, TOKEN_LEN);
  size_t n = std::strlen(token);
  std::memcpy(b + HEADER_LEN, token, n < TOKEN_LEN ? n : TOKEN_LEN);
  return HELLO_LEN;
}

inline uint8_t chunkCount(size_t len) { return uint8_t((len + CHUNK_MAX - 1) / CHUNK_MAX); }

// VIDEO と AUDIO は同じ 8 バイトのヘッダ（AUDIO では a=音声の連番, index/count=0）
inline size_t encodeChunk(uint8_t type, uint8_t deviceId, uint16_t id, uint8_t index, uint8_t count,
                          const uint8_t* data, size_t len, uint8_t* b) {
  detail::header(b, type, deviceId);
  detail::wr16(b + 4, id);
  b[6] = index;
  b[7] = count;
  std::memcpy(b + CHUNK_HEADER_LEN, data, len);
  return CHUNK_HEADER_LEN + len;
}

inline size_t encodeVideoChunk(uint8_t deviceId, uint16_t frameId, uint8_t index, uint8_t count,
                               const uint8_t* data, size_t len, uint8_t* b) {
  return encodeChunk(TYPE_VIDEO, deviceId, frameId, index, count, data, len, b);
}

inline size_t encodeAudio(uint8_t deviceId, uint16_t audioSeq, const int16_t* pcm, size_t samples, uint8_t* b) {
  detail::header(b, TYPE_AUDIO, deviceId);
  detail::wr16(b + 4, audioSeq);
  b[6] = 0;
  b[7] = 0;
  for (size_t i = 0; i < samples; i++) detail::wr16(b + CHUNK_HEADER_LEN + 2 * i, uint16_t(pcm[i]));
  return CHUNK_HEADER_LEN + 2 * samples;
}

}  // namespace mrc
