import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'app.dart';
import 'core/controllers/app_controller.dart';
import 'core/services/detection_history_store.dart';
import 'core/services/esp32_credentials_store.dart';
import 'core/services/feedback_service.dart';
import 'core/services/settings_store.dart';
import 'core/services/speech_service.dart';
import 'core/vision/mobile_inference_engine.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  _registerWvabLicenses();

  final controller = AppController(
    speechService: FlutterTtsSpeechService(),
    feedbackService: FlutterHapticFeedbackService(),
    settingsStore: SharedPreferencesSettingsStore(),
    historyStore: SharedPreferencesDetectionHistoryStore(),
    credentialsStore: SecureEsp32CredentialsStore(),
    inferenceEngine: OnnxMobileInferenceEngine(),
  );
  await controller.initialize();

  runApp(WvabMobileApp(controller: controller));
}

void _registerWvabLicenses() {
  LicenseRegistry.addLicense(() async* {
    yield const LicenseEntryWithLineBreaks(
      <String>['WVAB'],
      'MIT License\n\nCopyright (c) 2026 Shahanur Islam\n\n'
      'Permission is hereby granted, free of charge, to any person obtaining a copy '
      'of this software and associated documentation files (the "Software"), to deal '
      'in the Software without restriction, including without limitation the rights '
      'to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies '
      'of the Software, subject to inclusion of this copyright and permission notice.\n\n'
      'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.',
    );
    yield const LicenseEntryWithLineBreaks(
      <String>['Ultralytics YOLOv8 model asset'],
      'WVAB bundles a YOLOv8n model asset as third-party material. Ultralytics open-source '
      'software and model licensing is governed by its own upstream terms (AGPL-3.0 by '
      'default, with separate commercial/Enterprise licensing options). The WVAB MIT '
      'license does not relicense third-party model assets.',
    );
    yield const LicenseEntryWithLineBreaks(
      <String>['ONNX Runtime'],
      'ONNX Runtime is third-party software distributed under the MIT License. '
      'The Android runtime is bundled for local on-device inference.',
    );
  });
}
