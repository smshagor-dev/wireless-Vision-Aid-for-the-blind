# WVAB Quick Start

## 1. Setup and deterministic diagnostics

WVAB requires Python 3.10+.

```bash
./quick_start.sh setup
./quick_start.sh doctor
```

The default doctor is offline-first and non-interactive. It does not require Internet connectivity or claim that hardware is field-safe. For deeper host validation:

```bash
./quick_start.sh doctor --full --camera 0 --tts
```

`--full` runs a local YOLO dummy-frame inference; `--camera` verifies a real camera/stream; `--tts` initializes the host TTS engine without asserting audible output.

## 2. Pair an ESP32-CAM with Raspberry Pi

Generate matching, git-ignored device credentials instead of editing keys into source:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

Flash `esp32_cam_stream.ino` with the generated `esp32_secrets.h` beside the sketch, then start the authenticated AES-GCM edge path:

```bash
./quick_start.sh run esp32
```

For station-mode Wi-Fi, pass `--station --ssid ... --wifi-password ... --server-ip ...` to the generator.

## 3. Optional MiDaS depth provisioning

The 85 MB MiDaS weight is not stored in the source tree. To prepare depth support for later offline use, run once while online after installing runtime dependencies:

```bash
python tools/download_models.py midas
```

The downloader verifies the model checksum and prepares the Torch Hub source cache. Core YOLO object detection remains available from the local `yolov8n.pt` baseline without MiDaS.

## 4. Secure Python UDP server/client

If the sender is another Python client instead of ESP32, export deployment-specific credentials and then run:

```bash
./quick_start.sh run udp-server
./quick_start.sh run udp-client 127.0.0.1
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
