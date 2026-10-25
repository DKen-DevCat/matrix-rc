# PC 上で機体の判断ロジック（lib/core）をテストする。実機のビルドは PlatformIO（platformio.ini）。
CXX ?= c++
CXXFLAGS = -std=c++17 -Wall -Wextra -Werror -Ilib/core -Itest

.PHONY: test sim clean
test: build/test_core
	./build/test_core

build/test_core: test/test_core.cpp test/check.h $(wildcard lib/core/*.h)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ test/test_core.cpp

sim: build/sim
build/sim: sim/sim_main.cpp $(wildcard lib/core/*.h)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ sim/sim_main.cpp

clean:
	rm -rf build
