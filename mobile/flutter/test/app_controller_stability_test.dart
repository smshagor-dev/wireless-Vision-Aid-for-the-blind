import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/controllers/app_controller.dart';
import 'package:wvab_mobile/core/models/app_settings.dart';
import 'package:wvab_mobile/core/services/esp32_credentials_store.dart';
import 'package:wvab_mobile/core/services/feedback_service.dart';
import 'package:wvab_mobile/core/services/settings_store.dart';
import 'package:wvab_mobile/core/services/speech_service.dart';
import 'package:wvab_mobile/core/vision/mobile_inference_engine.dart';

class _ThrowingSettingsStore implements SettingsStore {
  @override
  Future<AppSettings> load() async => throw StateError('settings unavailable');

  @override
  Future<void> save(AppSettings settings) async {}
}

class _ThrowingCredentialsStore implements Esp32CredentialsStore {
  @override
  Future<Esp32Credentials?> read() async => throw StateError('keystore unavailable');

  @override
  Future<void> write(Esp32Credentials credentials) async {}

  @override
  Future<void> clear() async {}
}

class _ThrowingSpeechService implements SpeechService {
  @override
  Future<void> initialize(String languageCode) async => throw StateError('tts unavailable');

  @override
  Future<void> setLanguage(String languageCode) async => throw StateError('tts unavailable');

  @override
  Future<void> speak(String message) async => throw StateError('tts unavailable');

  @override
  Future<void> stop() async => throw StateError('tts unavailable');
}

class _ThrowingFeedbackService implements FeedbackService {
  @override
  Future<void> light() async => throw StateError('haptics unavailable');

  @override
  Future<void> medium() async => throw StateError('haptics unavailable');

  @override
  Future<void> urgent() async => throw StateError('haptics unavailable');
}

class _DelayedInferenceEngine implements InferenceEngine {
  final Completer<void> gate = Completer<void>();
  int initializeCalls = 0;
  bool _ready = false;

  @override
  bool get isReady => _ready;

  @override
  Future<void> initialize() async {
    initializeCalls += 1;
    await gate.future;
    _ready = true;
  }

  @override
  Future<MobileInferenceResult> run(
    Float32List nchwInput, {
    required double confidenceThreshold,
  }) async {
    return const MobileInferenceResult(
      detections: [],
      inferenceDuration: Duration(milliseconds: 1),
    );
  }

  @override
  Future<void> close() async => _ready = false;
}

AppController _controller(_DelayedInferenceEngine inference) {
  return AppController(
    speechService: _ThrowingSpeechService(),
    feedbackService: _ThrowingFeedbackService(),
    settingsStore: _ThrowingSettingsStore(),
    credentialsStore: _ThrowingCredentialsStore(),
    inferenceEngine: inference,
  );
}

void main() {
  test('startup plugin failures fall back instead of terminating initialization', () async {
    final inference = _DelayedInferenceEngine();
    final controller = _controller(inference);

    await expectLater(controller.initialize(), completes);
    expect(controller.settings.detectedClasses, allCocoDetectedClasses);
    expect(controller.esp32Credentials, isNull);
  });

  test('concurrent inference readiness calls share one initialization', () async {
    final inference = _DelayedInferenceEngine();
    final controller = _controller(inference);

    final first = controller.ensureInferenceReady();
    final second = controller.ensureInferenceReady();

    await Future<void>.delayed(Duration.zero);
    expect(inference.initializeCalls, 1);
    expect(controller.runtimeState, LocalRuntimeState.initializing);

    inference.gate.complete();
    await Future.wait([first, second]);

    expect(inference.initializeCalls, 1);
    expect(controller.runtimeState, LocalRuntimeState.ready);
    expect(inference.isReady, isTrue);
  });
}
