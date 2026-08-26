import 'package:flutter_tts/flutter_tts.dart';

abstract interface class SpeechService {
  Future<void> initialize(String languageCode);
  Future<void> setLanguage(String languageCode);
  Future<void> speak(String message);
  Future<void> stop();
}

class FlutterTtsSpeechService implements SpeechService {
  FlutterTtsSpeechService({FlutterTts? engine}) : _engine = engine ?? FlutterTts();

  final FlutterTts _engine;
  static const _fallbackLanguage = 'en-US';

  @override
  Future<void> initialize(String languageCode) async {
    await _engine.awaitSpeakCompletion(true);
    await _engine.setSpeechRate(0.45);
    await _engine.setVolume(1.0);
    await _engine.setPitch(1.0);
    await setLanguage(languageCode);
  }

  @override
  Future<void> setLanguage(String languageCode) async {
    final requestedAvailable = await _engine.isLanguageAvailable(languageCode);
    if (requestedAvailable == true) {
      await _engine.setLanguage(languageCode);
      return;
    }

    // Some Android devices do not have the selected voice pack installed.
    // Keep guidance audible instead of silently accepting an unavailable
    // language. English is the deterministic offline fallback used by WVAB.
    final fallbackAvailable = await _engine.isLanguageAvailable(_fallbackLanguage);
    if (fallbackAvailable == true) {
      await _engine.setLanguage(_fallbackLanguage);
      return;
    }

    // Let the platform report a meaningful error when no queried language is
    // advertised instead of silently pretending TTS is ready.
    await _engine.setLanguage(languageCode);
  }

  @override
  Future<void> speak(String message) async {
    if (message.trim().isEmpty) return;
    await _engine.stop();
    await _engine.setVolume(1.0);
    await _engine.speak(message);
  }

  @override
  Future<void> stop() async {
    await _engine.stop();
  }
}
