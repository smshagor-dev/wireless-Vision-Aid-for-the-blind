# Wireless Vision-Aid for the Blind (WVAB)

[![CI](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/ci.yml/badge.svg)](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/ci.yml)
[![Mobile Flutter](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/mobile-flutter.yml/badge.svg)](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/mobile-flutter.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Mobile: v1.0.0](https://img.shields.io/badge/Android-v1.0.0-blue.svg)](mobile/flutter/)

**Wireless Vision-Aid for the Blind (WVAB)** is an offline-first assistive computer-vision platform for blind and low-vision users. It combines real-time object detection, focused spoken guidance, local detection history, secure ESP32-CAM streaming, Raspberry Pi deployment, optional depth/localization research modules, and a standalone Flutter Android application.

WVAB is designed as an engineering and research platform. It intentionally separates reliable measurements from heuristic estimates, keeps wearable transport authenticated and encrypted by default, and exposes explicit degraded or stop states when navigation inputs are missing, stale, or uncalibrated.

> **Safety status**
>
> WVAB is a research/assistive prototype. It is not a certified mobility aid, medical device, emergency system, or autonomous navigation controller. Object detection, monocular distance estimates, visual-clearance hints, depth, and localization can be wrong or incomplete. A camera view that appears clear does not prove that the ground is safe to traverse.

---

## Contents

- [1. Project goals](#1-project-goals)
- [2. Current capabilities](#2-current-capabilities)
- [3. System architecture](#3-system-architecture)
- [4. Flutter Android application](#4-flutter-android-application)
- [5. Perception and guidance mathematics](#5-perception-and-guidance-mathematics)
- [6. Navigation and fail-safe semantics](#6-navigation-and-fail-safe-semantics)
- [7. Secure UDP design](#7-secure-udp-design)
- [8. Repository structure](#8-repository-structure)
- [9. Requirements](#9-requirements)
- [10. Quick start](#10-quick-start)
- [11. Flutter mobile build](#11-flutter-mobile-build)
- [12. ESP32-CAM and Raspberry Pi](#12-esp32-cam-and-raspberry-pi)
- [13. Smartphone and IP cameras](#13-smartphone-and-ip-cameras)
- [14. Python secure UDP streaming](#14-python-secure-udp-streaming)
- [15. Docker deployment](#15-docker-deployment)
- [16. Training and model export](#16-training-and-model-export)
- [17. Testing and CI](#17-testing-and-ci)
- [18. Production-readiness boundary](#18-production-readiness-boundary)
- [19. Privacy](#19-privacy)
- [20. Licensing](#20-licensing)
- [21. Academic use and reproducibility](#21-academic-use-and-reproducibility)
- [22. Maintainer and contact](#22-maintainer-and-contact)

---

## 1. Project goals

The central problem WVAB addresses is not simply object recognition. A detector may return many valid objects in every frame, but reading every label aloud creates an audio queue that becomes stale before a user can act on it.

WVAB therefore focuses on six engineering goals:

1. **Local perception** — run the primary detector locally without requiring a cloud inference server.
2. **Low cognitive load** — speak one relevant obstacle at a time instead of continuously reading the entire scene.
3. **Useful spatial context** — report direction and conservative distance information where technically justified.
4. **Fail-safe navigation research** — distinguish qualitative visual guidance from genuinely calibrated metric navigation.
5. **Secure wearable transport** — authenticate and encrypt ESP32/Python camera streams and reject replayed state.
6. **Reproducible deployment** — provide CI, model checks, Android release builds, Raspberry Pi tooling, Docker support, and explicit readiness gates.

The repository is suitable for software development, controlled research, bench validation, Android assistive-interface work, secure edge-camera integration, model experimentation, and navigation research.

---

## 2. Current capabilities

### Perception

- YOLOv8 real-time object detection.
- Bundled mobile ONNX model with `320 × 320` input.
- 80 COCO classes available in the Flutter application.
- Configurable detection confidence; mobile default is `0.25`.
- Qualitative proximity classification.
- Conservative approximate metric distance for selected reference-size classes.
- Left / center / right spatial classification.
- Focused obstacle selection to reduce audio overload.
- Local detection history containing timestamp, class, confidence, proximity, direction, and camera source.

### User feedback

- Android text-to-speech.
- Haptic feedback.
- Focus hold and announcement cooldown.
- Urgent stop behavior for visually blocked scenes.
- Language selection with OS-dependent TTS voice availability.
- Local profile/name onboarding.
- Spoken startup greeting: `Welcome Mr. {name}` when speech is enabled and a saved profile name exists.

### Camera and edge paths

- Android phone camera.
- ESP32-CAM.
- Trusted smartphone/IP-camera URL.
- Python UDP sender.
- Raspberry Pi edge runtime.

### Security

- AES-GCM encrypted UDP transport.
- Authentication required by default.
- Protocol-v2 authentication counters.
- Non-zero sender session IDs.
- Frame replay/order protection.
- Persistent authentication replay state across normal restarts.
- Full UDP packet header authenticated as AES-GCM AAD.
- Bounded authentication/session/frame state.
- Loopback WebSocket control by default.

### Navigation research

- Optional MiDaS depth path.
- Metric-calibration gating.
- Visual odometry.
- Optional ORB-SLAM3 bridge.
- Occupancy-grid mapping.
- A* planning pipeline.
- Explicit `STOP`, `DEGRADED`, and `GUIDANCE_AVAILABLE` output states.

### Delivery and validation

- Python 3.10 / 3.11 / 3.12 CI.
- Flutter analysis and tests.
- Standalone Android release APK generation.
- Android native ONNX Runtime verification.
- C++17 planner build/demo validation.
- ESP32 firmware compilation.
- Docker deployment checks.
- Release provenance workflow.

---

## 3. System architecture

All supported runtime paths follow the same high-level sequence:

**capture → validate → infer → interpret → provide bounded feedback**

```text
                         +----------------------+
                         |  Phone / USB Camera  |
                         +----------+-----------+
                                    |
                                    v
+-------------+             +-------+--------+              +----------------+
| ESP32-CAM   | --secure--> | Frame Handling | --tensor-->  | YOLO Detector  |
+-------------+   UDP       +-------+--------+              +--------+-------+
                                    |                                |
+-------------+                     |                                v
| IP / Phone  | --------------------+                     +----------+----------+
| Camera URL  |                                           | Detection Filtering |
+-------------+                                           +----------+----------+
                                                                    |
                                               +--------------------+-------------------+
                                               |                    |                   |
                                               v                    v                   v
                                      +--------+------+     +-------+-------+   +-------+-------+
                                      | Local History |     | Focus/Distance |   | Depth/Mapping |
                                      +---------------+     | Route Guidance |   | Research Path |
                                                            +-------+--------+   +-------+-------+
                                                                    |                    |
                                                                    v                    v
                                                            +-------+--------+   +-------+--------+
                                                            | TTS + Haptics  |   | Safety State   |
                                                            +----------------+   | STOP/DEGRADED |
                                                                                 +----------------+
```

### Important runtime entry points

| Path | Purpose |
|---|---|
| `vision_server.py` | Local USB/trusted camera detection and qualitative proximity |
| `udp_streaming.py` | Authenticated/encrypted remote camera streaming |
| `core/udp_runtime.py` | Shared UDP transport/session implementation |
| `core/udp_auth_state.py` | Persistent protocol-v2 authentication/replay state |
| `navigation_pipeline.py` | Experimental mapping/planning and fail-safe navigation state |
| `smartphone_camera.py` | Explicit trusted smartphone/IP-camera launcher |
| `main.py` | Source-checkout command dispatcher |
| `mobile/flutter/` | Standalone Android assistive application |

Legacy duplicate/mock GUI runtimes were removed because they either duplicated active functionality or exposed fixed values that could be mistaken for real measurements.

---

## 4. Flutter Android application

The standalone Android application is located in `mobile/flutter/`.

### Current mobile contract

| Item | Current value |
|---|---|
| Visible version | `1.0.0` |
| Internal build | `8` |
| Flutter | `3.47.0` |
| Dart SDK | `>=3.11.0 <4.0.0` |
| Android package | `com.smshagor.wvab_mobile` |
| Minimum Android SDK | `24` |
| Detector input | `1 × 3 × 320 × 320` |
| Detector classes | `80` COCO classes |
| Default confidence | `0.25` |
| ONNX Flutter wrapper | `flutter_onnxruntime 1.8.2` |
| Android ONNX Runtime | forced to `1.22.0` |
| Camera backend | `camera_android 0.10.11` |

### App features

The mobile application includes:

- first-run user-name setup;
- language selection;
- phone-camera and ESP32-CAM source selection;
- local ONNX object detection;
- focused one-object-at-a-time spoken guidance;
- approximate distance/range guidance;
- visual left/center/right route comparison;
- haptic feedback;
- local detection history;
- history clearing;
- configurable classes and confidence;
- local settings/profile persistence;
- Privacy Policy screen;
- Open Source Licenses screen using Flutter's installed license registry;
- How It Works screen;
- Contact screen;
- local-first operation for phone-camera inference.

### Focused guidance behavior

The detector may return several objects in one frame. The speech layer intentionally selects one primary object instead of serializing the full detection list.

The policy is:

1. rank currently accepted detections by risk;
2. choose one primary detection;
3. hold that focus briefly to avoid rapid switching;
4. allow a genuinely nearer hazard to preempt the old focus;
5. generate one route cue;
6. keep all detections in UI/history even when only one is spoken.

Example:

```text
Chair, about 1.5 meters away, left. Right side appears clearer. Keep right carefully.
```

The words **appears clearer** are deliberate. The camera sees image occupancy; it does not prove that the floor or ground is traversable.

---

## 5. Perception and guidance mathematics

This section uses **plain GitHub-safe mathematical notation** rather than renderer-dependent LaTeX. The formulas are the same ones implemented or referenced by the project, but they will render consistently in GitHub, terminals, exported Markdown, and plain-text documentation.

### 5.1 Normalized bounding-box geometry

For a normalized detection box:

```text
B = (x1, y1, x2, y2), where x and y are in [0, 1]
```

Width, height, and area are:

```text
w_B = max(0, x2 - x1)
h_B = max(0, y2 - y1)
A_B = w_B × h_B
```

Horizontal center is:

```text
c_x = clamp((x1 + x2) / 2, 0, 1)
```

These values remain normalized after model-space boxes are mapped back into source-frame coordinates.

### 5.2 Relative visual proximity

The mobile guidance engine uses normalized box height as a visual proximity heuristic:

```text
if h_B > 0.60:
    proximity = immediate
elif 0.40 < h_B <= 0.60:
    proximity = close
elif 0.20 < h_B <= 0.40:
    proximity = medium
else:
    proximity = far
```

Equivalent piecewise definition:

```text
P(h_B) = immediate, when h_B > 0.60
P(h_B) = close,     when 0.40 < h_B <= 0.60
P(h_B) = medium,    when 0.20 < h_B <= 0.40
P(h_B) = far,       when h_B <= 0.20
```

This is **not metric depth**. Two objects with different physical sizes can generate the same normalized image height at different real distances.

### 5.3 Horizontal direction

Direction is determined from the normalized horizontal box center:

```text
D(c_x) = left,   when c_x < 0.38
D(c_x) = center, when 0.38 <= c_x <= 0.62
D(c_x) = right,  when c_x > 0.62
```

The central range intentionally represents a walking corridor rather than a single image-center line.

### 5.4 Approximate monocular distance used by the mobile app

For selected classes that have a reasonably stable real-world vertical size, WVAB uses a normalized pinhole approximation:

```text
d_hat = (H_r × f_n) / h_B
```

where:

```text
d_hat = approximate object distance in meters
H_r   = assumed reference height for the detected class in meters
f_n   = normalized focal-length approximation
h_B   = normalized detected bounding-box height
```

Current mobile approximation:

```text
f_n = 0.87
```

The output is bounded before being used:

```text
0.4 m <= d_hat <= 20.0 m
```

Reference-size classes currently include examples such as:

- person;
- bicycle;
- car;
- motorcycle;
- bus;
- train;
- truck;
- traffic light;
- stop sign;
- parking meter;
- bench;
- chair;
- couch;
- toilet;
- refrigerator.

A single RGB phone camera cannot provide certified metric depth from an arbitrary object. If a class does not have a stable enough reference size, WVAB uses a broad visual range instead of inventing a precise meter value.

### 5.5 Controlled calibrated pinhole distance

The Python utility `core.proximity.estimate_metric_distance()` uses the standard pinhole relationship when explicit calibration is provided:

```text
d = (H × f_y) / h_p
```

where:

```text
H   = assumed physical object height in meters
f_y = calibrated vertical focal length in pixels
h_p = detected object height in pixels
d   = estimated distance in meters
```

This equation is academically meaningful only when the following are documented:

- camera model;
- camera intrinsics;
- calibration procedure;
- physical object-size assumption;
- test range;
- lighting/viewpoint conditions;
- expected error and failure cases.

### 5.6 Distance-error metrics

For a dataset containing N samples, predicted distance `d_hat_i`, and ground-truth distance `d_i`:

**Mean Absolute Error (MAE)**

```text
MAE = (1 / N) × sum(|d_hat_i - d_i|), for i = 1 ... N
```

**Root Mean Square Error (RMSE)**

```text
RMSE = sqrt((1 / N) × sum((d_hat_i - d_i)^2)), for i = 1 ... N)
```

These metrics should be reported with sample count, distance range, camera, object classes, and calibration conditions.

### 5.7 Focus selection

WVAB does not give `person` a hard-coded top priority. Candidate detections are compared lexicographically in this order:

1. nearer proximity band;
2. larger normalized bounding-box height;
3. closer position to the central walking corridor;
4. larger bounding-box area;
5. higher detector confidence;
6. object label only as the final deterministic tie-break.

Conceptually:

```text
RiskPriority(i) = lexicographic(
    proximity_rank(i),
    -box_height(i),
    center_rank(i),
    -box_area(i),
    -confidence(i),
    label(i)
)
```

Lower proximity rank means greater urgency. Larger box height and area are sorted earlier by the negative signs shown above.

The implementation uses explicit comparisons instead of an arbitrary weighted score, so changing one scale cannot accidentally dominate all other factors.

### 5.8 Focus stability and preemption

Default timing:

```text
focus_hold = 2 seconds
announcement_cooldown = 4 seconds
```

A held focus remains active while the same object class is still visible during the hold period. A newly detected object may preempt it when the new object belongs to a strictly nearer proximity band.

This reduces rapid speech switching while preserving urgent hazard preemption.

### 5.9 Lane occupancy

The image is divided into overlapping normalized horizontal regions:

```text
left   = [0.00, 0.38]
center = [0.31, 0.69]
right  = [0.62, 1.00]
```

For a lane `L = [l, r]`, horizontal overlap of detection `i` is:

```text
o_i = max(0, min(x2_i, r) - max(x1_i, l))
```

Lane width is:

```text
lane_width = r - l
```

Each detection contributes:

```text
contribution_i = (o_i / lane_width) × h_i × w_P(i)
```

Total lane occupancy is:

```text
O_L = sum(contribution_i)
```

Current proximity weights:

| Proximity | Weight |
|---|---:|
| immediate | `1.00` |
| close | `0.72` |
| medium | `0.38` |
| far | `0.10` |

The overlap between lane regions makes the heuristic less sensitive to boxes positioned exactly at a region boundary.

### 5.10 Route cue logic

The Flutter mobile route cue belongs to this set:

```text
NavigationCue = { moveLeft, moveRight, forward, stop }
```

The blocked threshold depends on focused-object proximity:

```text
blocked_threshold = 0.42, when proximity == immediate
blocked_threshold = 0.62, otherwise
```

The decision rules are intentionally conservative:

- if all relevant regions appear blocked, return `stop`;
- if an immediate hazard strongly blocks both side options, return `stop`;
- if an obstacle is on the left and the right region appears less occupied, prefer `moveRight`;
- if an obstacle is on the right and the left region appears less occupied, prefer `moveLeft`;
- when the center appears blocked, compare left and right occupancy;
- if the focused object is visually far, normal preference is `forward`.

This is a **visual-clearance heuristic**. It is not a ground-plane path planner and cannot prove that a suggested direction is physically safe.

### 5.11 Detector confidence

A candidate detection is accepted only when its confidence meets the configured threshold:

```text
p_i >= tau_c
```

Current mobile default:

```text
tau_c = 0.25
```

Lower confidence thresholds may increase recall but also increase false positives. Higher thresholds may reduce weak detections but miss partially visible, small, poorly lit, or motion-blurred objects.

A proper evaluation should therefore report class-level precision, recall, and preferably mAP rather than selecting a threshold by visual impression alone.

### 5.12 Precision, recall, and F1

For true positives `TP`, false positives `FP`, and false negatives `FN`:

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 × Precision × Recall / (Precision + Recall)
```

When evaluating object detection, matching must also define an IoU threshold.

Intersection over Union is:

```text
IoU = area(predicted_box ∩ ground_truth_box)
      / area(predicted_box ∪ ground_truth_box)
```

### 5.13 Latency metrics

One average latency number is not enough for an assistive real-time system. WVAB production-readiness work expects distributions such as:

```text
p50 = median latency
p95 = 95th percentile latency
p99 = 99th percentile latency
```

Useful measurements include:

- camera frame acquisition latency;
- preprocessing latency;
- inference latency;
- post-processing latency;
- camera-to-speech latency;
- reconnect/recovery time.

### 5.14 MiDaS and scale ambiguity

The optional MiDaS path estimates relative monocular depth. Raw monocular depth is scale ambiguous.

A simplified calibrated relation is:

```text
z_metric = scale × z_relative
```

The scale factor must come from external calibration or another trusted metric reference. WVAB therefore does not treat raw MiDaS values as meters by default.

### 5.15 Metric consistency for mapping

If metric depth is enabled, the same unit scale must be applied consistently to mapping and motion estimation.

Conceptually:

```text
metric_translation = scale × relative_translation
metric_depth       = scale × relative_depth
```

If metric visual-odometry scale is lost, the navigation path must degrade rather than mixing arbitrary-unit motion with metric occupancy data.

---

## 6. Navigation and fail-safe semantics

`navigation_pipeline.py` publishes an atomic state rather than pretending every generated path is safe.

| State | Meaning |
|---|---|
| `STOP` | Camera, localization, or usable path is unavailable |
| `DEGRADED` | A path exists but metric geometry/localization is not sufficiently calibrated or fresh |
| `GUIDANCE_AVAILABLE` | A path exists using coherent explicitly calibrated metric mapping/localization inputs |

This state is an integration boundary. It is not a certified actuator command.

### Fail-closed behavior

The navigation research path is expected to behave as follows:

```text
camera unavailable         -> STOP
localization unavailable   -> STOP
path unavailable           -> STOP
uncalibrated metric state  -> DEGRADED
stale metric localization  -> DEGRADED
calibrated + fresh + path  -> GUIDANCE_AVAILABLE
```

External ORB-SLAM3 pose input expires when the source stops updating. Stale pose data must not remain silently valid.

---

## 7. Secure UDP design

WVAB's wearable/remote camera path uses authenticated encrypted UDP rather than unauthenticated MJPEG fallback.

### Security properties

- AES-GCM encryption/authentication is enabled by default.
- AES keys may be 16, 24, or 32 bytes; 32 bytes are recommended.
- Tokens must be at least 16 characters.
- Each real deployment should use unique credentials.
- Authentication plaintext uses protocol v2.
- Sender boot creates a fresh non-zero 32-bit session ID.
- Authentication includes a monotonic 64-bit counter.
- Authentication also binds the sender's next frame ID.
- Complete 14-byte UDP headers are authenticated as AAD.
- Completed frame IDs are replay/order checked.
- Persistent replay state survives normal service/container restarts.
- A newer authenticated sender session retires the previous live session.
- Authentication refresh may advance the replay baseline but never move it backwards.

### Replay invariant

A simplified security invariant is:

```text
accepted_auth_counter_new > highest_persisted_auth_counter
```

and completed video-frame ordering follows a wrap-aware serial-number comparison rather than naive integer comparison.

Replay-state persistence is part of the security boundary. If the replay-state file or Docker replay-state volume is lost, deleted, or rolled back, rotate/re-pair device credentials before field use.

See `SECURE_UDP_PROTOCOL.md` for the complete wire contract.

---

## 8. Repository structure

```text
.
├── assets/                     fonts and related runtime assets
├── config/                     project/navigation configuration
├── core/                       shared Python security/runtime/proximity modules
├── deployment/                 Raspberry Pi and Docker deployment tooling
├── mobile/
│   └── flutter/                standalone Android application
├── navigation/                 navigation/planning components
├── tests/                      Python/system regression tests
├── tools/                      model, diagnostics, security and soak tooling
├── training/                   custom-model dataset configuration
├── vision_server.py            local vision runtime
├── udp_streaming.py            secure UDP camera runtime
├── navigation_pipeline.py      experimental navigation integration
├── smartphone_camera.py        trusted IP/smartphone camera launcher
├── main.py                     command dispatcher
├── PRODUCTION_READINESS.md     release/field-readiness evidence gate
├── SECURE_UDP_PROTOCOL.md      transport security contract
├── THIRD_PARTY_NOTICES.md      third-party licensing inventory
└── README.md                   primary project documentation
```

---

## 9. Requirements

Primary Python runtime:

- Python `3.10+`;
- local YOLO model for offline detection;
- platform camera/device dependencies as required by the selected runtime.

Install core requirements:

```bash
python -m pip install -r requirements.txt
```

Optional export/accelerator packages:

```bash
python -m pip install -r requirements-accelerators.txt
```

`setup.cfg` is the canonical Python package metadata source. `pyproject.toml` defines the build backend and pytest configuration.

### Model assets

The repository retains `yolov8n.pt` as its offline baseline model. This is a **third-party model asset**, not original MIT-licensed WVAB code. See `THIRD_PARTY_NOTICES.md`.

MiDaS weights are intentionally not committed. Provision them explicitly:

```bash
python tools/download_models.py midas
```

The provisioner validates the expected checksum and prepares the local cache used for later offline depth startup.

---

## 10. Quick start

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

See `QUICK_START.md` for the complete supported launch flows.

---

## 11. Flutter mobile build

```bash
cd mobile/flutter
flutter pub get
flutter analyze
flutter test
bash tool/bootstrap_android.sh
flutter build apk --release --split-per-abi
```

The mobile CI additionally verifies:

- exact visible version contract `1.0.0`;
- expected Flutter/plugin versions;
- generated Android host configuration;
- camera, vibration, network, and TTS declarations;
- Android ONNX Runtime resolution;
- ONNX model shape/class count/checksum;
- release APK ABI outputs;
- arm64 ONNX Runtime ELF packaging;
- absence of wrong-platform glibc dependencies;
- Android package name;
- `versionName=1.0.0`.

### Demo APK

The repository demo directory is:

```text
mobile/flutter/demo/
```

The demo README records the verified artifact metadata and checksum for the published Android arm64 build.

Passing CI does not prove physical-camera, speaker, OEM-driver, thermal, or battery behavior on every Android device.

---

## 12. ESP32-CAM and Raspberry Pi

Generate a matched credential pair locally:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

This creates git-ignored deployment credentials such as:

```text
esp32_secrets.h
deployment/rpi/wvab_edge.env
```

The generated Pi environment also configures persistent UDP replay state.

Flash `esp32_cam_stream.ino` with the generated credentials, then run:

```bash
./quick_start.sh run esp32
```

### Raspberry Pi service

```bash
sudo bash deployment/rpi/install_service.sh
systemctl status wvab_edge.service
```

The service uses the project virtual environment and persistent project state so replay protection survives normal restarts.

---

## 13. Smartphone and IP cameras

WVAB does not scan the local subnet for camera devices. Supply an explicit trusted stream URL:

```bash
python main.py phone http://192.168.1.20:8080/video --test-only
python main.py phone http://192.168.1.20:8080/video
```

The local/IP runtime does not reinterpret uncalibrated bounding-box proximity as certified metric distance.

---

## 14. Python secure UDP streaming

Set unique credentials:

```bash
export WVAB_UDP_KEY_HEX="<16/24/32-byte-key-as-hex>"
export WVAB_UDP_TOKEN="<unique-token-at-least-16-characters>"
```

Start server and sender:

```bash
python main.py udp-server --config wvab_config.sample.json
python main.py udp-client --config wvab_config.sample.json --server-ip 127.0.0.1 --camera 0
```

Authentication and encryption are required by default.

`WVAB_ALLOW_INSECURE_UDP=1` is an explicit isolated-development exception and must not be used for normal wearable/field deployment.

WebSocket control binds to `127.0.0.1:8765` by default and authenticates every command. Remote exposure should be treated as a deliberate deployment/security decision.

---

## 15. Docker deployment

Generate credentials before starting Compose:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
bash deployment/docker_start.sh build
bash deployment/docker_start.sh up -d udp-vision-server
```

Use the wrapper when generated custom UDP ports are in use so host and container configuration remain consistent.

The image runs as a non-root `wvab` user. Persistent replay state is stored in the configured Docker replay-state volume and must be preserved across normal upgrades/recreation.

Optional headless navigation + Prometheus on Linux:

```bash
export WVAB_VIDEO_GID="$(getent group video | cut -d: -f3)"
export WVAB_CAMERA_DEVICE=/dev/video0
bash deployment/docker_start.sh --profile navigation up -d navigation-engine prometheus
```

Metrics ports are intended to bind to loopback by default.

---

## 16. Training and model export

Canonical custom-model workflow:

```bash
python train_navigation_model.py train \
  --data training/wvab_custom.yaml \
  --model yolov8n.pt \
  --epochs 80 \
  --device 0
```

Validation:

```bash
python train_navigation_model.py val \
  --model runs/wvab/navigation/weights/best.pt \
  --data training/wvab_custom.yaml
```

ONNX export:

```bash
python train_navigation_model.py export \
  --model runs/wvab/navigation/weights/best.pt \
  --format onnx
```

Optional accelerator export:

```bash
python -m pip install -r requirements-accelerators.txt
python export_accelerated_models.py --format openvino
```

The current Flutter model supports the standard 80 COCO classes. Potholes, curbs, stairs, or other custom mobility-specific classes require a compatible custom-trained model if they are not part of the active model's output vocabulary.

---

## 17. Testing and CI

Fast Python validation:

```bash
python -m pip install -r requirements-ci.txt
python -m pytest -q
```

Full host diagnostics:

```bash
./quick_start.sh doctor --full --camera 0 --tts
```

Soak tools:

```bash
python tools/soak_monitor.py --help
python tools/summarize_soak.py --help
```

Automated validation covers major software contracts including:

- Python 3.10 / 3.11 / 3.12 tests;
- package/wheel verification;
- UDP cryptographic/replay behavior;
- Python compilation;
- C++17 planner build/demo;
- repository hygiene;
- secret exclusion;
- Docker invariants;
- ESP32 firmware compilation;
- Flutter analysis/tests;
- Android release APK construction;
- Android ONNX native-library inspection.

CI is reproducibility evidence. It is not field-validation evidence.

---

## 18. Production-readiness boundary

WVAB contains **production-oriented engineering controls**, but it must not be described as a certified production mobility device without hardware/user validation.

Engineering controls already represented in the repository include:

- automated multi-version CI;
- secure transport defaults;
- persistent replay protection;
- bounded state/memory policies;
- fail-safe navigation states;
- Android release builds;
- model/native runtime verification;
- Docker/Raspberry Pi deployment tooling;
- dependency and artifact checks;
- documented recovery procedures.

Before a field-ready claim, record evidence for at least:

- 8+ hour continuous soak testing;
- memory/CPU/GPU/temperature trends;
- camera disconnect/reconnect behavior;
- network/sender failure and recovery;
- TTS failure/recovery;
- replay/tamper rejection;
- sender and server restart behavior;
- model precision/recall/mAP on representative mobility scenes;
- calibrated distance MAE/RMSE where metric claims are made;
- end-to-end latency p50/p95/p99;
- battery and thermal behavior on target hardware;
- accessibility testing with blind/low-vision participants under appropriate ethics/consent procedures.

See `PRODUCTION_READINESS.md` for the full evidence gate.

---

## 19. Privacy

The Flutter phone-camera path is designed as local-first processing.

Current mobile behavior stores locally:

- entered user name;
- selected language;
- app preferences;
- selected classes;
- confidence threshold;
- recent detection-history events;
- configured ESP32 connection credentials in secure storage.

Detection history contains metadata such as label, timestamp, confidence, proximity, direction, and camera source. It is not intended to store camera photographs or videos.

The current mobile implementation does not include a WVAB advertising SDK, WVAB analytics upload service, or mandatory WVAB cloud account.

Android TTS behavior may depend on voice packs and services installed on the device.

---

## 20. Licensing

Original WVAB repository code is distributed under the repository **MIT License**.

Third-party components keep their own licenses and are not relicensed merely because they appear in or are used by WVAB.

Important examples include:

- Ultralytics software/model assets;
- YOLO model weights;
- MiDaS components/model assets;
- ONNX Runtime;
- Flutter/Dart dependencies;
- Noto fonts;
- external datasets.

Review these files before redistribution or commercial deployment:

```text
LICENSE
PROJECT_OWNERSHIP.md
THIRD_PARTY_NOTICES.md
```

The bundled YOLO baseline model is a third-party model asset and must not be described as an original WVAB-owned AI model.

---

## 21. Academic use and reproducibility

WVAB may be used as a software research platform, but academic claims should identify the exact experimental configuration.

A reproducible report should include:

- repository commit SHA;
- mobile/app version if Android is used;
- exact model identity and checksum;
- dataset and split definition;
- camera model and resolution;
- preprocessing/input dimensions;
- detector confidence threshold;
- IoU/NMS settings;
- CPU/GPU/accelerator configuration;
- inference and end-to-end latency distributions;
- distance-calibration procedure where metric distance is reported;
- MAE/RMSE and distance range;
- localization/depth scale source;
- hardware and OS versions;
- known limitations and failure cases.

### Suggested software citation

```bibtex
@software{wvab_2026,
  author  = {Md Shahanur Islam Shagor},
  title   = {Wireless Vision-Aid for the Blind (WVAB)},
  year    = {2026},
  url     = {https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind},
  note    = {Open-source assistive computer-vision and edge-navigation research platform}
}
```

For a paper or experiment, add the exact release/tag/commit used so another researcher can reproduce the software state.

---

## 22. Maintainer and contact

**Maintainer / Original WVAB project author:** Md Shahanur Islam Shagor

- GitHub: `smshagor-dev`
- Website: `https://smshagor.com`
- Email: `smshagor.dev@gmail.com`
- Mobile: `+79954949836`
- Repository: `https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind`

For technical bug reports, include:

- operating system/device model;
- Android version when applicable;
- camera source;
- exact commit or release;
- model identity;
- relevant logs;
- steps required to reproduce the issue.

---

## Final engineering note

WVAB is intentionally conservative about what the software claims to know. Object labels are detector outputs. Bounding-box proximity is a visual heuristic. Monocular meter estimates are approximations unless the camera/object assumptions are calibrated. A route that looks clearer in the image is not automatically a safe path. Metric mapping/navigation is gated by calibration and localization quality.

That distinction is central to the project: **use computer vision to provide useful assistance without presenting uncertain estimates as guaranteed physical truth.**
