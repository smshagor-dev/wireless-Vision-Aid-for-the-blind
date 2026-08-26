import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('camera runtime keeps lifecycle transitions serialized and generation guarded', () {
    final source = File('lib/features/camera/camera_screen.dart').readAsStringSync();

    expect(source, contains('_sourceTransition'));
    expect(source, contains('_sourceGeneration'));
    expect(source, contains('_isCurrentSource'));
    expect(source, contains('_enqueueSourceTransition'));
    expect(source, contains('AppLifecycleState.inactive'));
    expect(source, contains('AppLifecycleState.resumed'));
    expect(source, contains('await _safeDisposeCamera(controller)'));
  });

  test('v1.0.0 pins conservative Android camera and ORT native backends', () {
    final pubspec = File('pubspec.yaml').readAsStringSync();

    expect(pubspec, contains('version: 1.0.0+8'));
    expect(pubspec, contains('camera_android: 0.10.11'));
    expect(pubspec, contains('flutter_onnxruntime: 1.7.1'));
    expect(pubspec, isNot(contains('version: 1.0.1')));
    expect(pubspec, isNot(contains('version: 1.0.2')));
  });

  test('Android generator preserves ONNX JNI symbols and disables release shrinking', () {
    final source = File('tool/configure_android.py').readAsStringSync();

    expect(source, contains('-keep class ai.onnxruntime.** { *; }'));
    expect(source, contains('-keepclasseswithmembernames class *'));
    expect(source, contains('isMinifyEnabled = false'));
    expect(source, contains('isShrinkResources = false'));
    expect(source, contains('proguard-rules.pro'));
  });

  test('mobile inference uses CPU-only provider for process stability', () {
    final source = File('lib/core/vision/mobile_inference_engine.dart').readAsStringSync();

    expect(source, contains('providers: const [OrtProvider.CPU]'));
    expect(source, isNot(contains('OrtProvider.XNNPACK')));
  });
}
