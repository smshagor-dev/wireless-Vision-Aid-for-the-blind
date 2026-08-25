import 'package:flutter/services.dart';

abstract interface class FeedbackService {
  Future<void> light();
  Future<void> medium();
  Future<void> urgent();
}

class FlutterHapticFeedbackService implements FeedbackService {
  @override
  Future<void> light() => HapticFeedback.lightImpact();

  @override
  Future<void> medium() => HapticFeedback.mediumImpact();

  @override
  Future<void> urgent() => HapticFeedback.heavyImpact();
}
