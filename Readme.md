# Wireless Vision-Aid for the Blind (WVAB)

WVAB is an offline-first computer-vision assistance platform for blind and low-vision users. It combines real-time object detection, multilingual spoken guidance, secure camera streaming, optional depth/localization research modules, and Raspberry Pi edge deployment.

> **Safety status:** WVAB is a research/assistive prototype, not a certified mobility or medical device. Qualitative proximity from a monocular bounding box or uncalibrated MiDaS/VO/monocular-SLAM output must not be interpreted as metric distance or proof that a route is safe.

## Current capabilities

- YOLOv8 real-time object detection
- Qualitative proximity guidance (`immediate`, `close`, `medium`, `far`)
- Optional calibrated pinhole-distance utility for controlled experiments
- Multilingual labels and TTS
- Bundled Bengali, Devanagari, and Arabic overlay fonts
- Webcam, smartphone/IP camera, and ESP32-CAM paths
- Secure UDP transport with AES-GCM and token authentication enabled by default
- IoU-based temporal object tracking
- Authenticated WebSocket runtime control for language, confidence, and object filtering
- Health files, reconnect handling, watchdogs, and bounded auto-restart
- Raspberry Pi edge service configuration
- Optional MiDaS depth research path with explicit model provisioning and metric-calibration gating
- Visual odometry and optional ORB-SLAM3 bridge
- Occupancy-grid mapping and A* planning research pipeline
- Fail-safe `STOP` / `DEGRADED` / `GUIDANCE_AVAILABLE` state output
- OpenVINO/TensorRT export utilities
- Non-root Docker runtime with local-secret build exclusions
- Deterministic lightweight CI tests plus opt-in full integration smoke tests

## Requirements

- Python 3.10+
- Local camera, smartphone stream, or ESP32-CAM
- A local YOLO model for offline use

```bash
python -m pip install -r requirements.txt
```

Runtime dependency versions are bounded to compatible major versions. Lightweight CI dependencies are exactly pinned in `requirements-ci.txt`.

## Model provisioning

The small baseline `yolov8n.pt` remains in the repository for the core offline object-detection demo. The much larger MiDaS depth weight is intentionally excluded from source control.

Prepare MiDaS once while online:

```bash
python tools/download_models.py midas
```

The provisioner downloads the official MiDaS v2.1 small asset, verifies its SHA256 before installation, and prepares the Torch Hub source cache required for later offline depth startup. If `WVAB_OFFLINE=1` and those local assets are missing, depth is disabled cleanly instead of silently reaching the network.

## Quick start

```bash
python test_system.py
python vision_server.py
```

For ESP32-CAM + Raspberry Pi pairing, generate matching local credentials rather than editing secrets into source:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
```

That creates git-ignored `esp32_secrets.h` and `deployment/rpi/wvab_edge.env`. Flash the firmware with the generated header, then start the edge server:

```bash
bash deployment/rpi/wvab_edge_start.sh
```

For a Python UDP sender/client, export a unique `WVAB_UDP_KEY_HEX` and `WVAB_UDP_TOKEN` and run:

```bash
python udp_streaming.py server --config wvab_config.sample.json
python udp_streaming.py client --config wvab_config.sample.json
```

## Docker

Docker is intended for headless server or controlled navigation experiments, not direct access to host desktop audio/GUI.

First create the local server credential file; it is loaded by Compose at runtime and excluded from the Docker build context:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
docker compose build
docker compose up -d udp-vision-server
```

The image runs as non-root user `wvab`, `.dockerignore` excludes local credentials, and the default Compose service exposes only UDP `9999`. TTS and WebSocket control are disabled inside the container by default.

The optional navigation/metrics profile requires a Linux camera device. Set the host video-group ID explicitly when it differs from `44`:

```bash
export WVAB_VIDEO_GID="$(getent group video | cut -d: -f3)"
export WVAB_CAMERA_DEVICE=/dev/video0
docker compose --profile navigation up -d navigation-engine prometheus
```

Navigation runs headless in this profile. Prometheus binds only to host loopback at `127.0.0.1:9090`; the navigation metrics endpoint is likewise exposed only on loopback at `127.0.0.1:8000`.

## WebSocket control

WebSocket control is enabled by default for the native UDP server but binds only to `127.0.0.1:8765`. Every command requires a shared secret. `WVAB_WS_TOKEN` is preferred; when it is blank, the server falls back to `WVAB_UDP_TOKEN`.

For local control, send the token with every JSON command:

```json
{"token":"<control-token>","cmd":"set_language","value":"bn"}
{"token":"<control-token>","cmd":"set_all_objects","value":true}
{"token":"<control-token>","cmd":"set_confidence","value":0.4}
{"token":"<control-token>","cmd":"status"}
```

The server validates the token using constant-time comparison and validates command values before applying changes. If remote control is intentionally required, set `WVAB_WS_CONTROL_HOST=0.0.0.0` only behind a trusted network/TLS boundary and keep a unique `WVAB_WS_TOKEN` configured.

## Distance and depth semantics

The normal realtime assistant uses **qualitative proximity**, not meters. Bounding-box size alone is not a reliable metric-distance sensor.

`core.proximity.estimate_metric_distance()` is available only for controlled experiments where both focal length and physical object height assumptions are explicitly supplied. It should not be used as a general blind-navigation distance sensor.

MiDaS output is monocular and scale-ambiguous. The navigation pipeline therefore keeps metric occupancy updates disabled unless both camera intrinsics and a depth scale have been externally calibrated and enabled in `config/config.yaml`.

## Navigation safety state

`navigation_pipeline.py` writes an atomic state file configured by `navigation.safety_state_file`:

- `STOP`: camera/localization/path is unavailable
- `DEGRADED`: a path exists but geometry is not calibrated for metric use
- `GUIDANCE_AVAILABLE`: a path exists using an explicitly calibrated metric mapping source

This state file is an integration boundary, not a certified actuator controller. Hardware-specific audio/haptic/actuator adapters require their own validation.

## Multilingual fonts and speech

Bundled overlay fonts:

- `assets/fonts/NotoSansBengali-Regular.ttf`
- `assets/fonts/NotoSansDevanagari-Regular.ttf`
- `assets/fonts/NotoNaskhArabic-Regular.ttf`

The runtime checks bundled fonts for Bengali/Hindi/Arabic before falling back to system fonts. `WVAB_FONT_PATH` can override the selection.

TTS still depends on voices installed on the target OS. Windows voice-pack helpers remain available:

```powershell
.\install_tts_voice_packs.ps1 -Languages ru-RU,en-US,bn-BD,hi-IN -CopyToSettings
.\enable_onecore_voices.ps1
```

## Raspberry Pi edge mode

The Pi can act as the processing/audio node while an ESP32-CAM stays on the wearable camera side.

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv espeak-ng libatlas-base-dev
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/generate_device_secrets.py --server-ip 192.168.4.2
bash deployment/rpi/wvab_edge_start.sh
```

`deployment/rpi/wvab_edge_start.sh` refuses to start when credentials are absent/invalid or UDP authentication/encryption is disabled. `deployment/rpi/install_service.sh` renders a service for the actual checkout path instead of relying on a hard-coded `/home/pi/...` path.

## Training and export

```bash
python train_navigation_model.py train --data training/wvab_custom.yaml --model yolov8n.pt --epochs 80 --device 0
python train_navigation_model.py val --model runs/wvab/navigation/weights/best.pt --data training/wvab_custom.yaml
python train_navigation_model.py export --model runs/wvab/navigation/weights/best.pt --format onnx
python export_accelerated_models.py
```

The custom schema includes mobility-relevant classes such as crosswalk, curb, pothole, pole, road cone, stairs, and door. Dataset quality and real-world validation remain separate research requirements.

## Testing

Fast, device-independent validation:

```bash
python -m pip install -r requirements-ci.txt
python -m pytest -q
```

The test suite covers configuration validation, proximity semantics, calibrated-distance math, Unicode font selection, control-channel secret handling, model checksum handling, missing-depth handling, fail-safe state output, occupancy-grid behavior, and A* obstacle avoidance.

Full runtime smoke import is opt-in because it requires heavyweight ML/device dependencies:

```bash
WVAB_FULL_SMOKE=1 python -m pytest tests/test_smoke.py -q
```

GitHub Actions runs core tests on Python 3.10, 3.11, and 3.12, validates shell/tool syntax, rejects tracked cache/build/log/secret artifacts, and rejects known insecure deployment defaults.

## Repository hygiene

Generated Python caches, CMake/Visual Studio build output, runtime logs, health files, local datasets, downloaded depth assets, local ESP32/Pi credentials, and derived export files are ignored. `.dockerignore` additionally prevents those local credentials from being copied into image build contexts.

## Production-readiness gates

Before describing a build as field-ready, record and publish evidence for at least:

- 8+ hour soak testing without unbounded memory growth
- camera/network/TTS dropout recovery
- authenticated/encrypted transport and control-channel validation
- model accuracy on representative mobility hazards
- calibrated distance/depth error statistics where metric claims are made
- end-to-end latency distribution, not only best-case latency
- localization drift and path-planning failure rate
- battery/thermal behavior on the target edge device
- blind/low-vision user evaluation under an approved study protocol

See `PRODUCTION_READINESS.md` and `production.md` for release/deployment gates.

## License

MIT License. See `LICENSE`.
