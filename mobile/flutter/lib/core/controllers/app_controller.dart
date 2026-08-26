import 'dart:async';

import 'package:flutter/foundation.dart';

import '../localization/app_strings.dart';
import '../localization/detection_label_localizer.dart';
import '../localization/language_catalog.dart';
import '../localization/standalone_strings.dart';
import '../models/app_settings.dart';
import '../models/detection_history_entry.dart';
import '../services/detection_history_store.dart';
import '../services/esp32_credentials_store.dart';
import '../services/feedback_service.dart';
import '../services/settings_store.dart';
import '../services/speech_service.dart';
import '../vision/detection.dart';
import '../vision/guidance_engine.dart';
import '../vision/mobile_inference_engine.dart';
import '../vision/vision_input.dart';

enum LocalRuntimeState { idle, initializing, ready, error }

class AppController extends ChangeNotifier {
  AppController({
    required this.speechService,
    required this.feedbackService,
    required this.settingsStore,
    required this.credentialsStore,
    required this.inferenceEngine,
    DetectionHistoryStore? historyStore,
    DetectionLabelLocalizer? labelLocalizer,
    GuidanceEngine? guidanceEngine,
  })  : historyStore = historyStore ?? MemoryDetectionHistoryStore(),
        labelLocalizer = labelLocalizer ?? DetectionLabelLocalizer(),
        guidanceEngine = guidanceEngine ?? GuidanceEngine();

  final SpeechService speechService;
  final FeedbackService feedbackService;
  final SettingsStore settingsStore;
  final Esp32CredentialsStore credentialsStore;
  final InferenceEngine inferenceEngine;
  final DetectionHistoryStore historyStore;
  final DetectionLabelLocalizer labelLocalizer;
  final GuidanceEngine guidanceEngine;

  AppSettings _settings = const AppSettings();
  Esp32Credentials? _esp32Credentials;
  LocalRuntimeState _runtimeState = LocalRuntimeState.idle;
  String? _runtimeError;
  List<Detection> _lastDetections = const <Detection>[];
  Duration? _lastInferenceDuration;
  Future<void>? _inferenceInitialization;
  List<DetectionHistoryEntry> _history = <DetectionHistoryEntry>[];
  Future<void> _historyWrite = Future<void>.value();
  final Map<String, DateTime> _lastHistoryCapture = <String, DateTime>{};
  GuidanceEvent? _focusedGuidance;
  bool _guidanceSpeechBusy = false;

  AppSettings get settings => _settings;
  AppStrings get strings => AppStrings(_settings.languageCode);
  StandaloneStrings get standaloneStrings => StandaloneStrings(_settings.languageCode);
  Esp32Credentials? get esp32Credentials => _esp32Credentials;
  bool get esp32Configured => _esp32Credentials?.isConfigured ?? false;
  LocalRuntimeState get runtimeState => _runtimeState;
  String? get runtimeError => _runtimeError;
  List<Detection> get lastDetections => _lastDetections;
  Duration? get lastInferenceDuration => _lastInferenceDuration;
  List<DetectionHistoryEntry> get history => List<DetectionHistoryEntry>.unmodifiable(_history);
  GuidanceEvent? get focusedGuidance => _focusedGuidance;

  Future<void> initialize() async {
    try {
      _settings = await settingsStore.load();
    } catch (error, stackTrace) {
      debugPrint('WVAB settings initialization failed; using safe defaults: $error\n$stackTrace');
      _settings = const AppSettings();
    }

    try {
      _history = (await historyStore.load()).take(300).toList(growable: true);
    } catch (error, stackTrace) {
      debugPrint('WVAB history initialization failed; continuing with empty history: $error\n$stackTrace');
      _history = <DetectionHistoryEntry>[];
    }

    try {
      await labelLocalizer.initialize();
    } catch (error, stackTrace) {
      debugPrint('WVAB label localization initialization failed; using English label fallback: $error\n$stackTrace');
    }

    try {
      _esp32Credentials = await credentialsStore.read();
    } catch (error, stackTrace) {
      debugPrint('WVAB secure credential initialization failed: $error\n$stackTrace');
      _esp32Credentials = null;
    }

    try {
      await speechService.initialize(_settings.languageCode);
      if (_settings.firstRunCompleted && _settings.userName.trim().isNotEmpty) {
        unawaited(_speakWelcome());
      }
    } catch (error, stackTrace) {
      debugPrint('WVAB TTS initialization failed; continuing without startup failure: $error\n$stackTrace');
    }
    notifyListeners();
  }

  Future<void> updateSettings(AppSettings settings) async {
    if (settings.esp32ListenPort < 1 || settings.esp32ListenPort > 65535) {
      throw const FormatException('ESP32 UDP port must be in 1..65535.');
    }
    if (settings.detectionConfidence < 0.05 || settings.detectionConfidence > 0.99) {
      throw const FormatException('Detection confidence must be between 0.05 and 0.99.');
    }
    _settings = settings.copyWith(userName: settings.userName.trim());
    await settingsStore.save(_settings);
    try {
      await speechService.setLanguage(_settings.languageCode);
    } catch (error, stackTrace) {
      debugPrint('WVAB TTS language update failed: $error\n$stackTrace');
    }
    notifyListeners();
  }

  Future<void> completeOnboarding({
    String? userName,
    required String languageCode,
    required CameraSourceType cameraSource,
  }) async {
    final name = (userName ?? _settings.userName).trim();
    if (name.length < 2 || name.length > 80) {
      throw const FormatException('Please enter your name (2–80 characters).');
    }
    if (!LanguageCatalog.contains(languageCode)) {
      throw const FormatException('Unsupported language.');
    }
    await updateSettings(_settings.copyWith(
      firstRunCompleted: true,
      userName: name,
      languageCode: languageCode,
      cameraSource: cameraSource,
    ));
    unawaited(_speakWelcome());
  }

  Future<void> setLanguage(String languageCode) async {
    if (!LanguageCatalog.contains(languageCode)) return;
    await updateSettings(_settings.copyWith(languageCode: languageCode));
  }

  Future<void> setCameraSource(CameraSourceType source) async {
    await updateSettings(_settings.copyWith(cameraSource: source));
  }

  Future<void> saveEsp32Credentials(Esp32Credentials credentials) async {
    await credentialsStore.write(credentials);
    _esp32Credentials = credentials;
    notifyListeners();
  }

  Future<void> clearEsp32Credentials() async {
    await credentialsStore.clear();
    _esp32Credentials = null;
    notifyListeners();
  }

  Future<void> ensureInferenceReady() {
    if (_runtimeState == LocalRuntimeState.ready && inferenceEngine.isReady) {
      return Future<void>.value();
    }
    final existing = _inferenceInitialization;
    if (existing != null) return existing;

    final initialization = _initializeInference();
    _inferenceInitialization = initialization;
    return initialization.whenComplete(() {
      if (identical(_inferenceInitialization, initialization)) {
        _inferenceInitialization = null;
      }
    });
  }

  Future<void> _initializeInference() async {
    _runtimeState = LocalRuntimeState.initializing;
    _runtimeError = null;
    notifyListeners();
    try {
      await inferenceEngine.initialize();
      _runtimeState = LocalRuntimeState.ready;
    } catch (error, stackTrace) {
      _runtimeState = LocalRuntimeState.error;
      _runtimeError = error.toString();
      debugPrint('WVAB inference initialization failed: $error\n$stackTrace');
      rethrow;
    } finally {
      notifyListeners();
    }
  }

  Future<MobileInferenceResult> processTensor(
    Float32List input, {
    LetterboxTransform? transform,
  }) async {
    if (_runtimeState != LocalRuntimeState.ready || !inferenceEngine.isReady) {
      await ensureInferenceReady();
    }
    final result = await inferenceEngine.run(
      input,
      confidenceThreshold: _settings.detectionConfidence,
    );

    final remapped = result.detections.map((detection) {
      final box = transform == null ? detection.box : transform.modelBoxToSource(detection.box);
      return Detection(
        classId: detection.classId,
        label: detection.label,
        confidence: detection.confidence,
        box: box,
      );
    }).where((detection) => detection.box.area > 0).toList(growable: false);

    final selected = remapped
        .where((detection) => _settings.detectedClasses.contains(detection.label))
        .toList(growable: false);
    _lastInferenceDuration = result.inferenceDuration;

    _recordHistory(selected);

    if (selected.isEmpty) {
      _focusedGuidance = null;
    } else {
      final currentFocus = _focusedGuidance;
      if (currentFocus != null && !selected.any((detection) => detection.label == currentFocus.detection.label)) {
        _focusedGuidance = null;
      }
      if (!_guidanceSpeechBusy) {
        final event = guidanceEngine.choose(selected);
        if (event != null) {
          _focusedGuidance = event;
          unawaited(_announceFocusedGuidance(event));
        }
      }
    }

    final focusLabel = _focusedGuidance?.detection.label;
    final displayDetections = focusLabel == null
        ? selected
        : <Detection>[
            ...selected.where((detection) => detection.label == focusLabel),
            ...selected.where((detection) => detection.label != focusLabel),
          ];
    _lastDetections = displayDetections;

    notifyListeners();
    return MobileInferenceResult(
      detections: displayDetections,
      inferenceDuration: result.inferenceDuration,
    );
  }

  String localizedObjectLabel(String label) => labelLocalizer.objectLabel(label, _settings.languageCode);

  String focusedGuidanceText(GuidanceEvent event) =>
      labelLocalizer.focusedGuidanceMessage(event, _settings.languageCode);

  String focusedDistanceText(GuidanceEvent event) =>
      labelLocalizer.distanceDisplay(event.distanceBand, _settings.languageCode);

  String focusedRouteText(GuidanceEvent event) =>
      labelLocalizer.travelAdviceShort(event.travelAdvice, _settings.languageCode);

  Future<void> clearHistory() async {
    _history = <DetectionHistoryEntry>[];
    _lastHistoryCapture.clear();
    await historyStore.clear();
    notifyListeners();
  }

  void _recordHistory(List<Detection> detections) {
    if (detections.isEmpty) return;
    final now = DateTime.now();
    final bestByLabel = <String, Detection>{};
    for (final detection in detections) {
      final previous = bestByLabel[detection.label];
      if (previous == null || detection.confidence > previous.confidence) {
        bestByLabel[detection.label] = detection;
      }
    }

    final ordered = bestByLabel.values.toList(growable: false)
      ..sort((a, b) => b.confidence.compareTo(a.confidence));
    var changed = false;
    for (final detection in ordered.take(5)) {
      final last = _lastHistoryCapture[detection.label];
      if (last != null && now.difference(last) < const Duration(seconds: 5)) continue;
      _lastHistoryCapture[detection.label] = now;
      _history.insert(
        0,
        DetectionHistoryEntry(
          id: '${now.microsecondsSinceEpoch}-${detection.classId}-${detection.label}',
          timestamp: now,
          classId: detection.classId,
          label: detection.label,
          confidence: detection.confidence,
          proximity: classifyRelativeProximity(detection.box),
          direction: classifySpatialDirection(detection.box),
          cameraSource: _settings.cameraSource.storageValue,
        ),
      );
      changed = true;
    }
    if (!changed) return;
    if (_history.length > 300) {
      _history.removeRange(300, _history.length);
    }
    final snapshot = List<DetectionHistoryEntry>.from(_history);
    _historyWrite = _historyWrite.then((_) => historyStore.save(snapshot)).catchError((Object error, StackTrace stackTrace) {
      debugPrint('WVAB detection history write failed: $error\n$stackTrace');
    });
  }

  Future<void> _announceFocusedGuidance(GuidanceEvent event) async {
    if (_guidanceSpeechBusy) return;
    _guidanceSpeechBusy = true;
    try {
      await announce(
        labelLocalizer.focusedGuidanceMessage(event, _settings.languageCode),
        urgent: event.urgent || event.travelAdvice == TravelAdvice.stop,
      );
    } finally {
      _guidanceSpeechBusy = false;
    }
  }

  Future<void> _speakWelcome() async {
    if (!_settings.speechEnabled || _settings.userName.trim().isEmpty) return;
    try {
      await speechService.speak(
        labelLocalizer.welcomeMessage(_settings.userName, _settings.languageCode),
      );
    } catch (error, stackTrace) {
      debugPrint('WVAB welcome speech failed: $error\n$stackTrace');
    }
  }

  Future<void> announce(String message, {bool urgent = false}) async {
    if (_settings.vibrationEnabled) {
      try {
        if (urgent) {
          await feedbackService.urgent();
        } else {
          await feedbackService.medium();
        }
      } catch (error, stackTrace) {
        debugPrint('WVAB haptic feedback failed: $error\n$stackTrace');
      }
    }
    if (_settings.speechEnabled) {
      try {
        await speechService.speak(message);
      } catch (error, stackTrace) {
        debugPrint('WVAB speech feedback failed: $error\n$stackTrace');
      }
    }
  }

  Future<void> stopFeedback() async {
    guidanceEngine.reset();
    _focusedGuidance = null;
    try {
      await speechService.stop();
    } catch (error, stackTrace) {
      debugPrint('WVAB speech stop failed: $error\n$stackTrace');
    } finally {
      _guidanceSpeechBusy = false;
    }
  }

  @override
  void dispose() {
    inferenceEngine.close();
    super.dispose();
  }
}
