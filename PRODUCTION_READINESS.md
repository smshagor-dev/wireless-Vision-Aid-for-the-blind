# WVAB Production-Readiness Gate

WVAB is currently a research/assistive prototype. This checklist defines evidence required before a build is described as field-ready. Passing unit tests alone is not sufficient.

## 1. Automated quality gate

Required on every PR:

- Python source compiles on supported CI versions.
- Core unit tests pass on Python 3.10, 3.11, and 3.12.
- The distributable wheel contains internal WVAB packages, UDP auth-state support, and bundled Unicode fonts.
- C++17 navigation planner builds and its demo executes.
- ESP32 firmware compiles against the pinned Arduino-ESP32 core and keeps protocol-v2 authenticated AES-GCM behavior.
- ESP32 firmware has no unauthenticated MJPEG fallback.
- Generated caches, logs, CMake build output, local credentials, runtime replay state, and downloaded runtime models are not tracked.
- Full runtime smoke test is executed on at least one device-capable validation host before release.

## 2. Perception and distance

- Report object-detection precision/recall or mAP on a representative held-out mobility dataset.
- Test critical classes separately: person, moving vehicles, curb, stairs, crosswalk, pothole, pole, door.
- Verify custom underscore-style classes and generic COCO space-style aliases receive the same mobility priority/filtering policy.
- Bounding-box proximity labels are qualitative only.
- Any metric-distance claim must identify the calibration method, target camera, focal-length estimate, reference object assumptions, test range, MAE/RMSE, and failure cases.
- Monocular MiDaS/VO/monocular-SLAM output must not be presented as metric without an externally validated scale.

## 3. Navigation fail-safe behavior

`navigation_pipeline.py` must fail closed:

- camera unavailable -> `STOP`
- localization unavailable -> `STOP`
- path unavailable -> `STOP`
- path available but metric geometry/localization uncalibrated or stale -> `DEGRADED`
- coherent calibrated metric map + fresh metric localization + path available -> `GUIDANCE_AVAILABLE`

Calibrated depth must be converted to the same metric unit before it is used for both visual-odometry translation scale and occupancy mapping. A temporary loss of metric VO scale must not inject arbitrary unit translations. ORB-SLAM3 poses must expire when the external process stops updating them.

The state file is an integration boundary, not a certified actuator controller. Audio/haptic/robot hardware adapters require their own hardware-specific safety validation.

## 4. Reliability evidence

Minimum release evidence:

- 8+ hour continuous soak test
- memory/CPU/GPU/temperature trend
- camera disconnect/reconnect test
- sender/network loss and recovery test
- TTS failure/recovery test
- client/server watchdog and bounded auto-restart test
- malformed/incomplete UDP frame test
- packet reordering/loss test
- sender/ESP32 reboot with frame counter restarting at zero under a fresh authenticated session
- stale/retired-session replay test
- server/container restart followed by captured authentication-datagram replay test
- persistent replay-state loss/corruption recovery procedure test
- stale ORB-SLAM3 output test
- calibrated-depth dropout test

Use `tools/soak_monitor.py` and `tools/summarize_soak.py` to capture reproducible host/runtime evidence. These tools collect evidence; they do not themselves certify field readiness.

## 5. Security baseline

Required defaults:

- `WVAB_UDP_AUTH=1`
- `WVAB_UDP_ENCRYPT=1`
- AES key length 16/24/32 bytes; 32 bytes recommended
- UDP token length at least 16 characters
- unique token and key per deployment
- example credentials must never be reused in a real deployment
- authentication/encryption exceptions require the explicit development override `WVAB_ALLOW_INSECURE_UDP=1`
- WebSocket control binds to `127.0.0.1` by default
- every WebSocket control command is authenticated
- use a dedicated `WVAB_WS_TOKEN` when control is exposed beyond loopback

For the supported UDP wire protocol:

- the complete 14-byte header, including the non-zero 32-bit session ID, is authenticated as AES-GCM AAD
- every encrypted datagram carries its frame base nonce
- authentication plaintext is protocol v2: version + monotonic uint64 auth counter + next uint32 frame ID + token
- legacy token-only authentication is rejected
- authentication nonce replay is rejected from a bounded in-memory cache
- the highest accepted authentication counter is persisted before a session is granted/renewed
- persistent replay state survives normal Raspberry Pi process restarts and Docker container restarts/recreation
- a valid new sender session retires the old session for that UDP source
- authentication refresh may advance but must never move the completed-frame replay baseline backwards
- completed frame IDs are replay/order checked per authenticated source + session with wrap-aware serial comparison
- packet/chunk/frame size, authenticated-client state, replay caches, persistent session state, and in-flight buffering are bounded
- the server watchdog depends on completed/decodeable frames rather than authentication/chunk traffic
- old incompatible packet/authentication formats are not silently accepted

Replay-state durability is part of the security boundary. If `state/udp_replay_state.json`, the configured replay-state file, or the Docker `wvab-replay-state` volume is lost/deleted/rolled back, rotate/re-pair the UDP credentials before field use. A corrupt replay-state file must fail closed rather than reset silently.

See `SECURE_UDP_PROTOCOL.md` for the exact packet contract.

Remote WebSocket binding must be treated as an explicit deployment decision and protected by network-level controls as well as the application token.

## 6. Realtime performance

Record distributions rather than one-off values:

- camera FPS
- inference latency p50/p95/p99
- end-to-end camera-to-audio latency p50/p95/p99
- UDP packet loss and incomplete-frame rate
- replay/header-integrity rejection counts during fault injection
- reconnect/re-authentication time after sender reboot
- recovery time after server/container restart

A historical target such as `latency < 200 ms` is not considered validated until measured on the actual deployment hardware and network.

## 7. Edge-device validation

For Raspberry Pi/ESP32-CAM builds record:

- exact hardware revision
- OS/kernel/Python versions
- ESP32 board/core/camera-library versions
- source commit used on both ESP32 and Raspberry Pi
- secure UDP protocol/authentication version
- persistent replay-state location and backup/rotation procedure
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
- secure UDP protocol compatibility note
- replay-state preservation and credential-rotation instructions
- no generated local cache/build/log/credential/replay-state files in source control
