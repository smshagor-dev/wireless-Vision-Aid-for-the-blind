# WVAB Mobile

WVAB Mobile is the Android companion application for Wireless Vision-Aid for the Blind.

## Foundation scope

This first mobile wave provides:

- accessibility-first Material 3 interface with large semantic controls
- camera preview using the official Flutter `camera` plugin
- spoken feedback abstraction backed by `flutter_tts`
- built-in Android haptic feedback abstraction
- Bengali, English, Russian, and Hindi speech-language selection
- edge-server endpoint configuration with strict local validation
- explicit transport state that does **not** pretend an edge connection exists before Secure UDP Protocol v2 is implemented
- deterministic Android host-project bootstrap
- Flutter analyze, widget tests, and split debug APK builds in CI

Secure UDP Protocol v2 integration and on-device ONNX inference are intentionally separate follow-up waves. The mobile app must not introduce an unauthenticated/plaintext fallback for wearable deployment.

## Toolchain

- Flutter 3.47.0
- Dart 3.11+
- Android SDK 24+ (required by the current Flutter camera plugin)

## Develop

```bash
cd mobile/flutter
flutter pub get
flutter analyze
flutter test
```

## Generate the Android host project

The Android host is generated rather than vendored so it follows the pinned Flutter template. Run:

```bash
cd mobile/flutter
bash tool/bootstrap_android.sh
```

The bootstrap script creates the Android project, enforces Android SDK 24, and adds only the permissions currently required by this foundation: camera, internet, and vibration.

Then build architecture-specific debug APKs:

```bash
flutter build apk --debug --split-per-abi
```

Expected outputs include:

```text
build/app/outputs/flutter-apk/app-arm64-v8a-debug.apk
build/app/outputs/flutter-apk/app-armeabi-v7a-debug.apk
build/app/outputs/flutter-apk/app-x86_64-debug.apk
```

## Repository demo APK

A CI-built 64-bit ARM demo APK is kept in the repository for convenient installation on compatible Android phones:

```text
mobile/flutter/demo/wvab-mobile-demo-arm64-v8a.apk
```

The demo is generated only after Flutter analysis, tests, Android host contract checks, APK compilation, and the repository-size guard pass. Verify it against:

```text
mobile/flutter/demo/SHA256SUMS.txt
```

The repository demo targets `arm64-v8a`. Use the CI artifacts or build locally when a different Android ABI is required.

## Safety status

The app is an assistive/research prototype. Camera preview, speech, and vibration availability are not evidence that a route is safe. Metric distance/navigation claims remain subject to the calibration and validation gates documented in the repository root.
