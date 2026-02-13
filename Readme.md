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

## Smartphone Camera Mode
```powershell
python smartphone_camera.py
```

Use manual IP mode for faster setup.

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
