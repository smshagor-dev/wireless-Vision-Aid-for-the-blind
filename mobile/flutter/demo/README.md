# WVAB Mobile Demo APK

`wvab-mobile-demo-arm64-v8a.apk` is the WVAB Mobile v0.3.0 stability/full-detection Android release demo for 64-bit ARM devices.

- Full model coverage: all 80 classes supported by the bundled YOLOv8n COCO model are enabled by default.
- Existing installs migrate from the previous 11-class selection to the full 80-class detector set.
- Startup: settings, keystore, TTS, and optional feedback failures are isolated instead of terminating the app.
- Inference: XNNPACK is preferred with CPU fallback; device-fragile NNAPI is not used.
- Feedback: TTS/haptics run outside the inference hot path so camera detection does not wait for speech completion.
- Launcher icon: current restored WVAB branding; previous deterministic launcher icon is blocked by CI.
- Build type: optimized Flutter release APK.
- ABI: arm64-v8a.
- Minimum Android SDK: 24.

The bundled model recognizes the 80 COCO labels it was trained for. Arbitrary objects or custom mobility classes such as curb/pothole/stairs require a compatible trained model; this build does not make unsupported accuracy claims.

Verify the APK against `SHA256SUMS.txt` after download.
