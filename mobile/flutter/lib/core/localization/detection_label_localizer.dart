import 'dart:convert';

import 'package:flutter/services.dart';

import '../vision/detection.dart';
import '../vision/guidance_engine.dart';

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

  String focusedGuidanceMessage(GuidanceEvent event, String languageCode) {
    final language = _language(languageCode);
    final object = objectLabel(event.detection.label, languageCode);
    final directionText = _phrase(
      switch (event.direction) {
        SpatialDirection.left => 'left',
        SpatialDirection.center => 'in front',
        SpatialDirection.right => 'right',
      },
      language,
    );
    final distance = event.approximateDistanceMeters;
    final distanceText = distance == null
        ? _phrase(
            switch (event.proximity) {
              ProximityBand.immediate => 'very close',
              ProximityBand.close => 'close',
              ProximityBand.medium => 'in front',
              ProximityBand.far => 'too far',
            },
            language,
          )
        : _distancePhrase(distance, language);
    final navigation = _navigationPhrase(event.navigationCue, language);
    return switch (language) {
      'bn' => '$object $directionText, $distanceText। $navigation',
      'ru' => '$object $directionText, $distanceText. $navigation',
      'hi' => '$object $directionText, $distanceText। $navigation',
      'es' => '$object, $directionText, $distanceText. $navigation',
      'fr' => '$object, $directionText, $distanceText. $navigation',
      'ar' => '$object $directionText، $distanceText. $navigation',
      _ => '$object, $directionText, $distanceText. $navigation',
    };
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

  String _distancePhrase(double meters, String language) {
    final rounded = meters < 3 ? (meters * 2).round() / 2 : meters.roundToDouble();
    final value = rounded == rounded.roundToDouble()
        ? rounded.toInt().toString()
        : rounded.toStringAsFixed(1);
    return switch (language) {
      'bn' => 'প্রায় $value মিটার দূরে',
      'ru' => 'примерно $value м',
      'hi' => 'लगभग $value मीटर दूर',
      'es' => 'a unos $value metros',
      'fr' => 'à environ $value mètres',
      'ar' => 'على بعد حوالي $value متر',
      _ => 'about $value meters away',
    };
  }

  String _navigationPhrase(NavigationCue cue, String language) {
    return switch ((language, cue)) {
      ('bn', NavigationCue.moveLeft) => 'বাম দিক তুলনামূলক ফাঁকা, বামে যান',
      ('bn', NavigationCue.moveRight) => 'ডান দিক তুলনামূলক ফাঁকা, ডানে যান',
      ('bn', NavigationCue.forward) => 'সামনের পথ তুলনামূলক পরিষ্কার',
      ('bn', NavigationCue.stop) => 'থামুন, সামনে পথ বন্ধ',
      ('ru', NavigationCue.moveLeft) => 'Слева свободнее, двигайтесь влево',
      ('ru', NavigationCue.moveRight) => 'Справа свободнее, двигайтесь вправо',
      ('ru', NavigationCue.forward) => 'Впереди выглядит свободнее',
      ('ru', NavigationCue.stop) => 'Стоп, путь впереди перекрыт',
      ('hi', NavigationCue.moveLeft) => 'बाईं तरफ अधिक खाली है, बाएं जाएं',
      ('hi', NavigationCue.moveRight) => 'दाईं तरफ अधिक खाली है, दाएं जाएं',
      ('hi', NavigationCue.forward) => 'आगे का रास्ता अपेक्षाकृत साफ है',
      ('hi', NavigationCue.stop) => 'रुकें, आगे रास्ता अवरुद्ध है',
      ('es', NavigationCue.moveLeft) => 'La izquierda parece más libre, muévase a la izquierda',
      ('es', NavigationCue.moveRight) => 'La derecha parece más libre, muévase a la derecha',
      ('es', NavigationCue.forward) => 'El camino al frente parece más despejado',
      ('es', NavigationCue.stop) => 'Deténgase, el camino al frente está bloqueado',
      ('fr', NavigationCue.moveLeft) => 'La gauche semble plus libre, allez à gauche',
      ('fr', NavigationCue.moveRight) => 'La droite semble plus libre, allez à droite',
      ('fr', NavigationCue.forward) => 'Le passage devant semble plus dégagé',
      ('fr', NavigationCue.stop) => 'Arrêtez-vous, le passage devant est bloqué',
      ('ar', NavigationCue.moveLeft) => 'الجهة اليسرى تبدو أوضح، تحرك يساراً',
      ('ar', NavigationCue.moveRight) => 'الجهة اليمنى تبدو أوضح، تحرك يميناً',
      ('ar', NavigationCue.forward) => 'المسار أمامك يبدو أوضح',
      ('ar', NavigationCue.stop) => 'توقف، المسار أمامك مسدود',
      (_, NavigationCue.moveLeft) => 'Left side looks clearer. Move left',
      (_, NavigationCue.moveRight) => 'Right side looks clearer. Move right',
      (_, NavigationCue.forward) => 'Path ahead looks clearer',
      (_, NavigationCue.stop) => 'Stop. Path ahead is blocked',
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
