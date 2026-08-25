import 'dart:typed_data';

import 'package:flutter/foundation.dart';

import '../localization/app_strings.dart';
import '../localization/standalone_strings.dart';
import '../models/app_settings.dart';
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
    GuidanceEngine? guidanceEngine,
  }) : guidanceEngine = guidanceEngine ?? GuidanceEngine();

  final SpeechService speechService;
  final FeedbackService feedbackService;
  final SettingsStore settingsStore;
  final Esp32CredentialsStore credentialsStore;
  final InferenceEngine inferenceEngine;
  final GuidanceEngine guidanceEngine;

  AppSettings _settings = const AppSettings();
  Esp32Credentials? _esp32Credentials;
  LocalRuntimeState _runtimeState = LocalRuntimeState.idle;
  String? _runtimeError;
  List<Detection> _lastDetections = const [];
  Duration? _lastInferenceDuration;

  AppSettings get settings => _settings;
  AppStrings get strings => AppStrings(_settings.languageCode);
  StandaloneStrings get standaloneStrings => StandaloneStrings(_settings.languageCode);
  Esp32Credentials? get esp32Credentials => _esp32Credentials;
  bool get esp32Configured => _esp32Credentials?.isConfigured ?? false;
  LocalRuntimeState get runtimeState => _runtimeState;
  String? get runtimeError => _runtimeError;
  List<Detection> get lastDetections => _lastDetections;
  Duration? get lastInferenceDuration => _lastInferenceDuration;

  Future<void> initialize() async {
    _settings = await settingsStore.load();
    _esp32Credentials = await credentialsStore.read();
    await speechService.initialize(_settings.languageCode);
    notifyListeners();
  }

  Future<void> updateSettings(AppSettings settings) async {
    if (settings.esp32ListenPort < 1 || settings.esp32ListenPort > 65535) {
      throw const FormatException('ESP32 UDP port must be in 1..65535.');
    }
    if (settings.detectionConfidence < 0.05 || settings.detectionConfidence > 0.99) {
      throw const FormatException('Detection confidence must be between 0.05 and 0.99.');
    }
    _settings = settings;
    await settingsStore.save(settings);
    await speechService.setLanguage(settings.languageCode);
    notifyListeners();
  }

  Future<void> completeOnboarding({
    required String languageCode,
    required CameraSourceType cameraSource,
  }) async {
    if (!AppStrings.supportedLanguages.containsKey(languageCode)) {
      throw const FormatException('Unsupported language.');
    }
    await updateSettings(_settings.copyWith(
      firstRunCompleted: true,
      languageCode: languageCode,
      cameraSource: cameraSource,
    ));
  }

  Future<void> setLanguage(String languageCode) async {
    if (!AppStrings.supportedLanguages.containsKey(languageCode)) return;
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

  Future<void> ensureInferenceReady() async {
    if (_runtimeState == LocalRuntimeState.ready) return;
    if (_runtimeState == LocalRuntimeState.initializing) return;
    _runtimeState = LocalRuntimeState.initializing;
    _runtimeError = null;
    notifyListeners();
    try {
      await inferenceEngine.initialize();
      _runtimeState = LocalRuntimeState.ready;
    } catch (error) {
      _runtimeState = LocalRuntimeState.error;
      _runtimeError = error.toString();
      rethrow;
    } finally {
      notifyListeners();
    }
  }

  Future<MobileInferenceResult> processTensor(
    Float32List input, {
    LetterboxTransform? transform,
  }) async {
    if (_runtimeState != LocalRuntimeState.ready) {
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
    _lastDetections = selected;
    _lastInferenceDuration = result.inferenceDuration;

    final event = guidanceEngine.choose(selected);
    if (event != null) {
      await announce(
        standaloneStrings.guidanceMessage(event.detection.label, event.proximity),
        urgent: event.urgent,
      );
    }
    notifyListeners();
    return MobileInferenceResult(
      detections: selected,
      inferenceDuration: result.inferenceDuration,
    );
  }

  Future<void> announce(String message, {bool urgent = false}) async {
    if (_settings.vibrationEnabled) {
      if (urgent) {
        await feedbackService.urgent();
      } else {
        await feedbackService.medium();
      }
    }
    if (_settings.speechEnabled) {
      await speechService.speak(message);
    }
  }

  Future<void> stopFeedback() async {
    guidanceEngine.reset();
    await speechService.stop();
  }

  @override
  void dispose() {
    inferenceEngine.close();
    super.dispose();
  }
}
