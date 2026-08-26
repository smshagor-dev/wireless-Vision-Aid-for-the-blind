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
    final distanceText = event.approximateDistanceMeters == null
        ? _rangePhrase(event.proximity, language)
        : _distancePhrase(event.approximateDistanceMeters!, language);
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
      'bn' => 'আনুমানিক $value মিটার দূরে',
      'ru' => 'примерно $value м',
      'hi' => 'लगभग $value मीटर दूर',
      'es' => 'a unos $value metros',
      'fr' => 'à environ $value mètres',
      'ar' => 'على بعد حوالي $value متر',
      _ => 'about $value meters away',
    };
  }

  String _rangePhrase(ProximityBand proximity, String language) {
    return switch (language) {
      'bn' => switch (proximity) {
          ProximityBand.immediate => 'আনুমানিক ১ মিটারের কম দূরে',
          ProximityBand.close => 'আনুমানিক ১ থেকে ২ মিটার দূরে',
          ProximityBand.medium => 'আনুমানিক ২ থেকে ৪ মিটার দূরে',
          ProximityBand.far => 'আনুমানিক ৪ মিটারের বেশি দূরে',
        },
      'ru' => switch (proximity) {
          ProximityBand.immediate => 'примерно ближе одного метра',
          ProximityBand.close => 'примерно в одном-двух метрах',
          ProximityBand.medium => 'примерно в двух-четырёх метрах',
          ProximityBand.far => 'примерно дальше четырёх метров',
        },
      'hi' => switch (proximity) {
          ProximityBand.immediate => 'लगभग एक मीटर से कम दूर',
          ProximityBand.close => 'लगभग एक से दो मीटर दूर',
          ProximityBand.medium => 'लगभग दो से चार मीटर दूर',
          ProximityBand.far => 'लगभग चार मीटर से अधिक दूर',
        },
      'es' => switch (proximity) {
          ProximityBand.immediate => 'a menos de un metro aproximadamente',
          ProximityBand.close => 'a uno o dos metros aproximadamente',
          ProximityBand.medium => 'a dos o cuatro metros aproximadamente',
          ProximityBand.far => 'a más de cuatro metros aproximadamente',
        },
      'fr' => switch (proximity) {
          ProximityBand.immediate => 'à moins d’un mètre environ',
          ProximityBand.close => 'à environ un à deux mètres',
          ProximityBand.medium => 'à environ deux à quatre mètres',
          ProximityBand.far => 'à plus de quatre mètres environ',
        },
      'ar' => switch (proximity) {
          ProximityBand.immediate => 'على بعد أقل من متر تقريبًا',
          ProximityBand.close => 'على بعد متر إلى مترين تقريبًا',
          ProximityBand.medium => 'على بعد مترين إلى أربعة أمتار تقريبًا',
          ProximityBand.far => 'على بعد أكثر من أربعة أمتار تقريبًا',
        },
      _ => switch (proximity) {
          ProximityBand.immediate => 'estimated under 1 meter away',
          ProximityBand.close => 'estimated 1 to 2 meters away',
          ProximityBand.medium => 'estimated 2 to 4 meters away',
          ProximityBand.far => 'estimated more than 4 meters away',
        },
    };
  }

  String _navigationPhrase(NavigationCue cue, String language) {
    return switch ((language, cue)) {
      ('bn', NavigationCue.moveLeft) => 'বাম দিক তুলনামূলক ফাঁকা মনে হচ্ছে, সতর্কভাবে বাম দিকে থাকুন',
      ('bn', NavigationCue.moveRight) => 'ডান দিক তুলনামূলক ফাঁকা মনে হচ্ছে, সতর্কভাবে ডান দিকে থাকুন',
      ('bn', NavigationCue.forward) => 'সামনের পথ তুলনামূলক ফাঁকা মনে হচ্ছে, সতর্কভাবে সোজা থাকুন',
      ('bn', NavigationCue.stop) => 'থামুন, সামনে পথ বাধাগ্রস্ত মনে হচ্ছে',
      ('ru', NavigationCue.moveLeft) => 'Слева выглядит свободнее, осторожно держитесь левее',
      ('ru', NavigationCue.moveRight) => 'Справа выглядит свободнее, осторожно держитесь правее',
      ('ru', NavigationCue.forward) => 'Впереди выглядит свободнее, двигайтесь осторожно прямо',
      ('ru', NavigationCue.stop) => 'Остановитесь, путь впереди выглядит перекрытым',
      ('hi', NavigationCue.moveLeft) => 'बाईं ओर रास्ता अधिक साफ दिख रहा है, सावधानी से बाईं ओर रहें',
      ('hi', NavigationCue.moveRight) => 'दाईं ओर रास्ता अधिक साफ दिख रहा है, सावधानी से दाईं ओर रहें',
      ('hi', NavigationCue.forward) => 'आगे रास्ता अधिक साफ दिख रहा है, सावधानी से सीधे रहें',
      ('hi', NavigationCue.stop) => 'रुकें, आगे रास्ता अवरुद्ध दिख रहा है',
      ('es', NavigationCue.moveLeft) => 'La izquierda parece más despejada; manténgase a la izquierda con cuidado',
      ('es', NavigationCue.moveRight) => 'La derecha parece más despejada; manténgase a la derecha con cuidado',
      ('es', NavigationCue.forward) => 'El camino de frente parece más despejado; siga recto con cuidado',
      ('es', NavigationCue.stop) => 'Deténgase; el camino de frente parece bloqueado',
      ('fr', NavigationCue.moveLeft) => 'La gauche semble plus dégagée; restez prudemment à gauche',
      ('fr', NavigationCue.moveRight) => 'La droite semble plus dégagée; restez prudemment à droite',
      ('fr', NavigationCue.forward) => 'Le passage devant semble plus dégagé; restez prudemment tout droit',
      ('fr', NavigationCue.stop) => 'Arrêtez-vous; le passage devant semble bloqué',
      ('ar', NavigationCue.moveLeft) => 'الجهة اليسرى تبدو أوضح، ابقَ يسارًا بحذر',
      ('ar', NavigationCue.moveRight) => 'الجهة اليمنى تبدو أوضح، ابقَ يمينًا بحذر',
      ('ar', NavigationCue.forward) => 'المسار أمامك يبدو أوضح، تابع بحذر إلى الأمام',
      ('ar', NavigationCue.stop) => 'توقف، يبدو أن المسار أمامك مسدود',
      (_, NavigationCue.moveLeft) => 'Left side appears clearer. Keep left carefully',
      (_, NavigationCue.moveRight) => 'Right side appears clearer. Keep right carefully',
      (_, NavigationCue.forward) => 'Path ahead appears clearer. Continue straight carefully',
      (_, NavigationCue.stop) => 'Stop. The path ahead appears blocked',
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
