# WVAB Quick Start

## 1. Setup and deterministic diagnostics

WVAB requires Python 3.10+.

```bash
./quick_start.sh setup
./quick_start.sh doctor
./quick_start.sh doctor --full --camera 0 --tts
```

The doctor is offline-first and non-interactive. It does not require Internet connectivity or claim that hardware is field-safe.

## 2. Local or IP-camera runtime

USB/local camera:

```bash
./quick_start.sh run vision --camera 0
```

Smartphone/IP camera: use the exact trusted URL displayed by the phone app. WVAB no longer scans the local subnet for cameras.

```bash
./quick_start.sh run phone http://192.168.1.20:8080/video --test-only
./quick_start.sh run phone http://192.168.1.20:8080/video
```

This runtime reports qualitative proximity only; it does not label bounding-box heuristics as meters and exposes no remote control socket.

## 3. Pair an ESP32-CAM with Raspberry Pi

Generate matching, git-ignored device credentials:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

Flash `esp32_cam_stream.ino` with the generated `esp32_secrets.h` beside the sketch, then start the authenticated AES-GCM edge path:

```bash
./quick_start.sh run esp32
```

For station-mode Wi-Fi, pass `--station --ssid ... --wifi-password ... --server-ip ...` to the generator.

## 4. Optional MiDaS depth provisioning

```bash
python tools/download_models.py midas
```

The 85 MB MiDaS weight is not stored in the source tree. The downloader verifies its checksum and prepares the Torch Hub source cache.

## 5. Secure Python UDP server/client

For a Python camera sender instead of ESP32, export deployment-specific `WVAB_UDP_KEY_HEX` and `WVAB_UDP_TOKEN`, then run:

```bash
./quick_start.sh run udp-server
./quick_start.sh run udp-client 127.0.0.1
```

The canonical remote camera path is the authenticated/encrypted UDP runtime in `udp_streaming.py`.

## 6. Root command dispatcher

The repository root no longer points to nonexistent Android modules. Use:

```bash
python main.py --help
python main.py doctor --full --camera 0
python main.py vision --camera 0
python main.py phone http://192.168.1.20:8080/video --test-only
python main.py udp-server --config wvab_config.sample.json
```

## 7. C++ planner experiment

```bash
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release
```

The planner output is experimental and is not a certified mobility-safety controller. `cpp/build/` is intentionally ignored.
