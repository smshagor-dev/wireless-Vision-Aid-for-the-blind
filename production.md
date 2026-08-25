# WVAB Field Deployment Guide

WVAB is a research/assistive prototype, not a certified mobility or medical device. This guide describes supported deployment paths without making a field-safety claim.

## 1. Install the Raspberry Pi runtime

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv espeak-ng libatlas-base-dev
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run diagnostics before enabling the service:

```bash
python test_system.py
```

## 2. Generate paired device credentials

Do not put Wi-Fi passwords, UDP tokens, or AES keys in committed source files. Generate a matching ESP32 header and Raspberry Pi environment file locally:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
```

This creates two git-ignored files:

- `esp32_secrets.h`
- `deployment/rpi/wvab_edge.env`

The generated deployment uses a random AES-256 key, independent UDP/WebSocket tokens, and authentication/encryption enabled by default. `--force` explicitly rotates the pair; do not rotate only one side.

For station-mode Wi-Fi instead of the ESP32 access point:

```bash
python tools/generate_device_secrets.py \
  --station \
  --ssid "YOUR_WIFI" \
  --wifi-password "YOUR_PRIVATE_PASSWORD" \
  --server-ip "PI_IP_ADDRESS"
```

## 3. Flash the ESP32-CAM

Open `esp32_cam_stream.ino` in Arduino IDE with `esp32_secrets.h` beside it. Select the AI Thinker ESP32-CAM board and flash the firmware.

The supported UDP path validates non-placeholder secrets, sends encrypted authentication packets, refreshes authentication periodically, and encrypts every video chunk with AES-GCM using fresh frame nonces. The firmware does not print Wi-Fi passwords, UDP tokens, or AES keys to serial output.

The unauthenticated MJPEG server remains a development-only fallback in source and is disabled by default.

## 4. Start the Raspberry Pi server

```bash
bash deployment/rpi/wvab_edge_start.sh
```

The launcher refuses to start when the credential file is missing, authentication/encryption is disabled, the token is too short, the AES key is malformed, or the YOLO model is missing.

## 5. Optional systemd service

The repository does not use a hard-coded `/home/pi/...` service. Install one rendered for the current checkout/user:

```bash
sudo bash deployment/rpi/install_service.sh
```

Then inspect it:

```bash
systemctl status wvab_edge.service
journalctl -u wvab_edge.service -f
```

The generated service uses `NoNewPrivileges`, a private `/tmp`, a read-only system view, and only grants write access to the WVAB checkout.

## 6. Containerized headless server

Generate the local credential file before running Compose. `.dockerignore` prevents the local Pi environment file and ESP32 header from entering the image build context; Compose injects the server environment at runtime instead.

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
docker compose build
docker compose up -d udp-vision-server
```

The image runs as an unprivileged `wvab` user. The default service exposes only UDP port 9999 and disables TTS and WebSocket control inside the container.

The optional navigation profile requires Linux camera-device access:

```bash
export WVAB_VIDEO_GID="$(getent group video | cut -d: -f3)"
export WVAB_CAMERA_DEVICE=/dev/video0
docker compose --profile navigation up -d navigation-engine prometheus
```

The profile forces headless mode. Metrics are published by the navigation process on port 8000 and scraped by Prometheus. Host access to ports 8000 and 9090 is bound to loopback only.

## 7. Other camera sources

For a local USB/webcam Python sender, export a unique `WVAB_UDP_KEY_HEX` and `WVAB_UDP_TOKEN`, then run:

```bash
python udp_streaming.py server --config wvab_config.sample.json
python udp_streaming.py client --config wvab_config.sample.json --server-ip 127.0.0.1 --camera 0
```

For a smartphone/IP camera, pass the trusted local stream URL as `--camera`. Do not expose camera feeds or the UDP/control ports directly to the public Internet.

## 8. Depth and navigation research path

MiDaS is optional and scale-ambiguous. Provision it once while online:

```bash
python tools/download_models.py midas
```

Metric occupancy updates remain disabled unless external camera/depth calibration is explicitly configured. `navigation_pipeline.py` publishes `STOP`, `DEGRADED`, or `GUIDANCE_AVAILABLE` state instead of claiming a route is safe.

## 9. Validation before any supervised trial

At minimum capture evidence for:

- 8+ hour soak behavior and memory/thermal trends,
- camera/network/TTS dropout and recovery,
- malformed/incomplete UDP handling,
- authenticated/encrypted transport verification,
- model accuracy on representative mobility hazards,
- end-to-end latency p50/p95/p99,
- calibration error for any metric-distance claim,
- supervised evaluation with blind/low-vision users under an appropriate ethics/consent process.

See `PRODUCTION_READINESS.md` for the full release gate. The absence of a failed automated test is not evidence of field safety.
