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
- WebSocket runtime control for language, confidence, and object filtering
- Health files, reconnect handling, watchdogs, and bounded auto-restart
- Raspberry Pi edge service configuration
- MiDaS depth research path with explicit metric-calibration gating
- Visual odometry and optional ORB-SLAM3 bridge
- Occupancy-grid mapping and A* planning research pipeline
- Fail-safe `STOP` / `DEGRADED` / `GUIDANCE_AVAILABLE` state output
- OpenVINO/TensorRT export utilities
- Deterministic lightweight CI tests plus opt-in full integration smoke tests

## Requirements

- Python 3.10+
- Local camera, smartphone stream, or ESP32-CAM
- A local YOLO model for offline use

```bash
python -m pip install -r requirements.txt
```

Runtime dependency versions are bounded to compatible major versions. Lightweight CI dependencies are exactly pinned in `requirements-ci.txt`.

## Quick start

```bash
python test_system.py
python vision_server.py
```

For secure UDP streaming, generate deployment-specific credentials first:

```bash
python - <<'PY'
import os, secrets
print("WVAB_UDP_KEY_HEX=" + os.urandom(32).hex())
print("WVAB_UDP_TOKEN=" + secrets.token_urlsafe(24))
PY
```

Then export them in your environment and run:

```bash
python udp_streaming.py server --config wvab_config.sample.json
python udp_streaming.py client --config wvab_config.sample.json
```

Do not deploy the example key/token from `wvab_config.sample.json` unchanged.

## WebSocket control

The UDP server exposes a control socket on port `8765` by default when `WVAB_WS_CONTROL=1`.

Supported JSON commands:

```json
{"cmd":"set_language","value":"bn"}
{"cmd":"set_all_objects","value":true}
{"cmd":"set_confidence","value":0.4}
{"cmd":"status"}
```

The server validates language and confidence values before applying them.

## Distance and depth semantics

The normal realtime assistant uses **qualitative proximity**, not meters. Bounding-box size alone is not a reliable metric-distance sensor.

`core.proximity.estimate_metric_distance()` is available only for controlled experiments where both focal length and physical object height assumptions are explicitly supplied. It should not be used as a general blind-navigation distance sensor.

MiDaS output is monocular and scale-ambiguous. The navigation pipeline therefore keeps metric occupancy updates disabled unless both camera intrinsics and a depth scale have been externally calibrated and enabled in `config/config.yaml`.

## Navigation safety state

`navigation_pipeline.py` writes an atomic state file configured by `navigation.safety_state_file`:

- `STOP`: camera/localization/path is unavailable
- `DEGRADED`: a path exists but geometry is not calibrated for metric use
- `GUIDANCE_AVAILABLE`: a path exists using an explicitly calibrated metric mapping source

This replaces the previous placeholder motor-stop function. Hardware-specific audio/haptic/actuator adapters should consume this state and implement their own certified fail-safe behavior.

## Multilingual fonts and speech

Bundled overlay fonts:

- `assets/fonts/NotoSansBengali-Regular.ttf`
- `assets/fonts/NotoSansDevanagari-Regular.ttf`
- `assets/fonts/NotoNaskhArabic-Regular.ttf`

The runtime now checks bundled fonts for Bengali/Hindi/Arabic before falling back to system fonts. `WVAB_FONT_PATH` can override the selection.

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
bash deployment/rpi/wvab_edge_start.sh
```

Review `deployment/rpi/wvab_edge.env` and replace all deployment credentials before use.

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

The test suite covers configuration validation, proximity semantics, calibrated-distance math, Unicode font selection, missing-depth handling, fail-safe state output, occupancy-grid behavior, and A* obstacle avoidance.

Full runtime smoke import is opt-in because it requires heavyweight ML/device dependencies:

```bash
WVAB_FULL_SMOKE=1 python -m pytest tests/test_smoke.py -q
```

GitHub Actions runs core tests on Python 3.10, 3.11, and 3.12 and rejects tracked cache/build/log artifacts.

## Repository hygiene

Generated Python caches, CMake/Visual Studio build output, runtime logs, health files, local datasets, and derived export files are ignored. The currently vendored YOLO and MiDaS weights are retained intentionally to preserve the existing offline demo path; new/derived weights should be distributed as versioned release artifacts instead of being committed directly.

## Production-readiness gates

Before describing a build as field-ready, record and publish evidence for at least:

- 8+ hour soak testing without unbounded memory growth
- camera/network/TTS dropout recovery
- authenticated/encrypted transport validation
- model accuracy on representative mobility hazards
- calibrated distance/depth error statistics where metric claims are made
- end-to-end latency distribution, not only best-case latency
- localization drift and path-planning failure rate
- battery/thermal behavior on the target edge device
- blind/low-vision user evaluation under an approved study protocol

See `PRODUCTION_READINESS.md` for the release gate checklist.

## License

MIT License. See `LICENSE`.
