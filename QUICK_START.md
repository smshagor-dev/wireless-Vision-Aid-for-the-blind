# WVAB Quick Start

## 1. Setup and deterministic diagnostics

WVAB requires Python 3.10+.

```bash
./quick_start.sh setup
./quick_start.sh doctor
./quick_start.sh doctor --full --camera 0 --tts
```

The doctor is offline-first and non-interactive. It does not require Internet connectivity or claim that hardware is field-safe.

## 2. Local or IP-camera runtime

USB/local camera:

```bash
./quick_start.sh run vision --camera 0
```

Smartphone/IP camera: use the exact trusted URL displayed by the phone app. WVAB does not scan the local subnet for cameras.

```bash
./quick_start.sh run phone http://192.168.1.20:8080/video --test-only
./quick_start.sh run phone http://192.168.1.20:8080/video
```

This runtime reports qualitative proximity only; it does not label bounding-box heuristics as meters and exposes no remote control socket.

## 3. Pair an ESP32-CAM with Raspberry Pi

Generate matching, git-ignored device credentials:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
./quick_start.sh doctor --deployment
```

Flash `esp32_cam_stream.ino` with the generated `esp32_secrets.h` beside the sketch, then start the authenticated AES-GCM edge path:

```bash
./quick_start.sh run esp32
```

The secure wire format uses a fresh non-zero sender session ID at each ESP32 boot/Python sender start. The complete 14-byte header is AES-GCM authenticated, authentication and frame replays are rejected, and a fresh authenticated session allows the frame counter to restart safely after a sender reboot. See `SECURE_UDP_PROTOCOL.md` for the exact contract.

For station-mode Wi-Fi, pass `--station --ssid ... --wifi-password ... --server-ip ...` to the credential generator.

## 4. Optional MiDaS depth provisioning

```bash
python tools/download_models.py midas
```

The MiDaS weight is not stored in the source tree. The downloader verifies its checksum and prepares the Torch Hub source cache for later offline depth startup.

## 5. Secure Python UDP server/client

For a Python camera sender instead of ESP32, export deployment-specific `WVAB_UDP_KEY_HEX` and `WVAB_UDP_TOKEN`, then run:

```bash
./quick_start.sh run udp-server
./quick_start.sh run udp-client 127.0.0.1
```

The quick-start UDP path forces authentication and encryption. `udp_streaming.py` remains the compatibility entrypoint; the transport/session implementation lives in `core/udp_runtime.py`.

## 6. Raspberry Pi systemd service

After setup and credential generation, keep the project `.venv` and install the service with:

```bash
sudo bash deployment/rpi/install_service.sh
```

The installer requires `.venv/bin/python` with Python 3.10+ and renders the service to use that interpreter. This prevents a rebooted service from accidentally running with a system Python that lacks WVAB dependencies.

## 7. Root command dispatcher

```bash
python main.py --help
python main.py doctor --full --camera 0
python main.py vision --camera 0
python main.py phone http://192.168.1.20:8080/video --test-only
python main.py udp-server --config wvab_config.sample.json
```

## 8. C++ planner experiment

```bash
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release
```

The planner output is experimental and is not a certified mobility-safety controller. `cpp/build/` is intentionally ignored.

## License note

Original WVAB code is distributed under the repository MIT License. Third-party software/model/font assets retain their own licenses and terms; review `THIRD_PARTY_NOTICES.md` before redistribution or commercial deployment.
