import 'package:flutter/material.dart' show Key;
import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/app.dart';
import 'package:wvab_mobile/core/controllers/app_controller.dart';
import 'package:wvab_mobile/core/services/edge_connection_service.dart';
import 'package:wvab_mobile/core/services/feedback_service.dart';
import 'package:wvab_mobile/core/services/speech_service.dart';

class _FakeSpeechService implements SpeechService {
  final spoken = <String>[];

  @override
  Future<void> initialize(String languageCode) async {}

  @override
  Future<void> setLanguage(String languageCode) async {}

  @override
  Future<void> speak(String message) async => spoken.add(message);

  @override
  Future<void> stop() async {}
}

class _FakeFeedbackService implements FeedbackService {
  int mediumCount = 0;

  @override
  Future<void> light() async {}

  @override
  Future<void> medium() async => mediumCount++;

  @override
  Future<void> urgent() async {}
}

void main() {
  testWidgets('home exposes accessible start control and honest transport state', (tester) async {
    final speech = _FakeSpeechService();
    final feedback = _FakeFeedbackService();
    final controller = AppController(
      speechService: speech,
      feedbackService: feedback,
      edgeConnectionService: EdgeConnectionService(),
    );
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));

    expect(find.text('WVAB Mobile'), findsOneWidget);
    expect(find.byKey(const Key('start-assistance-button')), findsOneWidget);
    expect(find.textContaining('transport not connected yet'), findsOneWidget);
    expect(find.textContaining('Protocol v2 integration pending'), findsOneWidget);
  });

  testWidgets('feedback test uses speech and vibration services', (tester) async {
    final speech = _FakeSpeechService();
    final feedback = _FakeFeedbackService();
    final controller = AppController(
      speechService: speech,
      feedbackService: feedback,
      edgeConnectionService: EdgeConnectionService(),
    );
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));
    await tester.tap(find.text('Test voice and vibration'));
    await tester.pump();

    expect(speech.spoken, contains('WVAB Mobile feedback test'));
    expect(feedback.mediumCount, 1);
  });
}
