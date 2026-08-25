import 'package:flutter/foundation.dart';

import '../localization/app_strings.dart';
import '../models/app_settings.dart';
import '../services/edge_connection_service.dart';
import '../services/feedback_service.dart';
import '../services/speech_service.dart';

class AppController extends ChangeNotifier {
  AppController({
    required this.speechService,
    required this.feedbackService,
    required this.edgeConnectionService,
  });

  final SpeechService speechService;
  final FeedbackService feedbackService;
  final EdgeConnectionService edgeConnectionService;

  AppSettings _settings = const AppSettings();

  AppSettings get settings => _settings;
  AppStrings get strings => AppStrings(_settings.languageCode);
  EdgeEndpoint? get edgeEndpoint => edgeConnectionService.endpoint;
  EdgeConfigurationState get edgeState => edgeConnectionService.state;

  Future<void> initialize() async {
    edgeConnectionService.configure(
      host: _settings.edgeHost,
      port: _settings.edgePort,
    );
    await speechService.initialize(_settings.languageCode);
  }

  Future<void> updateSettings(AppSettings settings) async {
    edgeConnectionService.configure(
      host: settings.edgeHost,
      port: settings.edgePort,
    );
    _settings = settings;
    await speechService.setLanguage(settings.languageCode);
    notifyListeners();
  }

  Future<void> setLanguage(String languageCode) async {
    if (!AppStrings.supportedLanguages.containsKey(languageCode)) return;
    await updateSettings(_settings.copyWith(languageCode: languageCode));
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

  Future<void> stopFeedback() => speechService.stop();
}
