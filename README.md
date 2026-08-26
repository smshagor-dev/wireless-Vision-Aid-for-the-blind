# Wireless Vision-Aid for the Blind (WVAB)

[![CI](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/ci.yml/badge.svg)](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/ci.yml)
[![Mobile Flutter](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/mobile-flutter.yml/badge.svg)](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind/actions/workflows/mobile-flutter.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Mobile: v1.0.0](https://img.shields.io/badge/Android-v1.0.0-blue.svg)](mobile/flutter/)

**Wireless Vision-Aid for the Blind (WVAB)** is an offline-first assistive computer-vision platform for blind and low-vision users. The project combines real-time object detection, focused spoken guidance, local detection history, secure ESP32-CAM streaming, Raspberry Pi deployment, optional depth/localization research modules, and a standalone Flutter Android application.

WVAB is built as an engineering and research platform rather than a demo that hides important limitations. The system separates what can be measured reliably from what is only estimated, keeps critical transport paths authenticated and encrypted, and fails closed when navigation inputs are missing or uncalibrated.

> **Safety status**
>
> WVAB is a research/assistive prototype. It is not a certified mobility aid, medical device, emergency system, or autonomous navigation controller. Object detection, monocular distance estimates, visual-clearance hints, depth, and localization can be wrong or incomplete. A camera view that appears clear does not prove that the ground is safe to traverse.

---

## Contents

- [1. Project goals](#1-project-goals)
- [2. What is included](#2-what-is-included)
- [3. System architecture](#3-system-architecture)
- [4. Android application](#4-android-application)
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
- [21. Academic use and citation](#21-academic-use-and-citation)
- [22. Maintainer and contact](#22-maintainer-and-contact)

---

## 1. Project goals

The practical problem behind WVAB is simple to describe but difficult to solve well: a vision system can detect many objects in every frame, but reading every label aloud is not useful to a person who needs a short, timely instruction.

WVAB therefore focuses on six engineering goals:

1. **Local perception** — run the primary object detector locally without requiring a cloud inference server.
2. **Low cognitive load** — focus speech on one relevant obstacle instead of reading the whole scene continuously.
3. **Useful spatial context** — report object direction and conservative distance information where possible.
4. **Fail-safe navigation research** — distinguish between qualitative guidance and genuinely calibrated metric navigation.
5. **Secure wearable transport** — authenticate and encrypt ESP32/Python camera streams and reject replayed state.
6. **Reproducible deployment** — provide CI, model checks, Android release builds, Raspberry Pi tooling, Docker support, and explicit readiness gates.

The current project is suitable for software development, controlled research, bench testing, dataset/model experimentation, Android assistive-interface development, and secure edge-camera integration.

---

## 2. What is included

### Perception

- YOLOv8 real-time object detection.
- Mobile ONNX inference with a bundled `320 × 320` YOLOv8n model.
- 80 COCO classes enabled in the Flutter application.
- Configurable confidence threshold; mobile default is `0.25`.
- Qualitative proximity classification.
- Conservative approximate metric estimates for selected reference-size classes.
- Left / center / right spatial classification.
- Focused obstacle selection to reduce speech overload.
- Local detection history with timestamps, confidence, direction, proximity, and camera source.

### User feedback

- Android text-to-speech.
- Haptic feedback.
- Focus hold and announcement cooldown.
- Urgent `STOP` behavior for visually blocked scenes.
- Language selection with OS-dependent TTS availability.
- Local profile/name onboarding and spoken welcome.

### Camera and edge paths

- Android phone camera.
- ESP32-CAM.
- Trusted smartphone/IP camera URL.
- Python UDP camera sender.
- Raspberry Pi edge service.

### Security

- AES-GCM encrypted UDP transport.
- Authentication required by default.
- Protocol-v2 authentication counters.
- Session IDs and frame replay protection.
- Persistent replay state across normal restarts.
- Authenticated packet header as AES-GCM AAD.
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

The repository supports several runtime paths, but they share the same design principle: **capture → validate → infer → interpret → provide bounded feedback**.

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
| `core/udp_auth_state.py` | Persistent protocol-v2 auth/replay state |
| `navigation_pipeline.py` | Experimental mapping/planning and fail-safe navigation state |
| `smartphone_camera.py` | Explicit trusted smartphone/IP camera launcher |
| `main.py` | Source-checkout command dispatcher |
| `mobile/flutter/` | Standalone Android assistive application |

Legacy duplicate/mock GUI runtimes were removed because they either duplicated active functionality or exposed fixed values that could be mistaken for real measurements.

---

## 4. Android application

The standalone Android application lives in `mobile/flutter/`.

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

### Mobile features

The app includes:

- first-run name setup;
- language selection;
- phone-camera and ESP32-CAM source selection;
- local ONNX object detection;
- focused one-object-at-a-time speech guidance;
- approximate distance/range guidance;
- visual left/center/right route comparison;
- vibration feedback;
- local detection history;
- history clearing;
- configurable detection classes and confidence;
- local profile/settings persistence;
- Privacy Policy screen;
- Open Source Licenses screen using Flutter's installed license registry;
- How It Works screen;
- Contact screen;
- spoken startup greeting: `Welcome Mr. {name}` when speech is enabled and a profile name is stored.

### Why the app speaks one object at a time

A detector may return several valid objects per frame. Speaking all of them creates an audio queue that can become obsolete before it finishes. WVAB therefore uses a **focused guidance policy**:

1. choose one primary risk;
2. keep that focus briefly to avoid rapid switching;
3. allow a genuinely nearer hazard to preempt the old focus;
4. generate one concise route cue;
5. keep every accepted detection available to the UI/history even though only one is spoken.

A typical English message is intentionally short:

```text
Chair, about 1.5 meters away, left. Right side appears clearer. Keep right carefully.
```

The phrase **appears clearer** is deliberate. The camera sees image occupancy; it does not prove floor traversability.

---

## 5. Perception and guidance mathematics

This section documents the mathematical meaning of the values produced by the project. The equations are intentionally separated into **relative visual geometry**, **approximate monocular distance**, and **calibrated metric distance** because they have different validity.

### 5.1 Normalized bounding-box geometry

For a detection with normalized coordinates

$$
B = (x_1, y_1, x_2, y_2), \qquad x,y \in [0,1]
$$

the mobile runtime defines

$$
w_B = \max(0, x_2-x_1)
$$

$$
h_B = \max(0, y_2-y_1)
$$

$$
A_B = w_B h_B
$$

and the normalized horizontal center

$$
c_x = \operatorname{clip}\left(\frac{x_1+x_2}{2},0,1\right).
$$

These values are independent of the display resolution after box coordinates have been remapped from the model letterbox back into source-frame coordinates.

### 5.2 Relative proximity

The Flutter guidance engine uses bounding-box height as a **visual proximity heuristic**:

$$
P(h_B)=
\begin{cases}
\text{immediate}, & h_B > 0.60\\
\text{close}, & 0.40 < h_B \le 0.60\\
\text{medium}, & 0.20 < h_B \le 0.40\\
\text{far}, & h_B \le 0.20
\end{cases}
$$

This is not a metric depth measurement. A tall physical object and a short physical object can produce similar image heights at different real distances.

### 5.3 Horizontal direction

The horizontal direction is derived from the normalized box center:

$$
D(c_x)=
\begin{cases}
\text{left}, & c_x < 0.38\\
\text{center}, & 0.38 \le c_x \le 0.62\\
\text{right}, & c_x > 0.62
\end{cases}
$$

The thresholds intentionally leave a central corridor rather than treating exactly half the image as the only forward region.

### 5.4 Approximate monocular metric distance

For selected classes with a reasonably stable real-world vertical reference size, the mobile application computes a coarse estimate using a normalized pinhole approximation:

$$
\hat d = \frac{H_r f_n}{h_B}
$$

where:

- $\hat d$ is approximate distance in meters;
- $H_r$ is the class reference height in meters;
- $f_n$ is an approximate normalized focal length;
- $h_B$ is normalized detected box height.

The current mobile implementation uses

$$
f_n = 0.87
$$

as a rough approximation for a typical phone camera near a 60° vertical field of view. The result is bounded to a practical range:

$$
\hat d \in [0.4,20]\;\text{m}.
$$

Reference-size classes currently include examples such as person, bicycle, car, motorcycle, bus, train, truck, traffic light, stop sign, parking meter, bench, chair, couch, toilet, and refrigerator.

For classes without a reliable reference height, WVAB does **not** invent a precise meter value. It falls back to broad visual range language derived from the proximity band.

### 5.5 Controlled calibrated distance

The Python utility `core.proximity.estimate_metric_distance()` implements the standard pinhole relationship when explicit calibration is supplied:

$$
d = \frac{H f_y}{h_p}
$$

where:

- $H$ = assumed physical object height in meters;
- $f_y$ = calibrated vertical focal length in pixels;
- $h_p$ = detected object height in pixels;
- $d$ = estimated distance in meters.

This equation becomes meaningful only when the camera intrinsics and object-size assumption are documented. For an academic evaluation, report the camera, calibration method, test range, mean absolute error (MAE), root mean square error (RMSE), and known failure cases.

Recommended error metrics are

$$
\operatorname{MAE}=\frac{1}{N}\sum_{i=1}^{N}|\hat d_i-d_i|
$$

and

$$
\operatorname{RMSE}=\sqrt{\frac{1}{N}\sum_{i=1}^{N}(\hat d_i-d_i)^2}.
$$

### 5.6 Focus selection

WVAB does not use `person` as a hard-coded top class. Candidate detections are ordered by a risk-oriented lexicographic policy:

1. nearer proximity band;
2. larger normalized box height;
3. closer position to the central walking corridor;
4. larger bounding-box area;
5. higher detector confidence;
6. label only as a deterministic final tie-break.

Conceptually, the priority is

$$
R_i = \operatorname{lexicographic}\left(
-r_P(i),
+h_i,
-r_C(i),
+A_i,
+p_i
\right)
$$

where $r_P$ is proximity rank, $h_i$ box height, $r_C$ center rank, $A_i$ box area, and $p_i$ detector confidence. The code implements explicit comparisons rather than collapsing these terms into an arbitrary weighted sum.

### 5.7 Focus stability and preemption

The default focus hold is

$$
T_{hold}=2\;\text{s}
$$

and the same guidance state has a default announcement cooldown of

$$
T_{cooldown}=4\;\text{s}.
$$

A held object remains the spoken focus while it is still visible unless a new candidate enters a strictly nearer proximity band. This gives the audio channel temporal stability while still allowing urgent hazards to preempt stale guidance.

### 5.8 Lane occupancy

The guidance engine divides the normalized image into overlapping left, center, and right regions. For a lane $L=[l,r]$, each detection contributes according to its horizontal overlap, visual height, and proximity weight.

For detection $i$:

$$
o_i = \max\left(0,\min(x_{2,i},r)-\max(x_{1,i},l)\right)
$$

and lane occupancy is

$$
O_L = \sum_i \left(\frac{o_i}{r-l}\right) h_i w_{P_i}.
$$

The current proximity weights are:

| Proximity | Weight |
|---|---:|
| immediate | `1.00` |
| close | `0.72` |
| medium | `0.38` |
| far | `0.10` |

The current normalized lane ranges are approximately:

- left: `[0.00, 0.38]`
- center: `[0.31, 0.69]`
- right: `[0.62, 1.00]`

The overlap between regions makes the score less sensitive to a box lying exactly on a lane boundary.

### 5.9 Route cue logic

The mobile route cue is chosen from

$$
C \in \{\text{moveLeft},\text{moveRight},\text{forward},\text{stop}\}.
$$

The blocked threshold depends on the focused object's proximity:

$$
\tau =
\begin{cases}
0.42, & P=\text{immediate}\\
0.62, & \text{otherwise}
\end{cases}
$$

If all relevant regions appear blocked, or an immediate hazard occupies both side options strongly enough, WVAB issues `STOP`. If the focused obstacle is on one side and the opposite side has lower occupancy, the app suggests the opposite side. If the center is occupied, left and right scores are compared.

This is a **visual-clearance heuristic**, not a ground-plane path planner. It cannot see holes, transparent barriers, stairs outside the detector classes, slippery surfaces, or obstacles outside the current camera field of view.

### 5.10 Detector confidence

For each candidate detection, the mobile runtime accepts model output only when

$$
p_i \ge \tau_c
$$

where the default mobile confidence threshold is

$$
\tau_c = 0.25.
$$

Lowering this threshold can improve recall but also increases false positives. Raising it reduces weak detections but can miss partially visible or poorly illuminated objects. Evaluation should therefore report class-level precision/recall rather than selecting a threshold by visual impression alone.

### 5.11 MiDaS and scale ambiguity

The optional MiDaS path estimates relative monocular depth. A monocular network can infer depth ordering and scene structure, but its raw scale is not automatically metric.

A simplified relationship is

$$
z_{metric} = s\,z_{relative}
$$

where the scale $s$ must come from external calibration or another trusted metric source. WVAB therefore gates metric occupancy/navigation use until calibration is explicitly enabled.

---

## 6. Navigation and fail-safe semantics

`navigation_pipeline.py` publishes an atomic safety state rather than pretending that every path is valid.

| State | Meaning |
|---|---|
| `STOP` | Camera, localization, or usable path is unavailable |
| `DEGRADED` | A path exists but metric geometry/localization is not sufficiently calibrated or fresh |
| `GUIDANCE_AVAILABLE` | A path exists using coherent, explicitly calibrated metric mapping/localization inputs |

The navigation state is an integration boundary. It is not a certified actuator command.

### Metric consistency

When metric depth is enabled, the same distance scale must be used consistently by mapping and motion estimation. A temporary loss of metric visual-odometry scale must degrade guidance rather than injecting arbitrary unit translations into the map.

External ORB-SLAM3 output is treated as stale when its pose source stops updating.

---

## 7. Secure UDP design

WVAB's wearable/remote camera path uses authenticated encrypted UDP rather than unauthenticated MJPEG fallback.

### Security properties

- AES-GCM authentication and encryption are enabled by default.
- AES keys may be 16, 24, or 32 bytes; 32 bytes are recommended.
- Tokens must be at least 16 characters.
- Each sender boot creates a fresh non-zero 32-bit session ID.
- The complete 14-byte protocol header is authenticated as AES-GCM Additional Authenticated Data (AAD).
- Authentication protocol v2 binds:
  - protocol version;
  - monotonic 64-bit authentication counter;
  - sender next-frame ID;
  - deployment token.
- Legacy token-only authentication is rejected.
- Authentication nonces are replay checked.
- Highest accepted authentication counters are persisted before a session is granted or renewed.
- Completed frame IDs are replay/order checked per authenticated source/session.
- A newly authenticated sender session retires the old live session for that source.

### Replay invariant

For an authentication refresh with counter $c_{new}$ and persisted maximum $c_{max}$, normal acceptance requires a strictly newer counter:

$$
c_{new} > c_{max}.
$$

The persisted value is updated before the authenticated session is considered active. This is why the replay-state file is part of the security boundary.

**Do not delete, roll back, or restore an older replay-state file during a deployment.** If replay state is lost, rotate/re-pair the UDP credentials before field use.

For the exact packet contract and recovery procedure, read [`SECURE_UDP_PROTOCOL.md`](SECURE_UDP_PROTOCOL.md).

---

## 8. Repository structure

```text
.
├── assets/                     Fonts and shared assets
├── config/                     Runtime/navigation configuration
├── core/                       Shared Python security, proximity and runtime logic
├── deployment/                 Raspberry Pi and Docker deployment assets
├── mobile/flutter/             Standalone Flutter Android application
│   ├── assets/                 Mobile ONNX model + translations
│   ├── lib/                    App, controller, vision, history, settings, legal/help UI
│   ├── test/                   Flutter unit/widget regression tests
│   ├── tool/                   Android/model/branding generation and verification
│   └── demo/                   Versioned demo APK documentation/artifact
├── training/                   Custom dataset configuration/support
├── tools/                      Provisioning, model download, soak/evidence utilities
├── main.py                     Root command dispatcher
├── navigation_pipeline.py      Experimental mapping/planning pipeline
├── smartphone_camera.py        Trusted phone/IP camera launcher
├── udp_streaming.py            Secure remote camera runtime
├── vision_server.py            Local camera detection runtime
├── PRODUCTION_READINESS.md     Release/field-readiness evidence gate
├── PROJECT_OWNERSHIP.md        Authorship and attribution boundary
├── THIRD_PARTY_NOTICES.md      Third-party software/model/font inventory
└── LICENSE                     MIT license for original WVAB code
```

---

## 9. Requirements

### Python runtime

- Python `3.10+`
- local YOLO model for offline detection

Install the standard runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

Optional export/accelerator dependencies are separated deliberately:

```bash
python -m pip install -r requirements-accelerators.txt
```

`setup.cfg` is the canonical package metadata source. `pyproject.toml` defines the build backend and pytest configuration.

### Mobile runtime

The source contract currently pins Flutter `3.47.0`. Android release builds are generated in CI and may also be built locally with the same version.

---

## 10. Quick start

Recommended source-checkout flow:

```bash
./quick_start.sh setup
./quick_start.sh doctor
./quick_start.sh doctor --full --camera 0
./quick_start.sh run vision --camera 0
```

Equivalent dispatcher commands:

```bash
python main.py --help
python main.py doctor --full --camera 0
python main.py vision --camera 0
```

See [`QUICK_START.md`](QUICK_START.md) for additional supported launch paths.

### Offline model assets

The repository retains `yolov8n.pt` as the baseline third-party YOLO asset.

The larger MiDaS weight is intentionally excluded from source control. Provision it once while online:

```bash
python tools/download_models.py midas
```

The provisioner validates the expected checksum and prepares the local Torch Hub source cache. If required assets are missing while `WVAB_OFFLINE=1`, the depth path disables cleanly rather than silently downloading from the network.

---

## 11. Flutter mobile build

### Development validation

```bash
cd mobile/flutter
flutter pub get
flutter analyze
flutter test
```

### Generate Android host project and branding

```bash
bash tool/bootstrap_android.sh
```

### Build release APKs

```bash
flutter build apk --release --split-per-abi
```

Expected outputs include:

```text
build/app/outputs/flutter-apk/app-arm64-v8a-release.apk
build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk
build/app/outputs/flutter-apk/app-x86_64-release.apk
```

### What CI verifies for mobile

The Mobile Flutter workflow checks more than compilation:

- exact `v1.0.0+8` dependency/version contract;
- offline ONNX export and model checksum;
- model input shape `1 × 3 × 320 × 320`;
- exactly 80 detector classes;
- Dart analysis;
- Flutter tests;
- Android permissions and TTS service declaration;
- launcher branding integrity;
- Android ONNX Runtime resolved to `1.22.0`;
- required ONNX keep rules;
- release minification/shrinking configuration;
- split release APK creation;
- presence of ARM64 `libonnxruntime.so`;
- rejection of Linux/glibc native dependencies inside the Android APK;
- Android package name and `versionName=1.0.0`.

The verified demo APK documentation is in [`mobile/flutter/demo/`](mobile/flutter/demo/).

GitHub Actions can verify build and packaging behavior, but it cannot prove every physical phone camera, OEM camera stack, speaker, TTS engine, battery, or thermal condition.

---

## 12. ESP32-CAM and Raspberry Pi

Generate a matched credential pair locally:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

This creates git-ignored deployment files such as:

- `esp32_secrets.h`
- `deployment/rpi/wvab_edge.env`

The generated Raspberry Pi environment also configures persistent replay state at:

```text
state/udp_replay_state.json
```

Flash `esp32_cam_stream.ino` with the generated header, then run:

```bash
./quick_start.sh run esp32
```

### Raspberry Pi service

The systemd installer uses the project virtual environment and requires Python 3.10+:

```bash
sudo bash deployment/rpi/install_service.sh
systemctl status wvab_edge.service
```

The service works from the project root so replay state survives normal process/service restarts.

---

## 13. Smartphone and IP cameras

WVAB expects an explicit trusted stream URL. It does not scan the local network for cameras.

```bash
python main.py phone http://192.168.1.20:8080/video --test-only
python main.py phone http://192.168.1.20:8080/video
```

The trusted local/IP runtime does not expose a remote control socket and does not convert uncalibrated box-size heuristics into authoritative metric distance.

---

## 14. Python secure UDP streaming

For a Python camera sender, configure a unique key and token:

```bash
export WVAB_UDP_KEY_HEX="<16/24/32-byte-key-as-hex>"
export WVAB_UDP_TOKEN="<unique-token-at-least-16-characters>"

python main.py udp-server --config wvab_config.sample.json
python main.py udp-client --config wvab_config.sample.json --server-ip 127.0.0.1 --camera 0
```

Authentication and encryption are required by default.

`WVAB_ALLOW_INSECURE_UDP=1` exists only as an explicit isolated-development exception. Do not use it for normal wearable or field deployment.

WebSocket control binds to `127.0.0.1:8765` by default and requires a secret for every command. Remote binding should be placed behind an explicitly trusted and protected network boundary with a dedicated `WVAB_WS_TOKEN`.

---

## 15. Docker deployment

Generate credentials before starting Compose:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
bash deployment/docker_start.sh build
bash deployment/docker_start.sh up -d udp-vision-server
```

Use the wrapper rather than plain `docker compose up` when generated ports are involved; it applies `WVAB_UDP_PORT` consistently to the container and host mapping.

The image runs as non-root user `wvab`. Persistent replay state is stored in the `wvab-replay-state` named volume at:

```text
/var/lib/wvab/udp_replay_state.json
```

If that volume is intentionally deleted or restored from stale backup, re-pair/rotate credentials before field use.

Optional headless navigation and Prometheus on Linux:

```bash
export WVAB_VIDEO_GID="$(getent group video | cut -d: -f3)"
export WVAB_CAMERA_DEVICE=/dev/video0
bash deployment/docker_start.sh --profile navigation up -d navigation-engine prometheus
```

Host metrics ports bind only to loopback (`127.0.0.1:8000` and `127.0.0.1:9090`).

---

## 16. Training and model export

The canonical trainer validates local dataset splits, numeric arguments, and offline/local model behavior.

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

### Custom mobility classes

The stock mobile model contains the 80 COCO classes. Classes such as custom `pothole`, `curb`, `crosswalk`, or `stairs` require a compatible model trained to emit those labels. The application must not invent a label that the detector was never trained to produce.

For research results, report at least:

- dataset source and split strategy;
- class distribution;
- input resolution;
- confidence threshold;
- IoU/NMS settings;
- per-class precision and recall;
- mAP@0.5 and preferably mAP@0.5:0.95;
- latency on the actual deployment hardware;
- difficult environmental cases such as low light, blur, occlusion, glare, and crowded scenes.

---

## 17. Testing and CI

### Python tests

```bash
python -m pip install -r requirements-ci.txt
python -m pytest -q
```

### Host diagnostics

```bash
./quick_start.sh doctor --full --camera 0 --tts
```

### Runtime soak evidence

```bash
python tools/soak_monitor.py --help
python tools/summarize_soak.py --help
```

### CI coverage

The repository's automated validation includes:

- Python 3.10 / 3.11 / 3.12;
- wheel content and isolated installed imports;
- cryptographic UDP tests;
- authentication and frame replay tests;
- restart/replay-state behavior;
- Python compilation;
- shell/CLI syntax;
- clean C++17 planner build/demo;
- repository hygiene and secret exclusion;
- Docker replay-state/custom-port invariants;
- actual ESP32 firmware compilation;
- Flutter analysis/tests;
- Android release APK and native runtime inspection.

CI is reproducibility evidence, not field-validation evidence.

---

## 18. Production-readiness boundary

WVAB contains **production-oriented engineering controls**, including release builds, explicit version contracts, authenticated transport, replay protection, CI, deterministic asset verification, local-first storage, fail-safe navigation states, and deployment tooling.

That does **not** mean the project is already certified for independent mobility use.

Before any field-ready claim, the release evidence should include at least:

- 8+ hour continuous soak test;
- bounded memory behavior;
- camera disconnect/reconnect recovery;
- network/TTS dropout recovery;
- authentication/header/replay fault injection;
- sender and server reboot behavior;
- replay-state corruption/loss procedure;
- model accuracy on representative mobility hazards;
- calibrated distance MAE/RMSE if metric distance is claimed;
- localization error statistics if metric navigation is claimed;
- end-to-end camera-to-audio latency p50/p95/p99;
- sustained FPS;
- battery runtime;
- CPU/GPU/temperature behavior;
- physical Android device coverage;
- Raspberry Pi/ESP32 hardware revision records;
- structured blind/low-vision user evaluation under appropriate ethics/consent procedures.

The detailed checklist is maintained in [`PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md).

---

## 19. Privacy

The Android application is designed as a local-first assistive runtime.

Current mobile behavior:

- phone-camera frames are processed locally by the bundled ONNX detector;
- the app does not require a WVAB cloud account;
- no WVAB advertising SDK is part of the current mobile implementation;
- no WVAB analytics upload service is part of the current mobile implementation;
- name, language, settings, and detection history are stored locally in app storage;
- detection history stores metadata, not intentional camera photo/video archives;
- ESP32 pairing/authentication material is stored using Android secure-storage facilities;
- history can be cleared from the app;
- app data can also be removed using Android storage controls or uninstall.

Android TTS may depend on voice packages or services installed on the user's device; their behavior and privacy terms are outside the WVAB codebase.

The app includes an in-app Privacy Policy with the same implementation boundary.

---

## 20. Licensing

Original WVAB source code is distributed under the repository **MIT License**.

Third-party software, models, fonts, datasets, and transitive dependencies retain their own licenses and are not relicensed merely because WVAB uses or stores them.

Important examples include:

- Ultralytics software/model assets;
- the bundled `yolov8n.pt` / exported YOLO model asset;
- MiDaS components/model assets;
- ONNX Runtime;
- Flutter/Dart packages;
- Noto fonts.

Before redistribution or commercial deployment, review:

- [`LICENSE`](LICENSE)
- [`PROJECT_OWNERSHIP.md`](PROJECT_OWNERSHIP.md)
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

The Flutter app also exposes the installed package license registry from its Open Source Licenses screen.

---

## 21. Academic use and citation

WVAB can be used as a software platform for experiments in assistive computer vision, secure edge-camera streaming, human-centered audio guidance, monocular distance estimation, perception-driven navigation, and edge deployment.

When publishing results, distinguish clearly between:

- **detector output**;
- **qualitative proximity**;
- **approximate monocular meter estimates**;
- **externally calibrated metric distance**;
- **relative monocular depth**;
- **metric localization**;
- **visual-clearance route hints**;
- **planner output**.

Do not report these as interchangeable measurements.

If you cite the repository as software, a simple BibTeX entry is:

```bibtex
@software{shagor_wvab_2026,
  author  = {Md Shahanur Islam Shagor},
  title   = {Wireless Vision-Aid for the Blind (WVAB)},
  year    = {2026},
  version = {1.0.0},
  url     = {https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind},
  note    = {Assistive computer-vision and secure edge-camera research platform}
}
```

For reproducibility, academic results should additionally record the exact Git commit, model checksum, hardware, camera configuration, Android/Python runtime version, dataset version, and experiment configuration.

---

## 22. Maintainer and contact

**Md Shahanur Islam Shagor**  
Project maintainer and original author of the WVAB-specific architecture, integration code, documentation, deployment tooling, and other original WVAB contributions unless repository history states otherwise.

- **GitHub:** [smshagor-dev](https://github.com/smshagor-dev)
- **Website:** [smshagor.com](https://smshagor.com)
- **Email:** [smshagor.dev@gmail.com](mailto:smshagor.dev@gmail.com)
- **Mobile:** `+7 995 494-98-36`
- **Repository:** [github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind](https://github.com/smshagor-dev/wireless-Vision-Aid-for-the-blind)

Bug reports and reproducible engineering issues are welcome through GitHub Issues. When reporting a mobile camera/detector problem, include the Android device model, Android version, camera source, exact build/commit, and what happened immediately before the failure.

---

## Final engineering note

WVAB is intentionally conservative about what it claims. A high-confidence object detection is not the same thing as safe navigation; a large bounding box is not a calibrated range sensor; monocular depth is not automatically metric; and a green CI run is not a substitute for target-device testing.

The project is designed so those boundaries remain visible in the code, documentation, mobile UI, tests, and deployment process. That makes it more useful for serious development and research than a system that reports certainty it has not measured.
