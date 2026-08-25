import 'package:flutter/material.dart';

import 'app.dart';
import 'core/controllers/app_controller.dart';
import 'core/services/esp32_credentials_store.dart';
import 'core/services/feedback_service.dart';
import 'core/services/settings_store.dart';
import 'core/services/speech_service.dart';
import 'core/vision/mobile_inference_engine.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final controller = AppController(
    speechService: FlutterTtsSpeechService(),
    feedbackService: FlutterHapticFeedbackService(),
    settingsStore: SharedPreferencesSettingsStore(),
    credentialsStore: SecureEsp32CredentialsStore(),
    inferenceEngine: OnnxMobileInferenceEngine(),
  );
  await controller.initialize();

  runApp(WvabMobileApp(controller: controller));
}
