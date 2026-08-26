# WVAB Mobile Demo APK

`wvab-mobile-demo-arm64-v8a.apk` is the freshly rebuilt optimized Android release demo for 64-bit ARM devices.

- Launcher icon: restored from the committed WVAB branding source under `tool/branding/`
- Old deterministic launcher icon: explicitly blocked by CI
- Languages: English, Bangla, Russian, Hindi
- Build type: Flutter release APK
- ABI: arm64-v8a
- Minimum Android SDK: 24
- Validation: Flutter analyze, widget tests, Android host checks, launcher source/PNG validation, split release APK build, repository-size gate, and APK verification all pass before publication.

Verify the APK against `SHA256SUMS.txt` after download.

Secure UDP Protocol v2 mobile streaming and object inference are not represented as active until implemented and validated. This is an assistive prototype, not a certified navigation or safety device.
