# WVAB Mobile Demo APK

The stale demo APKs that contained the regressed launcher icon have been removed.

This branch restores the committed WVAB launcher artwork under `tool/branding/` as the source of truth and rebuilds the Android demo from that icon source in CI.

The CI publication step writes the fresh 64-bit ARM APK back to this folder as:

`wvab-mobile-demo-arm64-v8a.apk`

Build contract:

- WVAB committed launcher artwork is materialized from `tool/branding/`
- adaptive launcher foreground uses the matching committed source
- Flutter analyze and widget tests must pass
- Android host and launcher checksums must pass
- split APK build and APK verification must pass before publication

The resulting APK is an assistive prototype and is not a certified navigation or safety device.
