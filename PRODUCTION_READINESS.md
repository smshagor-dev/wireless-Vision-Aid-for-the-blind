# WVAB Production-Readiness Gate

WVAB is currently a research/assistive prototype. This checklist defines evidence required before a build is described as field-ready. Passing unit tests alone is not sufficient.

## 1. Automated quality gate

Required on every PR:

- Python source compiles on supported CI versions.
- Core unit tests pass on Python 3.10, 3.11, and 3.12.
- Generated caches, logs, and CMake build output are not tracked.
- Full runtime smoke test is executed on at least one device-capable validation host before release.

## 2. Perception and distance

- Report object-detection precision/recall or mAP on a representative held-out mobility dataset.
- Test critical classes separately: person, moving vehicles, curb, stairs, crosswalk, pothole, pole, door.
- Bounding-box proximity labels are qualitative only.
- Any metric-distance claim must identify the calibration method, target camera, focal-length estimate, reference object assumptions, test range, MAE/RMSE, and failure cases.
- Monocular MiDaS/VO/monocular-SLAM output must not be presented as metric without an externally validated scale.

## 3. Navigation fail-safe behavior

`navigation_pipeline.py` must fail closed:

- camera unavailable -> `STOP`
- localization unavailable -> `STOP`
- path unavailable -> `STOP`
- path available but metric geometry uncalibrated -> `DEGRADED`
- calibrated metric path available -> `GUIDANCE_AVAILABLE`

The state file is an integration boundary, not a certified actuator controller. Audio/haptic/robot hardware adapters require their own hardware-specific safety validation.

## 4. Reliability evidence

Minimum release evidence:

- 8+ hour continuous soak test
- memory/CPU/GPU/temperature trend
- camera disconnect/reconnect test
- sender/network loss and recovery test
- TTS failure/recovery test
- watchdog and bounded auto-restart test
- malformed/incomplete UDP frame test

## 5. Security baseline

Required defaults:

- `WVAB_UDP_AUTH=1`
- `WVAB_UDP_ENCRYPT=1`
- AES key length 16/24/32 bytes; 32 bytes recommended
- unique token and key per deployment
- example credentials must never be reused in a real deployment

The current UDP payload uses AES-GCM integrity protection. Authentication expires and must be refreshed by the sender.

## 6. Realtime performance

Record distributions rather than one-off values:

- camera FPS
- inference latency p50/p95/p99
- end-to-end camera-to-audio latency p50/p95/p99
- UDP packet loss and incomplete-frame rate
- reconnect time

A historical target such as `latency < 200 ms` is not considered validated until measured on the actual deployment hardware and network.

## 7. Edge-device validation

For Raspberry Pi/ESP32-CAM builds record:

- exact hardware revision
- OS/kernel/Python versions
- model/export format
- sustained FPS and thermals
- power draw and battery runtime
- Wi-Fi/RF test environment
- audio output device and reconnect behavior

## 8. Accessibility/user evaluation

Before real-world mobility claims, conduct structured evaluation with blind/low-vision participants under an appropriate ethics/consent process. Record task success, false/missed warnings, cognitive/audio load, user preference, and failure cases.

## 9. Release artifacts

A public release should include:

- versioned source tag
- release notes and known limitations
- dependency/runtime versions
- model identity/checksum
- validation report and hardware configuration
- secure credential setup instructions
- no generated local cache/build/log files in source control
