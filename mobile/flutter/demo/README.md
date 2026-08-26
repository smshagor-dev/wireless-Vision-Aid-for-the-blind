# WVAB Mobile v1.0.0 Demo APK

This directory contains the verified Android arm64-v8a demo build for WVAB Mobile **v1.0.0**.

- App version: `1.0.0`
- ABI: `arm64-v8a`
- APK: `wvab-mobile-demo-arm64-v8a.apk`
- SHA256: `4458ab48b75d9218cb3e8459a31ae77f66297ad4b73f50b2ef68d8133d12ab37`
- CI source run: `32929761223`
- Detection model: bundled YOLOv8n 320 ONNX, 80 COCO classes
- Android ONNX Runtime: forced to 1.22.0 with the Kotlin-safe Flutter wrapper

The CI gate verified Dart analysis, 31 Flutter tests including detection-to-speech invocation, Android/TTS/ProGuard contracts, resolved ONNX Runtime dependency, release APK build, arm64 native ELF packaging, bundled model presence, and `versionName=1.0.0`.

Physical phone camera/speaker behavior still depends on the target Android device and cannot be proven by GitHub Actions alone.
