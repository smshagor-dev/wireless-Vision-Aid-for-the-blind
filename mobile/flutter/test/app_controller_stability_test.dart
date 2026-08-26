import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/controllers/app_controller.dart';
import 'package:wvab_mobile/core/models/app_settings.dart';
import 'package:wvab_mobile/core/services/detection_history_store.dart';
import 'package:wvab_mobile/core/services/esp32_credentials_store.dart';
import 'package:wvab_mobile/core/services/feedback_service.dart';
import 'package:wvab_mobile/core/services/settings_store.dart';
import 'package:wvab_mobile/core/services/speech_service.dart';
import 'package:wvab_mobile/core/vision/detection.dart';
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

class _RecordingSpeechService implements SpeechService {
  final List<String> spoken = <String>[];
  String? initializedLanguage;
  @override
  Future<void> initialize(String languageCode) async => initializedLanguage = languageCode;
  @override
  Future<void> setLanguage(String languageCode) async => initializedLanguage = languageCode;
  @override
  Future<void> speak(String message) async => spoken.add(message);
  @override
  Future<void> stop() async {}
}

class _ThrowingFeedbackService implements FeedbackService {
  @override
  Future<void> light() async => throw StateError('haptics unavailable');
  @override
  Future<void> medium() async => throw StateError('haptics unavailable');
  @override
  Future<void> urgent() async => throw StateError('haptics unavailable');
}

class _NoopFeedbackService implements FeedbackService {
  @override
  Future<void> light() async {}
  @override
  Future<void> medium() async {}
  @override
  Future<void> urgent() async {}
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
  Future<MobileInferenceResult> run(Float32List nchwInput, {required double confidenceThreshold}) async =>
      const MobileInferenceResult(detections: [], inferenceDuration: Duration(milliseconds: 1));
  @override
  Future<void> close() async => _ready = false;
}

class _ExactInferenceEngine implements InferenceEngine {
  bool _ready = false;
  double? threshold;
  @override
  bool get isReady => _ready;
  @override
  Future<void> initialize() async => _ready = true;
  @override
  Future<MobileInferenceResult> run(Float32List nchwInput, {required double confidenceThreshold}) async {
    threshold = confidenceThreshold;
    return const MobileInferenceResult(
      detections: [
        Detection(
          classId: 0,
          label: 'person',
          confidence: 0.82,
          box: BoundingBox(left: 0.35, top: 0.1, right: 0.65, bottom: 0.62),
        ),
        Detection(
          classId: 73,
          label: 'book',
          confidence: 0.94,
          box: BoundingBox(left: 0.05, top: 0.05, right: 0.32, bottom: 0.64),
        ),
        Detection(
          classId: 39,
          label: 'bottle',
          confidence: 0.90,
          box: BoundingBox(left: 0.72, top: 0.08, right: 0.92, bottom: 0.58),
        ),
      ],
      inferenceDuration: Duration(milliseconds: 5),
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
    expect(controller.settings.detectionConfidence, 0.25);
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
  });

  test('all detections remain available while speech and UI focus one object with distance and route', () async {
    final inference = _ExactInferenceEngine();
    final speech = _RecordingSpeechService();
    final historyStore = MemoryDetectionHistoryStore();
    final controller = AppController(
      speechService: speech,
      feedbackService: _NoopFeedbackService(),
      settingsStore: MemorySettingsStore(const AppSettings(vibrationEnabled: false, userName: 'Tester')),
      historyStore: historyStore,
      credentialsStore: MemoryEsp32CredentialsStore(),
      inferenceEngine: inference,
    );

    await controller.initialize();
    final result = await controller.processTensor(Float32List(3 * 320 * 320));
    await Future<void>.delayed(Duration.zero);

    expect(inference.threshold, 0.25);
    expect(result.detections.map((item) => item.label).toSet(), {'person', 'book', 'bottle'});
    expect(result.detections.first.label, 'book');
    expect(controller.focusedGuidance, isNotNull);
    expect(controller.focusedGuidance!.detection.label, 'book');
    expect(speech.spoken, hasLength(1));
    expect(speech.spoken.single, contains('Book'));
    expect(speech.spoken.single, contains('estimated 1 to 2 meters away'));
    expect(speech.spoken.single, isNot(contains('Bottle')));
    expect(speech.spoken.single, isNot(contains('Person')));
    expect(
      speech.spoken.single.contains('appears clearer') || speech.spoken.single.contains('Stop'),
      isTrue,
    );
    expect(controller.history.map((item) => item.label).toSet(), {'person', 'book', 'bottle'});

    await Future<void>.delayed(Duration.zero);
    final stored = await historyStore.load();
    expect(stored.map((item) => item.label).toSet(), {'person', 'book', 'bottle'});
  });

  test('saved profile speaks welcome on future app launch', () async {
    final speech = _RecordingSpeechService();
    final inference = _ExactInferenceEngine();
    final controller = AppController(
      speechService: speech,
      feedbackService: _NoopFeedbackService(),
      settingsStore: MemorySettingsStore(const AppSettings(
        firstRunCompleted: true,
        userName: 'Shagor',
        vibrationEnabled: false,
      )),
      credentialsStore: MemoryEsp32CredentialsStore(),
      inferenceEngine: inference,
    );

    await controller.initialize();
    await Future<void>.delayed(Duration.zero);
    expect(speech.spoken, contains('Welcome Mr. Shagor'));
  });

  test('clearing history removes locally stored events', () async {
    final historyStore = MemoryDetectionHistoryStore();
    final controller = AppController(
      speechService: _RecordingSpeechService(),
      feedbackService: _NoopFeedbackService(),
      settingsStore: MemorySettingsStore(const AppSettings(userName: 'Tester')),
      historyStore: historyStore,
      credentialsStore: MemoryEsp32CredentialsStore(),
      inferenceEngine: _ExactInferenceEngine(),
    );
    await controller.initialize();
    await controller.processTensor(Float32List(3 * 320 * 320));
    expect(controller.history, isNotEmpty);
    await controller.clearHistory();
    expect(controller.history, isEmpty);
    expect(await historyStore.load(), isEmpty);
  });
}
