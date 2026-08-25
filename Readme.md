# Wireless Vision-Aid for the Blind (WVAB)

WVAB is an offline-first computer-vision assistance platform for blind and low-vision users. It combines real-time object detection, multilingual spoken guidance, secure camera streaming, optional depth/localization modules, and Raspberry Pi / ESP32-CAM deployment tooling.

> **Safety status:** WVAB is a research/assistive prototype, not a certified mobility or medical device. Qualitative proximity from bounding boxes or uncalibrated monocular depth/localization must not be interpreted as metric distance or proof that a route is safe.

## Supported runtime paths

- `vision_server.py` — local USB or trusted IP-camera assistive detection with qualitative proximity only
- `udp_streaming.py` — compatibility entrypoint for authenticated/encrypted remote camera streaming
- `core/udp_runtime.py` — secure UDP runtime/session implementation
- `navigation_pipeline.py` — experimental fail-safe navigation path publishing `STOP`, `DEGRADED`, or `GUIDANCE_AVAILABLE`
- `smartphone_camera.py` — explicit trusted smartphone/IP stream launcher
- `main.py` — source-checkout command dispatcher

Legacy mock/duplicate GUI runtimes were removed because they displayed hard-coded readiness/metric values or duplicated unsafe uncalibrated navigation heuristics.

## Current capabilities

- YOLOv8 real-time object detection
- qualitative proximity guidance: `immediate`, `close`, `medium`, `far`
- optional calibrated pinhole-distance utility for controlled experiments
- multilingual labels and TTS
- bundled Bengali, Devanagari, and Arabic overlay fonts
- webcam, smartphone/IP-camera, Python UDP sender, and ESP32-CAM paths
- AES-GCM encrypted UDP transport with authentication required by default
- authenticated 32-bit sender session IDs and reboot-safe frame replay protection
- full 14-byte UDP header authenticated as AES-GCM AAD
- bounded authentication/session/frame replay state and in-flight frame memory
- IoU-based temporal object tracking
- authenticated loopback WebSocket control on the UDP server
- completed-frame watchdogs, health files, reconnect handling, and bounded auto-restart
- Raspberry Pi edge launcher and hardened systemd service generation
- optional MiDaS depth path with verified model provisioning and metric-calibration gating
- visual odometry and optional ORB-SLAM3 bridge with stale-pose rejection
- occupancy-grid mapping and A* planning research pipeline
- fail-safe `STOP` / `DEGRADED` / `GUIDANCE_AVAILABLE` state output
- optional ONNX/OpenVINO/TensorRT export validation
- non-root Docker runtime with local-secret build exclusions
- Python 3.10/3.11/3.12 CI definitions, wheel-content verification, and lightweight unit tests
- clean C++17 planner build/demo validation in CI
- SLSA source-provenance workflow for releases/manual provenance generation

## Requirements

WVAB requires Python 3.10+ and a local YOLO model for offline object detection.

```bash
python -m pip install -r requirements.txt
```

Optional export/accelerator dependencies are separate:

```bash
python -m pip install -r requirements-accelerators.txt
```

`setup.cfg` is the canonical package metadata source; `pyproject.toml` defines the build backend and pytest configuration.

## Model assets

The repository currently retains `yolov8n.pt` as the offline baseline model. It is a **third-party model asset**, not original MIT-licensed WVAB code; see `THIRD_PARTY_NOTICES.md` for licensing boundaries.

The larger MiDaS depth weight is intentionally excluded from source control. Provision it once while online:

```bash
python tools/download_models.py midas
```

The MiDaS provisioner downloads the expected upstream legacy asset, verifies its SHA256 before installation, and prepares the Torch Hub source cache required for later offline depth startup. If local assets are missing while `WVAB_OFFLINE=1`, depth disables cleanly instead of silently reaching the network.

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

See `QUICK_START.md` for the supported launch flows.

## ESP32-CAM + Raspberry Pi

Generate a matched credential pair locally:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

This creates git-ignored:

- `esp32_secrets.h`
- `deployment/rpi/wvab_edge.env`

Flash `esp32_cam_stream.ino` with the generated header, then run:

```bash
./quick_start.sh run esp32
```

The release firmware is secure-UDP-only. It creates a fresh non-zero session ID at boot, authenticates/encrypts every datagram with AES-GCM, and authenticates the complete packet header as AAD. A newly authenticated session retires the previous sender session, allowing an ESP32/Python sender reboot to restart its frame counter safely without disabling replay protection. Authentication refresh within the same session does not reset frame replay state.

See `SECURE_UDP_PROTOCOL.md` for the exact wire contract and replay/resource bounds.

### Raspberry Pi service

Keep the project virtual environment created during setup. The systemd installer requires `.venv/bin/python` with Python 3.10+ and renders the service to use that exact interpreter:

```bash
sudo bash deployment/rpi/install_service.sh
systemctl status wvab_edge.service
```

This prevents a rebooted service from falling back to an unprepared system Python.

## Smartphone/IP camera

Use the exact trusted stream URL provided by the camera app. WVAB does not scan the local subnet.

```bash
python main.py phone http://192.168.1.20:8080/video --test-only
python main.py phone http://192.168.1.20:8080/video
```

The local/IP runtime exposes no remote control socket and does not convert uncalibrated bounding-box heuristics into meters.

## Python UDP streaming

For another Python sender, export a unique AES key and UDP token before starting:

```bash
export WVAB_UDP_KEY_HEX="<16/24/32-byte-key-as-hex>"
export WVAB_UDP_TOKEN="<unique-token-at-least-16-characters>"
python main.py udp-server --config wvab_config.sample.json
python main.py udp-client --config wvab_config.sample.json --server-ip 127.0.0.1 --camera 0
```

Authentication and encryption are required by default. `WVAB_ALLOW_INSECURE_UDP=1` is an explicit isolated-development exception and must not be used for normal wearable/field deployment.

WebSocket control belongs to the UDP server, binds to `127.0.0.1:8765` by default, and requires a secret for every command. Remote binding requires a dedicated WebSocket token and should only be used behind an explicitly trusted/TLS network boundary.

## Docker

Generate local device/server credentials before running Compose. `.dockerignore` excludes local credential files from the image build context; Compose injects the server environment only at runtime.

Use the wrapper so the generated `WVAB_UDP_PORT` is applied both inside the container and to the host UDP port mapping:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
bash deployment/docker_start.sh build
bash deployment/docker_start.sh up -d udp-vision-server
```

Do not replace the wrapper with a plain `docker compose up` when using a non-default generated port; Compose service `env_file` values are not used for YAML port interpolation unless the file is also supplied as Compose's `--env-file`.

The image runs as non-root user `wvab`. The UDP server disables TTS/WebSocket control inside the container and enables a completed/decodeable-frame watchdog. The container health check requires both a fresh health record and a recent completed video frame.

Optional headless navigation + Prometheus on Linux:

```bash
export WVAB_VIDEO_GID="$(getent group video | cut -d: -f3)"
export WVAB_CAMERA_DEVICE=/dev/video0
bash deployment/docker_start.sh --profile navigation up -d navigation-engine prometheus
```

Host metrics ports bind only to loopback (`127.0.0.1:8000` and `127.0.0.1:9090`).

## Distance, depth, and localization semantics

Normal realtime assistance uses **qualitative proximity**, not meters. Bounding-box size alone is not a reliable metric-distance sensor.

`core.proximity.estimate_metric_distance()` exists only for controlled experiments where focal length and physical-object assumptions are explicitly supplied. It is not a general mobility distance sensor.

MiDaS monocular depth is scale-ambiguous. Metric occupancy updates remain disabled until camera intrinsics and a depth scale have been externally calibrated and explicitly enabled in `config/config.yaml`.

Metric navigation guidance additionally requires coherent metric localization. Calibrated depth is scaled consistently before both visual-odometry translation and occupancy mapping; temporary metric VO scale loss degrades guidance rather than injecting arbitrary unit motion. ORB-SLAM3 output expires when its external pose file stops updating.

## Navigation safety state

`navigation_pipeline.py` writes an atomic state file configured by `navigation.safety_state_file`:

- `STOP` — camera, localization, or path is unavailable
- `DEGRADED` — a path exists but metric geometry/localization is not sufficiently calibrated/fresh
- `GUIDANCE_AVAILABLE` — a path exists using coherent explicitly calibrated metric mapping/localization inputs

This state is an integration boundary, not a certified actuator controller.

## Multilingual fonts and speech

Bundled overlay fonts:

- `assets/fonts/NotoSansBengali-Regular.ttf`
- `assets/fonts/NotoSansDevanagari-Regular.ttf`
- `assets/fonts/NotoNaskhArabic-Regular.ttf`

`WVAB_FONT_PATH` can override font selection. TTS voice availability remains host-OS dependent. Bundled fonts retain their upstream license; see `THIRD_PARTY_NOTICES.md`.

## Training and export

The canonical trainer validates local dataset splits, numeric arguments, and local/offline model behavior:

```bash
python train_navigation_model.py train --data training/wvab_custom.yaml --model yolov8n.pt --epochs 80 --device 0
python train_navigation_model.py val --model runs/wvab/navigation/weights/best.pt --data training/wvab_custom.yaml
python train_navigation_model.py export --model runs/wvab/navigation/weights/best.pt --format onnx
```

Explicit accelerator export:

```bash
python -m pip install -r requirements-accelerators.txt
python export_accelerated_models.py --format openvino
```

Export commands fail fast when required backend dependencies or local source models are missing instead of silently relying on hidden downloads in the normal offline path.

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

The CI definition covers Python 3.10/3.11/3.12, wheel content plus isolated installed imports, Python compilation, shell/CLI syntax, UDP protocol/session tests, clean C++17 planner build/demo execution, repository hygiene, secret exclusion, container custom-port invariants, and known insecure-default regressions. A GitHub workflow being configured is not itself field-validation evidence; release hardware tests remain separate.

## Production-readiness gates

Before any field-ready claim, record evidence for at least:

- 8+ hour soak testing without unbounded memory growth
- camera/network/TTS dropout recovery
- authenticated/encrypted transport, header-tamper rejection, replay rejection, and sender reboot/session rotation
- completed-frame watchdog and reconnect behavior
- model accuracy on representative mobility hazards
- calibrated depth/distance and localization error statistics where metric claims are made
- end-to-end latency p50/p95/p99
- battery/thermal behavior on target edge hardware
- blind/low-vision user evaluation under an approved ethics/consent process

See `PRODUCTION_READINESS.md` and `production.md`.

## License and third-party components

Original WVAB code is distributed under the repository **MIT License**. Third-party software, models, fonts, datasets, and dependencies retain their own applicable licenses/terms and are not relicensed merely because they are used by or stored in this repository.

Review:

- `LICENSE`
- `PROJECT_OWNERSHIP.md`
- `THIRD_PARTY_NOTICES.md`

before redistribution or commercial deployment.
