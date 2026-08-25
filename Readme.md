# Wireless Vision-Aid for the Blind (WVAB)

WVAB is an offline-first computer-vision assistance platform for blind and low-vision users. It combines real-time object detection, multilingual spoken guidance, secure camera streaming, optional depth/localization research modules, and Raspberry Pi edge deployment.

> **Safety status:** WVAB is a research/assistive prototype, not a certified mobility or medical device. Qualitative proximity from a monocular bounding box or uncalibrated MiDaS/VO/monocular-SLAM output must not be interpreted as metric distance or proof that a route is safe.

## Supported runtime paths

- `vision_server.py`: local USB or trusted IP-camera assistive detection with qualitative proximity only
- `udp_streaming.py`: authenticated AES-GCM remote camera transport and server
- `navigation_pipeline.py`: experimental fail-safe navigation research path publishing `STOP`, `DEGRADED`, or `GUIDANCE_AVAILABLE`
- `smartphone_camera.py`: explicit trusted smartphone/IP stream launcher
- `main.py`: source-checkout command dispatcher

Legacy mock/duplicate Tk dashboards were removed because they displayed hard-coded readiness/metric values or duplicated unsafe uncalibrated navigation heuristics.

## Current capabilities

- YOLOv8 real-time object detection
- Qualitative proximity guidance (`immediate`, `close`, `medium`, `far`)
- Optional calibrated pinhole-distance utility for controlled experiments
- Multilingual labels and TTS
- Bundled Bengali, Devanagari, and Arabic overlay fonts
- Webcam, smartphone/IP camera, and ESP32-CAM paths
- Secure UDP transport with AES-GCM and token authentication enabled by default
- IoU-based temporal object tracking
- Authenticated loopback WebSocket control on the UDP server
- Health files, reconnect handling, watchdogs, and bounded auto-restart
- Raspberry Pi edge service configuration
- Optional MiDaS depth research path with explicit model provisioning and metric-calibration gating
- Visual odometry and optional ORB-SLAM3 bridge
- Occupancy-grid mapping and A* planning research pipeline
- Fail-safe `STOP` / `DEGRADED` / `GUIDANCE_AVAILABLE` state output
- Optional OpenVINO acceleration/export support
- Non-root Docker runtime with local-secret build exclusions
- Deterministic lightweight CI tests plus opt-in full integration smoke tests

## Requirements

WVAB requires Python 3.10+ and a local YOLO model for offline use.

```bash
python -m pip install -r requirements.txt
```

OpenVINO is intentionally not part of the default edge install:

```bash
python -m pip install -r requirements-accelerators.txt
```

`setup.cfg` is the canonical package metadata source; `pyproject.toml` defines the build backend and pytest configuration.

## Model provisioning

The baseline `yolov8n.pt` remains local for the core offline object-detection demo. The much larger MiDaS depth weight is excluded from source control.

```bash
python tools/download_models.py midas
```

The MiDaS provisioner downloads the official v2.1 small asset, verifies SHA256 before installation, and prepares the Torch Hub source cache required for later offline depth startup. If local assets are missing while `WVAB_OFFLINE=1`, depth is disabled cleanly rather than silently reaching the network.

## Quick start

```bash
./quick_start.sh setup
./quick_start.sh doctor
./quick_start.sh doctor --full --camera 0
./quick_start.sh run vision --camera 0
```

Or use the root dispatcher:

```bash
python main.py --help
python main.py doctor --full --camera 0
python main.py vision --camera 0
```

## ESP32-CAM + Raspberry Pi

Generate a matched credential pair locally:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

This creates git-ignored `esp32_secrets.h` and `deployment/rpi/wvab_edge.env`. Flash the ESP32 firmware with the generated header, then start the authenticated AES-GCM edge server:

```bash
./quick_start.sh run esp32
```

The launcher refuses missing/invalid credentials, disabled auth/encryption, malformed AES keys, and missing YOLO models.

## Smartphone/IP camera

Use the exact trusted stream URL provided by the camera app. WVAB does not scan the local subnet.

```bash
python main.py phone http://192.168.1.20:8080/video --test-only
python main.py phone http://192.168.1.20:8080/video
```

The local/IP runtime exposes no remote control socket and never converts uncalibrated bounding-box heuristics into meters.

## Python UDP streaming

For another Python sender, export a unique `WVAB_UDP_KEY_HEX` and `WVAB_UDP_TOKEN` before starting:

```bash
python main.py udp-server --config wvab_config.sample.json
python main.py udp-client --config wvab_config.sample.json --server-ip 127.0.0.1 --camera 0
```

WebSocket control belongs to the UDP server, binds to `127.0.0.1:8765` by default, and requires a shared secret for every command. A remote bind should only be used behind an explicitly trusted/TLS boundary with a dedicated `WVAB_WS_TOKEN`.

## Docker

Generate the local credential file first; `.dockerignore` excludes it from the image build context and Compose loads it only at runtime.

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
docker compose build
docker compose up -d udp-vision-server
```

The image runs as non-root user `wvab`. The default service exposes only UDP 9999 and disables TTS/WebSocket control inside the container.

Optional headless navigation + Prometheus on Linux:

```bash
export WVAB_VIDEO_GID="$(getent group video | cut -d: -f3)"
export WVAB_CAMERA_DEVICE=/dev/video0
docker compose --profile navigation up -d navigation-engine prometheus
```

Host metrics ports bind only to loopback (`127.0.0.1:8000` and `127.0.0.1:9090`).

## Distance and depth semantics

Normal realtime assistance uses **qualitative proximity**, not meters. Bounding-box size alone is not a reliable metric-distance sensor.

`core.proximity.estimate_metric_distance()` exists only for controlled experiments where focal length and physical-object assumptions are explicitly provided. It is not a general mobility distance sensor.

MiDaS monocular depth is scale-ambiguous. Metric occupancy updates remain disabled until both camera intrinsics and a depth scale have been externally calibrated and explicitly enabled in `config/config.yaml`.

## Navigation safety state

`navigation_pipeline.py` writes an atomic state file configured by `navigation.safety_state_file`:

- `STOP`: camera/localization/path is unavailable
- `DEGRADED`: a path exists but geometry is not calibrated for metric use
- `GUIDANCE_AVAILABLE`: a path exists using an explicitly calibrated metric mapping source

This state is an integration boundary, not a certified actuator controller.

## Multilingual fonts and speech

Bundled overlay fonts:

- `assets/fonts/NotoSansBengali-Regular.ttf`
- `assets/fonts/NotoSansDevanagari-Regular.ttf`
- `assets/fonts/NotoNaskhArabic-Regular.ttf`

`WVAB_FONT_PATH` can override font selection. TTS voice availability remains host-OS dependent.

## Training and export

```bash
python train_navigation_model.py train --data training/wvab_custom.yaml --model yolov8n.pt --epochs 80 --device 0
python train_navigation_model.py val --model runs/wvab/navigation/weights/best.pt --data training/wvab_custom.yaml
python train_navigation_model.py export --model runs/wvab/navigation/weights/best.pt --format onnx
```

For OpenVINO export/runtime support:

```bash
python -m pip install -r requirements-accelerators.txt
python export_accelerated_models.py
```

## Testing

Fast device-independent validation:

```bash
python -m pip install -r requirements-ci.txt
python -m pytest -q
```

Full host diagnostics:

```bash
./quick_start.sh doctor --full --camera 0 --tts
```

GitHub Actions covers Python 3.10/3.11/3.12, package metadata, Python compilation, shell/tool CLI syntax, unit tests, repository hygiene, secret exclusion, and known insecure-default regression checks.

## Production-readiness gates

Before any field-ready claim, record evidence for at least:

- 8+ hour soak testing without unbounded memory growth
- camera/network/TTS dropout recovery
- authenticated/encrypted transport and control-channel validation
- model accuracy on representative mobility hazards
- calibrated distance/depth error statistics where metric claims are made
- end-to-end latency p50/p95/p99
- localization drift and path-planning failure rate
- battery/thermal behavior on target edge hardware
- blind/low-vision user evaluation under an approved ethics/consent protocol

See `PRODUCTION_READINESS.md` and `production.md`.

## License

MIT License. See `LICENSE`.
