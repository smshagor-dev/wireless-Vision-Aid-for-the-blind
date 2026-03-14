# Production Guide (WVAB)

This guide creates a production-ready setup and shows step-by-step how to connect a real camera.
It includes code snippets for ESP32-CAM firmware and practical wiring/setup notes.

## 0) Hardware Connectivity (Setup)

In public places, operating without a local network is risky. First, create a stable local network.

1. Create a hotspot:
   Use a smartphone hotspot or a small 4G router.
   Note the hotspot SSID and password.

2. ESP32-CAM (Eye):
   Mount on glasses and connect to the hotspot Wi-Fi.
   It will stream video to the Raspberry Pi over UDP.

3. Raspberry Pi (Brain):
   Connect to the same Wi-Fi and receive the stream to run inference.
   Check Pi IP:
   ```bash
   hostname -I
   ```

4. Audio (Voice):
   Connect a Bluetooth neckband or 3.5mm wired headphones to the Pi.

### Network Modes (Hotspot vs ESP32 AP)

- Hotspot Mode (recommended for public use):
  ESP32-CAM and Pi both connect to the phone/router hotspot.
  In ESP32 firmware, set `USE_AP_MODE false` and set `WIFI_SSID`/`WIFI_PASSWORD`.

- ESP32 AP Mode:
  ESP32 creates its own Wi-Fi and the Pi connects to it.
  In this case set `USE_AP_MODE true`.

## 1) Production Base Setup (Server Device)

1. Install Python dependencies.

```powershell
pip install -r requirements.txt
```

2. Confirm the model file exists (default is `yolov8n.pt`).

3. Run a local diagnostics test once.

```powershell
python test_system.py
```

4. Choose the camera pipeline for production: USB webcam, smartphone IP camera, or ESP32-CAM.

## 2) Production Camera Connection Options

### Option 0: Raspberry Pi Edge (ESP32-CAM -> Pi -> Audio)

This is the full end-to-end flow for a wearable ESP32-CAM + Raspberry Pi 4 "central brain".
The Pi stays in a pocket or small bag, and plays audio to Bluetooth neckband or wired earphones.

#### Step A: Raspberry Pi OS setup

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv espeak-ng libatlas-base-dev
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Step B: Audio output (Bluetooth or 3.5mm)

Bluetooth quick pairing:
```bash
bluetoothctl
power on
agent on
scan on
pair XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
quit
```

Set default audio sink (PulseAudio/PipeWire):
```bash
pactl list short sinks
pactl set-default-sink <sink_name>
```

For 3.5mm wired audio, select analog output if needed:
```bash
sudo raspi-config
```

#### Step C: Configure WVAB edge env on Pi

Edit the edge env file and match the UDP key with ESP32:
```bash
nano deployment/rpi/wvab_edge.env
```

Recommended for ESP32 (no auth, 16-byte key):
```
WVAB_UDP_AUTH=0
WVAB_UDP_KEY_HEX=0102030405060708090A0B0C0D0E0F10
```

#### Step D: ESP32-CAM firmware setup

In `esp32_cam_stream.ino`, set:
- `UDP_HOST` to the Raspberry Pi IP
- `UDP_PORT` to 9999
- `USE_AP_MODE` true (ESP32 creates Wi-Fi) OR false (ESP32 joins your Wi-Fi)

AP mode example (ESP32 is 192.168.4.1, Pi gets 192.168.4.2):
```cpp
#define USE_AP_MODE true
const char* UDP_HOST = "192.168.4.2";
const int UDP_PORT = 9999;
```

Hotspot mode example (ESP32 joins phone/router Wi-Fi):
```cpp
#define USE_AP_MODE false
#define WIFI_SSID "YOUR_HOTSPOT_SSID"
#define WIFI_PASSWORD "YOUR_HOTSPOT_PASSWORD"
const char* UDP_HOST = "PI_IP_ADDRESS";
const int UDP_PORT = 9999;
```

#### Step E: Run the UDP vision server on Pi

```bash
chmod +x deployment/rpi/wvab_edge_start.sh
bash deployment/rpi/wvab_edge_start.sh
```

You should see frames and hear speech from the Pi.

#### Step F: Optional systemd service (auto-start)

1. Copy the service file and update the path if needed:
```bash
sudo cp deployment/rpi/wvab_edge.service /etc/systemd/system/wvab_edge.service
sudo nano /etc/systemd/system/wvab_edge.service
```

2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable wvab_edge
sudo systemctl start wvab_edge
```

3. Check logs:
```bash
journalctl -u wvab_edge -f
```

### Option A: USB Webcam (fastest setup)

1. Plug a USB webcam into the server device.

2. Start UDP server.

```powershell
python udp_streaming.py server --host 0.0.0.0 --port 9999 --language en --headless
```

3. Start UDP client using local webcam.

```powershell
python udp_streaming.py client --server-ip 127.0.0.1 --server-port 9999 --camera 0
```

4. If you want the full GUI overlay for testing, run the GUI camera test.

```powershell
python camera_gui.py
```

### Option B: Smartphone IP Camera

1. Install an IP camera app on the phone (example: IP Webcam).

2. Make sure the phone and server are on the same Wi-Fi.

3. Run the helper to confirm the stream URL.

```powershell
python smartphone_camera.py
```

4. Start UDP server.

```powershell
python udp_streaming.py server --host 0.0.0.0 --port 9999 --language en --headless
```

5. Start UDP client and pass the phone stream URL.

```powershell
python udp_streaming.py client --server-ip 127.0.0.1 --server-port 9999 --camera http://PHONE_IP:PORT/video
```

### Option C: ESP32-CAM (production wearable)

This is the most stable low-cost setup for field use.

#### Step 1: Add Wi-Fi credentials and UDP target in firmware

Open `esp32_cam_stream.ino` and add the block below near the top (after includes).
It defines Wi-Fi/AP names and sets the UDP target to the server device.

```cpp
// ===== Wi-Fi Credentials =====
// If USE_AP_MODE is true, ESP32 creates its own Wi-Fi.
// If USE_AP_MODE is false, ESP32 joins your existing Wi-Fi.

#define AP_SSID "WVAB_CAM"
#define AP_PASSWORD "wvab1234"

#define WIFI_SSID "YourWiFiName"
#define WIFI_PASSWORD "YourWiFiPassword"

// ===== UDP Target (Vision Server) =====
// If ESP32 is AP (192.168.4.1), your server should be 192.168.4.2
const char* UDP_HOST = "192.168.4.2";
const int UDP_PORT = 9999;
```

Also set these flags at the top of the file.

```cpp
#define USE_AP_MODE true
#define USE_SECURE_UDP true
```

#### Step 2: Match AES key between ESP32 and server

The ESP32 uses a 16-byte AES key (AES-128). Make sure the server uses the same key.

1. In `esp32_cam_stream.ino`, keep the AES key like this.

```cpp
static const uint8_t AES_KEY[16] = {
  0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
  0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
};
```

2. On the server, set the matching key as 32 hex characters.

```powershell
$env:WVAB_UDP_KEY_HEX = "0102030405060708090A0B0C0D0E0F10"
```

#### Step 3: Disable UDP auth for ESP32

The ESP32 firmware does not send auth packets, so the server must disable auth.

```powershell
$env:WVAB_UDP_AUTH = "0"
```

If you want auth, it must be added to the ESP32 firmware first.

#### Step 4: Flash ESP32-CAM

1. Open Arduino IDE.

2. Install the ESP32 boards package.

3. Select board: `AI Thinker ESP32-CAM`.

4. Select the correct COM port.

5. Upload `esp32_cam_stream.ino`.

#### Step 5: Connect the server to ESP32 Wi-Fi (AP mode)

1. On the server device, connect to the Wi-Fi network `WVAB_CAM`.

2. The ESP32 will be `192.168.4.1`.

3. The server should be `192.168.4.2` (assigned by the ESP32 AP).

#### Step 6: Run the UDP vision server

```powershell
$env:WVAB_UDP_ENCRYPT = "1"
$env:WVAB_UDP_AUTH = "0"
$env:WVAB_UDP_KEY_HEX = "0102030405060708090A0B0C0D0E0F10"
python udp_streaming.py server --host 0.0.0.0 --port 9999 --language en --headless
```

You should now receive frames from the ESP32-CAM.

## 2.5) Software Integration (Code Mapping)

Follow this mapping to complete the end-to-end flow.

1. ESP32-CAM firmware:
   Set Wi-Fi and `UDP_HOST` in `esp32_cam_stream.ino` and flash it.

2. Raspberry Pi inference (recommended UDP path):
   Run `udp_streaming.py server` to receive UDP frames and run YOLO inference.

3. MJPEG alternative:
   If you do not use UDP, run MJPEG stream with `vision_server.py`.

4. Navigation Planner (C++):
   You can compile and use `cpp/navigation_planner.cpp` on the Pi.
   Demo build:
   ```bash
   cd cpp
   mkdir -p build
   cmake -S . -B build
   cmake --build build --config Release
   ./build/navigation_demo
   ```

5. Depth + Mapping (optional heavy pipeline):
   `navigation_pipeline.py` uses `midas_v21_small_256.pt` for depth + grid update.
   This mode uses more resources on the Pi.

6. OpenVINO acceleration:
   Export OpenVINO models with `export_accelerated_models.py` and set them in
   `udp_streaming.py`/`vision_server.py`.
   ```bash
   python export_accelerated_models.py
   python udp_streaming.py server --model yolov8n_openvino_model --headless
   ```

7. Config goal update:
   `config/config.yaml` reads the goal from `config/goal.json`.
   For dynamic goals, use `tools/update_goal.py`.
   ```bash
   python tools/update_goal.py --x 5.0 --y 0.0 --frame local
   ```

## 2.6) Voice Feedback (Raspberry Pi)

Windows SAPI (`speaker_cli.cpp`) does not work on Pi.
Use `pyttsx3` + `espeak-ng` on the Pi.

```bash
sudo apt install -y espeak-ng
```

TTS control:
```bash
export WVAB_UDP_TTS=1
export WVAB_UDP_TTS_RATE=170
```

### Multi-language voice setup (Pi)

1. List available voices (espeak-ng):
```bash
espeak-ng --voices
espeak-ng --voices=bn
espeak-ng --voices=hi
```

2. List pyttsx3 voices (on Pi):
```bash
python - <<'PY'
import pyttsx3
e = pyttsx3.init()
for v in e.getProperty("voices"):
    print(v.id, "|", v.name)
PY
```

3. Select a specific voice:
```bash
export WVAB_UDP_TTS_VOICE=bn
export WVAB_UDP_TTS_RATE=170
```

If using `vision_server.py`:
```bash
export WVAB_TTS_VOICE=bn
```

Note: espeak-ng has good language coverage, but pronunciation quality varies by language.

## 3) Production Real Device Setup Notes

1. Power stability matters. Use a regulated 5V supply (2A recommended) for ESP32-CAM.

2. Mount the camera at chest level and avoid strong backlighting.

3. Use a static local Wi-Fi channel when possible to avoid dropouts.

4. Keep the server device on the same network as the camera or AP.

5. For faster startup, keep the model file (`yolov8n.pt`) in the project root.

6. Run a 2-minute live test before field use.

```powershell
python test_system.py
```

## 4) Optional: Production Config File

You can store settings in a config file and reuse them.

```powershell
python udp_streaming.py server --config wvab_config.sample.json
```

If you use ESP32-CAM, update `wvab_config.sample.json` to disable auth and to use a 16-byte key.

```json
"WVAB_UDP_AUTH": "0",
"WVAB_UDP_KEY_HEX": "0102030405060708090A0B0C0D0E0F10"
```

## 5) Troubleshooting (Production)

1. No frames arriving. Check `UDP_HOST` in `esp32_cam_stream.ino` and ensure the server is connected to the ESP32 AP if using AP mode.

2. Encrypted stream not working. Key length must be 16 bytes for ESP32 and must match `WVAB_UDP_KEY_HEX` on the server.

3. Stream works but no speech. Install voice packs and run `enable_onecore_voices.ps1`.

4. Low FPS or dropouts. Lower `TARGET_FPS` in `esp32_cam_stream.ino` and move the AP closer to the server device.

## 6) Android App (Kivy) End-to-End

A full mobile UI flow is available in `android_kivy/` with three screens:

1. App logo splash
2. Audio check
3. Language selection
4. Camera GUI preview

### Folder Layout

- `android_kivy/main.py`: Kivy app entrypoint
- `android_kivy/kv/wvab.kv`: Kivy UI layout
- `android_kivy/assets/logo.png`: App logo (replace with your real logo)
- `android_kivy/data/multilingual_labels.common.json`: Language list for UI
- `android_kivy/buildozer.spec`: Android build configuration

### Run Locally (Desktop)

```powershell
cd android_kivy
python main.py
```

### Build for Android (Buildozer)

Buildozer requires Linux. If you are on Windows, use WSL or a Linux VM.

```bash
cd android_kivy
pip install buildozer
buildozer -v android debug
```

The APK will be created under `android_kivy/bin/`.

### Audio Check Screen Notes

- The app uses `plyer.tts` for Android speech.
- If the phone has no TTS engine enabled, the status line will show a warning.

### Camera Screen Notes

- The Kivy `Camera` widget is used for the live preview.
- The detection pipeline is not yet attached on Android. To integrate detection:

1. Export a lightweight model (ONNX or TFLite).
2. Add `onnxruntime` or `tflite-runtime` to `requirements` in `buildozer.spec`.
3. Implement a frame callback in `main.py` to run inference and overlay results.

### Production Notes

- Replace `assets/logo.png` with your final app logo.
- Set package domain/name in `buildozer.spec` before release.
- Test TTS and camera permissions on real devices.
