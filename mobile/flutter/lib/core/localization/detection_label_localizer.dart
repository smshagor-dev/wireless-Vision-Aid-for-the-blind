import 'dart:convert';

import 'package:flutter/services.dart';

import '../vision/detection.dart';

class DetectionLabelLocalizer {
  DetectionLabelLocalizer({this.assetPath = 'assets/i18n/multilingual_labels.common.json'});

  final String assetPath;
  Map<String, dynamic> _data = const {};

  Future<void> initialize() async {
    final raw = await rootBundle.loadString(assetPath);
    _data = jsonDecode(raw) as Map<String, dynamic>;
  }

  String objectLabel(String label, String languageCode) {
    final language = _language(languageCode);
    final entry = _data[label];
    if (entry is Map<String, dynamic>) {
      final translated = entry[language] ?? entry['en'];
      if (translated is String && translated.trim().isNotEmpty) return translated;
    }
    return _titleCase(label);
  }

  String guidanceMessage(
    String label,
    ProximityBand proximity,
    SpatialDirection direction,
    String languageCode,
  ) {
    final language = _language(languageCode);
    final object = objectLabel(label, languageCode);
    final proximityText = _phrase(
      switch (proximity) {
        ProximityBand.immediate => 'very close',
        ProximityBand.close => 'close',
        ProximityBand.medium => 'in front',
        ProximityBand.far => 'too far',
      },
      language,
    );
    final directionText = _phrase(
      switch (direction) {
        SpatialDirection.left => 'left',
        SpatialDirection.center => 'in front',
        SpatialDirection.right => 'right',
      },
      language,
    );
    return '$object, $proximityText, $directionText';
  }

  String welcomeMessage(String userName, String languageCode) {
    final normalized = userName.trim();
    return switch (_language(languageCode)) {
      'bn' => 'স্বাগতম মিস্টার $normalized',
      'ru' => 'Добро пожаловать, мистер $normalized',
      'hi' => 'स्वागत है मिस्टर $normalized',
      'es' => 'Bienvenido, señor $normalized',
      'fr' => 'Bienvenue, Monsieur $normalized',
      'ar' => 'مرحباً السيد $normalized',
      _ => 'Welcome Mr. $normalized',
    };
  }

  String _phrase(String key, String language) {
    final phrases = _data['__phrases__'];
    if (phrases is Map<String, dynamic>) {
      final requested = phrases[language];
      if (requested is Map<String, dynamic>) {
        final translated = requested[key];
        if (translated is String && translated.trim().isNotEmpty) return translated;
      }
      final english = phrases['en'];
      if (english is Map<String, dynamic>) {
        final fallback = english[key];
        if (fallback is String && fallback.trim().isNotEmpty) return fallback;
      }
    }
    return key;
  }

  String _language(String languageCode) {
    final value = languageCode.split('-').first.toLowerCase();
    return const {'en', 'ru', 'bn', 'hi', 'es', 'fr', 'ar'}.contains(value) ? value : 'en';
  }

  String _titleCase(String value) => value
      .split(' ')
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
}
