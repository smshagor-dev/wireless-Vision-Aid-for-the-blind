# WVAB Quick Start

## 1) One-command startup (Linux/Raspberry Pi)

```bash
chmod +x quick_start.sh
./quick_start.sh setup
./quick_start.sh doctor
./quick_start.sh run esp32
```

Other run modes:

```bash
./quick_start.sh run phone
./quick_start.sh run udp-server
./quick_start.sh run udp-client 192.168.1.10
```

## 2) Cheap real-life C++ planner module

Files:
- `cpp/navigation_planner.h`
- `cpp/navigation_planner.cpp`

This module takes detections (`class_name`, `confidence`, bbox center/area) and returns:
- `GO LEFT`
- `GO RIGHT`
- `GO STRAIGHT`
- `SLOW - path blocked ahead`
- `STOP - obstacle very close`

## 3) Build C++ demo

Using CMake:

```bash
cd cpp
cmake -S . -B build
cmake --build build --config Release
./build/navigation_demo
```

Or with g++ directly:

```bash
g++ -std=c++17 -O2 -Icpp cpp/navigation_planner.cpp cpp/main_demo.cpp -o navigation_demo
./navigation_demo
```

