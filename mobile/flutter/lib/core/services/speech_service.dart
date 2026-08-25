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
    await _engine.setLanguage(languageCode);
  }

  @override
  Future<void> speak(String message) async {
    if (message.trim().isEmpty) return;
    await _engine.stop();
    await _engine.speak(message);
  }

  @override
  Future<void> stop() async {
    await _engine.stop();
  }
}
