# WVAB Validation Evidence

This directory documents how to collect repeatable runtime evidence. Generated CSV/JSON evidence files are intentionally git-ignored because they can be large and may contain host/runtime metadata.

Evidence collection does **not** certify WVAB as a mobility or medical device. It records measurements that can support a later validation report.

## Record a soak run

Start the WVAB runtime with a health file, then record it together with optional process/system telemetry:

```bash
python tools/soak_monitor.py \
  --health wvab_udp_server_health.json \
  --pid <WVAB_PROCESS_PID> \
  --interval 5 \
  --duration 28800 \
  --output evidence/soak-8h.csv
```

`28800` seconds is 8 hours. Omit `--pid` when only WVAB health plus host-wide CPU/memory/temperature are needed. Omit `--duration` to record until Ctrl+C.

The recorder flushes and attempts to fsync every sample so a partial run remains useful after an interruption.

## Summarize a run

```bash
python tools/summarize_soak.py evidence/soak-8h.csv \
  --json evidence/soak-8h-summary.json
```

The summary reports:

- sample count and observed duration
- latency p50/p95/p99/max from sampled runtime health
- FPS min/median/max
- health-record age and completed-frame idle maxima
- process RSS first/last/max/growth when a PID is supplied
- available host temperature maximum/median
- count of missing/invalid health samples

A summary intentionally does not emit a pass/fail safety verdict. Thresholds must be justified for the exact hardware, model, network, and intended use.

## Recommended metadata to record separately

For each evidence set, record at least:

- source commit SHA and release/tag if applicable
- Raspberry Pi / PC hardware revision
- OS, kernel, Python, Torch, Ultralytics, OpenCV versions
- ESP32 board revision and Arduino-ESP32 core version
- camera and audio hardware
- model file identity/checksum
- secure UDP protocol revision and generated-pair rotation date
- test network/RF conditions
- whether MiDaS, VO, ORB-SLAM3, OpenVINO, or other optional paths were enabled
- known test interruptions or environmental changes

Never commit AES keys, UDP/WebSocket tokens, camera credentials, private video, or personally identifying participant data with evidence artifacts.

## Other required evidence

See `PRODUCTION_READINESS.md`. Automated telemetry is only one part of the gate; dropout/fault injection, model accuracy, calibrated-depth/localization error, battery/thermal behavior, and structured blind/low-vision user evaluation require their own controlled procedures and records.
