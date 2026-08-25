#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'android/app/src/main/AndroidManifest.xml'
GRADLE = ROOT / 'android/app/build.gradle.kts'


def configure_manifest() -> None:
    text = MANIFEST.read_text(encoding='utf-8')
    permissions = (
        '    <uses-permission android:name="android.permission.CAMERA" />\n'
        '    <uses-permission android:name="android.permission.INTERNET" />\n'
        '    <uses-permission android:name="android.permission.VIBRATE" />\n'
    )
    if 'android.permission.CAMERA' not in text:
        marker = '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
        if marker not in text:
            raise SystemExit('Unexpected AndroidManifest.xml template')
        text = text.replace(marker, marker + permissions, 1)

    if 'android.intent.action.TTS_SERVICE' not in text:
        application_marker = '    <application'
        if application_marker not in text:
            raise SystemExit('Unexpected AndroidManifest.xml application template')
        queries = (
            '    <queries>\n'
            '        <intent>\n'
            '            <action android:name="android.intent.action.TTS_SERVICE" />\n'
            '        </intent>\n'
            '    </queries>\n'
        )
        text = text.replace(application_marker, queries + application_marker, 1)

    if 'android:label="wvab_mobile"' in text:
        text = text.replace('android:label="wvab_mobile"', 'android:label="WVAB"', 1)
    elif 'android:label="WVAB"' not in text:
        raise SystemExit('Unexpected Android application label template')

    MANIFEST.write_text(text, encoding='utf-8')


def configure_gradle() -> None:
    text = GRADLE.read_text(encoding='utf-8')
    if 'minSdk = 24' not in text:
        source = 'minSdk = flutter.minSdkVersion'
        if source not in text:
            raise SystemExit('Unexpected Android Gradle minSdk template')
        text = text.replace(source, 'minSdk = 24', 1)
    GRADLE.write_text(text, encoding='utf-8')


def main() -> None:
    if not MANIFEST.is_file() or not GRADLE.is_file():
        raise SystemExit('Run flutter create for Android before configuring the host project')
    configure_manifest()
    configure_gradle()


if __name__ == '__main__':
    main()
