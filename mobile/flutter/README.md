# WVAB Standalone Android Runtime

WVAB Mobile is the offline Android runtime for Wireless Vision-Aid for the Blind. The Android phone is the compute device: no Raspberry Pi, desktop server, cloud API, or HTTP backend is required for normal assistance.

## Runtime modes

### Phone camera

```text
Android camera -> YUV420 -> local preprocessing -> packaged ONNX detector
               -> source-space detections -> relative proximity -> TTS / haptics
```

This mode requires no network connection after installation.

### ESP32-CAM

```text
ESP32-CAM -> local Wi-Fi -> Secure UDP Protocol v2 -> AES-GCM decrypt
          -> JPEG frame reassembly -> packaged ONNX detector
          -> relative proximity -> TTS / haptics
```

Internet access is not required. ESP32-CAM pairing requires a 16/24/32-byte AES key and an authentication token of at least 16 characters. Credentials are stored with Android secure storage. Replay counters and ordinary preferences are persisted separately.

## First launch

The first launch asks for:

1. Interface / voice language: English, বাংলা, Русский, or हिन्दी.
2. Camera source: Phone Camera or ESP32-CAM.
3. ESP32 secure pairing values when ESP32-CAM is selected.

These choices are stored locally and can be changed later from Settings, Camera Source, and Language.

## Offline model build

The repository contains the pinned source checkpoint `../../yolov8n.pt`. Before building the APK, generate and validate the packaged ONNX asset:

```bash
python -m pip install -r tool/model-export-requirements.txt
python tool/export_mobile_model.py
```

The exporter creates:

```text
assets/models/yolov8n_320.onnx
.generated/mobile_model_manifest.json
```

The graph must expose a static `[1, 3, 320, 320]` input and a raw YOLO detection output containing 84 channels. Runtime code loads only the packaged asset. It does not download a model and does not fall back to a remote backend.

## Toolchain

- Flutter 3.47.0
- Dart 3.11+
- Android SDK 24+
- flutter_onnxruntime 1.8.4 / ONNX Runtime 1.23 runtime wrapper
- build-time Ultralytics 8.4.113 + ONNX 1.22.0

## Develop

```bash
cd mobile/flutter
python -m pip install -r tool/model-export-requirements.txt
python tool/export_mobile_model.py
flutter pub get
flutter analyze
flutter test
bash tool/bootstrap_android.sh
flutter build apk --debug --split-per-abi
```

Expected outputs:

```text
build/app/outputs/flutter-apk/app-arm64-v8a-debug.apk
build/app/outputs/flutter-apk/app-armeabi-v7a-debug.apk
build/app/outputs/flutter-apk/app-x86_64-debug.apk
```

CI verifies the ONNX graph and checksum manifest, Android permissions/minimum SDK, professional launcher branding, Flutter analyzer/tests, encrypted ESP32 protocol tests, and the split APK outputs.

## Repository demo APK

The existing repository demo path is:

```text
mobile/flutter/demo/wvab-mobile-demo-arm64-v8a.apk
```

A standalone runtime build may exceed GitHub's normal 100 MB per-file repository limit because it contains the native ONNX Runtime library and packaged detector. When that happens, use the GitHub Actions APK artifact instead of committing an oversized binary to Git.

## Safety status

WVAB uses qualitative relative proximity (`immediate`, `close`, `medium`, `far`) derived from detection-box scale. It does **not** claim calibrated metric distance from a monocular camera.

The application remains an assistive prototype, not a certified navigation or safety device. Repository/CI validation demonstrates software behavior only. Physical Android handset performance, real ESP32-CAM radio behavior, thermals, battery life, sustained frame rate, latency, and user-safety outcomes require separate hardware validation.
