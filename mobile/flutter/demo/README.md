# WVAB Mobile v1.0.1 Camera-Stability Demo APK

`wvab-mobile-demo-arm64-v8a.apk` is the WVAB Mobile **v1.0.1** Android release demo for 64-bit ARM devices.

- App version: 1.0.1 (build 7)
- Camera lifecycle start/stop operations are serialized.
- Stale camera permission/initialization sessions are invalidated before they can reuse disposed controllers.
- Camera preview is established before ONNX inference initialization begins.
- ONNX Runtime uses the CPU provider for device-stable native execution.
- Camera and ESP32 teardown is defensive and idempotent.
- Inference is throttled to reduce camera/native runtime pressure.
- All 80 COCO classes supported by the bundled YOLOv8n model remain enabled by default.
- Current restored WVAB launcher branding is retained.
- Build type: optimized Flutter release APK.
- ABI: arm64-v8a.
- Minimum Android SDK: 24.

This build specifically addresses the process crash observed when opening the phone camera.

Verify the APK against `SHA256SUMS.txt` after download.
