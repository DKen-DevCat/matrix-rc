// 依存なしの最小テスト枠。
#pragma once
#include <cmath>
#include <cstdio>
#include <functional>
#include <vector>

struct TestCase { const char* name; std::function<void()> fn; };
inline std::vector<TestCase>& tests() { static std::vector<TestCase> t; return t; }
inline int& failures() { static int f = 0; return f; }
struct Register { Register(const char* n, std::function<void()> f) { tests().push_back({n, f}); } };

#define TEST(name) static void name(); static Register reg_##name(#name, name); static void name()
#define CHECK(cond) do { if (!(cond)) { std::printf("  %s:%d: CHECK(%s)\n", __FILE__, __LINE__, #cond); failures()++; } } while (0)
#define CHECK_EQ(a, b) do { auto _a = (a); auto _b = (b); if (!(_a == _b)) { std::printf("  %s:%d: %s == %s (%lld vs %lld)\n", __FILE__, __LINE__, #a, #b, (long long)_a, (long long)_b); failures()++; } } while (0)
#define CHECK_NEAR(a, b) do { double _a = (a), _b = (b); if (std::fabs(_a - _b) > 1e-6) { std::printf("  %s:%d: %s ≈ %s (%f vs %f)\n", __FILE__, __LINE__, #a, #b, _a, _b); failures()++; } } while (0)

inline int runAll() {
  for (auto& t : tests()) {
    int before = failures();
    t.fn();
    std::printf("%s %s\n", failures() == before ? "ok  " : "FAIL", t.name);
  }
  std::printf("%zu tests, %d failures\n", tests().size(), failures());
  return failures() ? 1 : 0;
}
