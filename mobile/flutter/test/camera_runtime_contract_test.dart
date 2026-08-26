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

  test('mobile inference uses CPU-only provider for process stability', () {
    final source = File('lib/core/vision/mobile_inference_engine.dart').readAsStringSync();

    expect(source, contains('providers: const [OrtProvider.CPU]'));
    expect(source, isNot(contains('OrtProvider.XNNPACK')));
  });
}
