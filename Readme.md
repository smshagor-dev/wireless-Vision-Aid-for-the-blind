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
- If selected voice is unavailable, system falls back to English speech.

Install voice packs (Run as Administrator):
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_tts_voice_packs.ps1 -Languages ru-RU,en-US -CopyToSettings
```

Install any language:
```powershell
.\install_tts_voice_packs.ps1 -Languages hi-IN,bn-BD,fr-FR -CopyToSettings
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

## Notes for Deployment
- For blind-user safety, prioritize audio reliability:
  - keep language packs installed on target device
  - test with `test_system.py` before field use
  - keep model and labels file synced

## License
This project is licensed under the MIT License. See `LICENSE`.
