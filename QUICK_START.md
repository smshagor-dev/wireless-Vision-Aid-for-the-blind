# WVAB Quick Start

## 1. Setup and diagnostics

WVAB requires Python 3.10+.

```bash
./quick_start.sh setup
./quick_start.sh doctor
```

Normal camera helpers:

```bash
./quick_start.sh run esp32
./quick_start.sh run phone
```

## 2. Pair an ESP32-CAM with Raspberry Pi

Generate matching, git-ignored device credentials instead of editing keys into source:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
```

Flash `esp32_cam_stream.ino` with the generated `esp32_secrets.h` in the sketch directory, then start the edge server:

```bash
bash deployment/rpi/wvab_edge_start.sh
```

For station-mode Wi-Fi, pass `--station --ssid ... --wifi-password ... --server-ip ...` to the generator.

## 3. Optional MiDaS depth provisioning

The 85 MB MiDaS weight is not stored in the source tree. To prepare depth support for later offline use, run once while online after installing runtime dependencies:

```bash
python tools/download_models.py midas
```

The downloader verifies the model checksum and prepares the Torch Hub source cache. Core YOLO object detection remains available from the local `yolov8n.pt` baseline without MiDaS.

## 4. Secure Python UDP server/client

If the sender is another Python client instead of ESP32, generate/export deployment-specific credentials and then run:

```bash
python udp_streaming.py server --config wvab_config.sample.json
python udp_streaming.py client --config wvab_config.sample.json --server-ip 127.0.0.1 --camera 0
```

The runtime refuses encrypted/authenticated mode when key/token configuration is invalid. WebSocket control is loopback-only by default and requires a token for every command.

## 5. C++ planner experiment

Build with CMake:

```bash
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release
```

Or directly with g++:

```bash
g++ -std=c++17 -O2 -Icpp cpp/navigation_planner.cpp cpp/main_demo.cpp -o navigation_demo
./navigation_demo
```

The planner output is experimental and is not a certified mobility-safety controller. `cpp/build/` is intentionally ignored.
