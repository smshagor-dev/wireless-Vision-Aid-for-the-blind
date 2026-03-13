<!--
Name: Md. Shahanur Islam Shagor
Autonomous Systems & UAV Researcher | Cybersecurity Specialist | Software Engineer
Voronezh State University of Forestry and Technologies
Build for Blind people within 15$
-->

# WVAB Production Readiness Guide (Public Release)

This document converts the current research prototype into a public-release baseline across:
- Windows PC (primary runtime)
- ESP32-CAM (camera sender)
- Android phone (IP camera sender)

## 1. Release Criteria (Must Pass)
- End-to-end demo on all targets with consistent audio guidance.
- 8+ hour soak test without memory growth or crashes.
- Offline mode validated (no network dependency for model).
- Security enabled (UDP auth + encryption).
- Clear failure modes: camera loss, network loss, TTS failure.

## 2. Security Baseline
- Require UDP auth by default (`WVAB_UDP_AUTH=1`).
- Require encryption by default (`WVAB_UDP_ENCRYPT=1`).
- AES key length must be 16/24/32 bytes.
- Rotate `WVAB_UDP_TOKEN` and AES key per deployment.

Generate a 32-byte key (hex):
```powershell
@'
import os
print(os.urandom(32).hex())
'@ | python -
```

Generate a random token:
```powershell
@'
import secrets
print(secrets.token_urlsafe(24))
'@ | python -
```

## 3. Windows PC (Vision Server)
Recommended production command:
```powershell
$env:WVAB_UDP_ENCRYPT="1"
$env:WVAB_UDP_AUTH="1"
$env:WVAB_UDP_KEY_HEX="<32-byte-hex>"
$env:WVAB_UDP_TOKEN="<random-token>"
$env:WVAB_UDP_HEADLESS="1"
$env:WVAB_UDP_TTS="1"
python udp_streaming.py server --host 0.0.0.0 --port 9999 --language en --headless --log-path wvab_udp.log
```

Recommended config-based launch:
```powershell
python udp_streaming.py server --config wvab_config.sample.json
python udp_streaming.py client --config wvab_config.sample.json
```

Operational checks:
- Confirm CPU/GPU utilization stays stable over time.
- Verify audio cadence feels safe (no spam, no silence).
- Keep `yolov8n.pt` locally for offline use.

## 4. ESP32-CAM (Camera Sender)
Production steps:
- Stable Wi-Fi power supply and RF environment.
- Fixed IP or DHCP reservation.
- UDP packet loss test in real environment.

## 5. Android (IP Camera Sender)
Use a stable IP camera app with fixed FPS and resolution.
Recommended:
- 640x360 or lower to reduce jitter.
- Fixed bitrate if available.
- Disable battery optimizations for the app.

## 6. Operational Runbook
Start order:
1. Start server on Windows.
2. Start camera sender (ESP32/Android/PC).
3. Confirm logs: FPS > 10, latency < 200ms baseline.

Failure handling:
- If stream idle for >10s, sender reconnects; server resets buffers.
- If TTS fails, logs show error; restart service.
- Optional: auto-restart on crash using `--auto-restart` flags.
- Optional: server idle restart via `WVAB_UDP_SERVER_IDLE_RESTART_S`.
- Optional: watchdog restarts via `WVAB_UDP_WATCHDOG_*` settings.
- Health file output via `WVAB_UDP_HEALTH_PATH`.

## 7. Test Checklist
- UDP auth on/off behavior (unauthenticated should be ignored).
- AES encryption on/off behavior.
- Language switching (labels + TTS).
- Camera dropout recovery (disconnect/reconnect).
- Minimum latency under typical Wi-Fi load.
- Tracking stability (IDs persist across frames).

## 8. Release Artifacts
For public release, prepare:
- Versioned zip or installer.
- Release notes and known limitations.
- Preconfigured `.env` or setup guide for keys/tokens.
