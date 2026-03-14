<!--
Name: Md. Shahanur Islam Shagor
Autonomous Systems & UAV Researcher | Cybersecurity Specialist | Software Engineer
Voronezh State University of Forestry and Technologies
Build for Blind people within 15$
-->

# Wireless Vision-Aid for the Blind (WVAB)

WVAB is a real-time vision assistance system for blind and low-vision users.  
It detects objects from camera input and provides spoken guidance with position and distance.

## Features
- Real-time object detection (YOLOv8)
- Audio feedback for object position and distance
- GUI-based real camera testing
- Multilingual labels from JSON
- Runtime language selection
- Smartphone camera support (IP stream)
- Raspberry Pi edge mode (ESP32-CAM -> Pi -> audio)
- Model training, validation, and export utilities
- Optional Windows C++ speech backend (`wvab_speaker.exe`)

## Project Structure
- `vision_server.py`: Main runtime for ESP32/IP camera streams
- `camera_gui.py`: Desktop GUI camera test and live detection
- `test_system.py`: End-to-end diagnostics and real test launcher
- `smartphone_camera.py`: Smartphone IP camera setup helper
- `train_navigation_model.py`: Train/val/export for YOLO models
- `multilingual_labels.common.json`: Main multilingual labels + phrase map
- `multilingual_labels.sample.json`: Sample mapping file
- `deployment/rpi/wvab_edge.env`: Raspberry Pi edge environment defaults
- `deployment/rpi/wvab_edge_start.sh`: Raspberry Pi edge start script
- `deployment/rpi/wvab_edge.service`: Raspberry Pi systemd service
- `tools/update_goal.py`: Update navigation goal file for dynamic planning
- `install_tts_voice_packs.ps1`: Windows language/speech pack installer
- `cpp/speaker_cli.cpp`: Windows SAPI speech CLI (for optional C++ speech path)

## Requirements
- Python 3.8+
- Windows recommended for current TTS flow
- Camera (webcam / ESP32-CAM / smartphone IP camera)
- `pip install -r requirements.txt`

## Quick Start
1. Install dependencies:
```powershell
pip install -r requirements.txt
```

2. Run full diagnostics and GUI test:
```powershell
python test_system.py
```

3. Run main server:
```powershell
python vision_server.py
```

## Offline (Edge AI) Mode
Basic object detection works fully offline using a local YOLO model.

Requirements:
- Keep a local model file in the project (default: `yolov8n.pt`)
- No internet connection is needed once the model file is present

By default, WVAB forces offline behavior for Ultralytics. If you want to allow
online downloads later, set:
```powershell
$env:WVAB_OFFLINE = "0"
```

## Language and Voice

### Text Language
- Object names and phrases come from `multilingual_labels.common.json`.
- Add new languages by adding language keys (for example `ru`, `bn`, `hi`) in JSON.
- Test flow and server startup both support language selection.

### Voice Language (Real Device)
- Spoken language requires installed TTS voice packs on the device.
- If selected voice is unavailable, system attempts default voice.

Install voice packs (Run as Administrator):
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_tts_voice_packs.ps1 -Languages ru-RU,en-US -CopyToSettings
```

Install any language:
```powershell
.\install_tts_voice_packs.ps1 -Languages "bn,hi,ar" -CopyToSettings
.\install_tts_voice_packs.ps1 -Languages hi-IN,bn-BD,fr-FR -CopyToSettings
```

Expose OneCore voices to SAPI (Run as Administrator):
```powershell
.\enable_onecore_voices.ps1
```

### Font Support for BN/HI/AR Overlay
If camera overlay shows `[][][][]`, install fonts or use bundled Noto fonts in `assets/fonts`:
- `assets/fonts/NotoSansBengali-Regular.ttf`
- `assets/fonts/NotoSansDevanagari-Regular.ttf`
- `assets/fonts/NotoNaskhArabic-Regular.ttf`

You can also force a font:
```powershell
$env:WVAB_FONT_PATH="C:\Path\To\YourFont.ttf"
```

### Depth Model (MiDaS)
If depth shows "Unavailable", ensure MiDaS weights exist:
```powershell
$env:WVAB_MIDAS_WEIGHTS="data\models\midas_v21_small_256.pt"
python training\depth_diag.py
```

## Optional: Build C++ Speaker (Windows)
If `wvab_speaker.exe` exists, runtime can use it for speech.

```powershell
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release --target wvab_speaker
```

Output should be available at one of:
- `cpp/build/wvab_speaker.exe`
- `cpp/build/Release/wvab_speaker.exe`

## Training Custom Models
Train:
```powershell
python train_navigation_model.py train --data data/wvab.yaml --model yolov8n.pt --epochs 80 --device 0
```

Validate:
```powershell
python train_navigation_model.py val --model runs/wvab/navigation/weights/best.pt --data data/wvab.yaml
```

Export:
```powershell
python train_navigation_model.py export --model runs/wvab/navigation/weights/best.pt --format onnx
```

With multilingual mapping output:
```powershell
python train_navigation_model.py train --data data/wvab.yaml --language-map multilingual_labels.sample.json --labels-out runs/wvab/multilingual_labels.json
```

## Accelerated Inference (TensorRT / OpenVINO)
For production latency, export optimized models:

```powershell
# Set model path (optional)
$env:WVAB_MODEL="yolov8n.pt"
python export_accelerated_models.py
```

Outputs:
- TensorRT: `.engine`
- OpenVINO: `<model>_openvino_model/` (example: `yolov8n_openvino_model/`)

Run with OpenVINO (no code change needed):
```powershell
$env:WVAB_OPENVINO = "1"
$env:WVAB_MODEL = "yolov8n.pt"
python vision_server.py
```

Or point directly to the OpenVINO export:
```powershell
$env:WVAB_OPENVINO = "1"
$env:WVAB_MODEL = "yolov8n_openvino_model"
python vision_server.py
```

## Smartphone Camera Mode
```powershell
python smartphone_camera.py
```

Use manual IP mode for faster setup.

## Raspberry Pi Edge (ESP32-CAM -> Pi -> Audio)
Use your Raspberry Pi 4 as the "central brain" and keep the ESP32-CAM on glasses.
The Pi receives the low-latency stream and plays audio over Bluetooth or wired earphones.

1. Install dependencies on Raspberry Pi:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv espeak-ng libatlas-base-dev
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure Pi edge env:
```bash
nano deployment/rpi/wvab_edge.env
```

3. Start the UDP vision server:
```bash
bash deployment/rpi/wvab_edge_start.sh
```

4. On ESP32-CAM, set `UDP_HOST` to the Pi IP and flash `esp32_cam_stream.ino`.

See `production.md` for the full end-to-end Raspberry Pi flow (hardware, software mapping, voice).

## Secure UDP + WebSocket Control
Encrypted UDP is supported for low-latency video with privacy protection.

Config file (recommended):
```powershell
python udp_streaming.py server --config wvab_config.sample.json
python udp_streaming.py client --config wvab_config.sample.json
```

Server (UDP Vision):
```powershell
$env:WVAB_UDP_ENCRYPT = "1"
$env:WVAB_UDP_KEY_HEX = "0102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20"
$env:WVAB_UDP_AUTH = "1"
$env:WVAB_UDP_TOKEN = "change-me"
$env:WVAB_UDP_HEALTH_PATH = "wvab_udp_server_health.json"
python udp_streaming.py server --host 0.0.0.0 --port 9999 --language en --headless --auto-restart
```

Client (Python webcam):
```powershell
$env:WVAB_UDP_ENCRYPT = "1"
$env:WVAB_UDP_KEY_HEX = "0102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20"
$env:WVAB_UDP_AUTH = "1"
$env:WVAB_UDP_TOKEN = "change-me"
$env:WVAB_UDP_HEALTH_PATH = "wvab_udp_client_health.json"
python udp_streaming.py client --server-ip 192.168.4.1 --server-port 9999 --camera 0 --auto-restart
```

WebSocket control (default port 8765):
```json
{"cmd":"set_language","value":"bn"}
{"cmd":"set_all_objects","value":true}
{"cmd":"set_confidence","value":0.4}
```

## Troubleshooting
- `name 'np' is not defined`: update to latest `camera_gui.py`.
- First voice only / no second voice: use latest code (speech queue fixes already included).
- RU text shows but RU speech not correct: install RU speech pack on device.
- `cmake not recognized`: install CMake and add to PATH.
- Unicode text in frame not rendering: use latest GUI/server code (Unicode overlay support added).
- BN/HI/AR speech not available: run `install_tts_voice_packs.ps1` as Administrator, then `enable_onecore_voices.ps1`, and reboot.
- Depth unavailable: set `WVAB_MIDAS_WEIGHTS` and run `training\depth_diag.py`.

## Notes for Deployment
- For blind-user safety, prioritize audio reliability:
  - keep language packs installed on target device
  - test with `test_system.py` before field use
  - keep model and labels file synced

## License
This project is licensed under the MIT License. See `LICENSE`.
