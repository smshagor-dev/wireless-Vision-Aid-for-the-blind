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

## 2. Optional MiDaS depth provisioning

The 85 MB MiDaS weight is not stored in the source tree. To prepare depth support for later offline use, run once while online after installing runtime dependencies:

```bash
python tools/download_models.py midas
```

The downloader verifies the model checksum and prepares the Torch Hub source cache. Core YOLO object detection remains available from the local `yolov8n.pt` baseline without MiDaS.

## 3. Secure UDP server/client

Generate deployment-specific credentials and export them before using UDP mode:

```bash
export WVAB_UDP_KEY_HEX="$(python - <<'PY'
import os
print(os.urandom(32).hex())
PY
)"
export WVAB_UDP_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
```

Then start the server and sender:

```bash
./quick_start.sh run udp-server
./quick_start.sh run udp-client 192.168.1.10
```

The quick-start script refuses UDP mode when the token is blank or the AES key length is invalid. WebSocket control is loopback-only by default and uses `WVAB_WS_TOKEN` when set, otherwise it reuses `WVAB_UDP_TOKEN`.

## 4. C++ planner experiment

Files:

- `cpp/navigation_planner.h`
- `cpp/navigation_planner.cpp`

The C++ demo produces directional/stop-style planner outputs from detection heuristics. These outputs are experimental and are not a certified mobility-safety controller.

Build with CMake:

```bash
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release
```

Or build the demo directly with g++:

```bash
g++ -std=c++17 -O2 -Icpp cpp/navigation_planner.cpp cpp/main_demo.cpp -o navigation_demo
./navigation_demo
```

`cpp/build/` is intentionally ignored and must not be committed.
