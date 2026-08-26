# WVAB Mobile v1.0.0 Demo APK

`wvab-mobile-demo-arm64-v8a.apk` is the WVAB Mobile **v1.0.0** Android release demo for 64-bit ARM devices.

- App version: 1.0.0 (build 6)
- Full model coverage: all 80 classes supported by the bundled YOLOv8n COCO model are enabled by default.
- Existing installs migrate from the previous 11-class selection to the full 80-class detector set.
- Startup failures from settings, keystore, TTS, or optional feedback are isolated instead of terminating the app.
- Inference uses XNNPACK with CPU fallback for wider Android device stability.
- TTS/haptics run outside the inference hot path so camera detection does not wait for speech completion.
- Current restored WVAB launcher branding is used; the old deterministic launcher icon is blocked by CI.
- Build type: optimized Flutter release APK.
- ABI: arm64-v8a.
- Minimum Android SDK: 24.

The bundled detector recognizes the 80 COCO classes it was trained for. Custom WVAB mobility classes such as curb, pothole, or stairs require an appropriately trained model.

Verify the APK against `SHA256SUMS.txt` after download.
