#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'android/app/src/main/AndroidManifest.xml'
APP_GRADLE = ROOT / 'android/app/build.gradle.kts'
ROOT_GRADLE = ROOT / 'android/build.gradle.kts'
PROGUARD = ROOT / 'android/app/proguard-rules.pro'
ORT_ANDROID_COORDINATE = 'com.microsoft.onnxruntime:onnxruntime-android:1.22.0'


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


def configure_proguard() -> None:
    PROGUARD.write_text(
        '# WVAB Android native-runtime stability rules.\n'
        '# flutter_onnxruntime requires ONNX Runtime Java/JNI symbols to survive release packaging.\n'
        '-keep class ai.onnxruntime.** { *; }\n'
        '-dontwarn ai.onnxruntime.**\n'
        '-keepclasseswithmembernames class * {\n'
        '    native <methods>;\n'
        '}\n',
        encoding='utf-8',
    )


def configure_root_gradle() -> None:
    text = ROOT_GRADLE.read_text(encoding='utf-8')
    marker = f'force("{ORT_ANDROID_COORDINATE}")'
    if marker not in text:
        stanza = (
            '\n// WVAB v1.0.0 stability pin: flutter_onnxruntime 1.8.2 contains the\n'
            '// Kotlin compatibility fix, while Android stays on ORT 1.22.0.\n'
            'allprojects {\n'
            '    configurations.configureEach {\n'
            '        resolutionStrategy {\n'
            f'            force("{ORT_ANDROID_COORDINATE}")\n'
            '        }\n'
            '    }\n'
            '}\n'
        )
        text = text.rstrip() + '\n' + stanza
    ROOT_GRADLE.write_text(text, encoding='utf-8')


def configure_app_gradle() -> None:
    text = APP_GRADLE.read_text(encoding='utf-8')
    if 'minSdk = 24' not in text:
        source = 'minSdk = flutter.minSdkVersion'
        if source not in text:
            raise SystemExit('Unexpected Android Gradle minSdk template')
        text = text.replace(source, 'minSdk = 24', 1)

    if 'isMinifyEnabled = false' not in text:
        signing = 'signingConfig = signingConfigs.getByName("debug")'
        if signing not in text:
            raise SystemExit('Unexpected Android Gradle release template')
        release_stability = (
            signing
            + '\n            // Keep release packaging deterministic for native camera/ORT plugins.\n'
            + '            isMinifyEnabled = false\n'
            + '            isShrinkResources = false\n'
            + '            proguardFiles(\n'
            + '                getDefaultProguardFile("proguard-android-optimize.txt"),\n'
            + '                "proguard-rules.pro",\n'
            + '            )'
        )
        text = text.replace(signing, release_stability, 1)
    APP_GRADLE.write_text(text, encoding='utf-8')


def main() -> None:
    if not MANIFEST.is_file() or not APP_GRADLE.is_file() or not ROOT_GRADLE.is_file():
        raise SystemExit('Run flutter create for Android before configuring the host project')
    configure_manifest()
    configure_proguard()
    configure_root_gradle()
    configure_app_gradle()


if __name__ == '__main__':
    main()
