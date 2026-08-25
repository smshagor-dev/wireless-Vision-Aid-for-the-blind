import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/app.dart';
import 'package:wvab_mobile/core/controllers/app_controller.dart';
import 'package:wvab_mobile/core/services/edge_connection_service.dart';
import 'package:wvab_mobile/core/services/feedback_service.dart';
import 'package:wvab_mobile/core/services/speech_service.dart';

class _FakeSpeechService implements SpeechService {
  @override
  Future<void> initialize(String languageCode) async {}

  @override
  Future<void> setLanguage(String languageCode) async {}

  @override
  Future<void> speak(String message) async {}

  @override
  Future<void> stop() async {}
}

class _FakeFeedbackService implements FeedbackService {
  @override
  Future<void> light() async {}

  @override
  Future<void> medium() async {}

  @override
  Future<void> urgent() async {}
}

AppController _controller() {
  return AppController(
    speechService: _FakeSpeechService(),
    feedbackService: _FakeFeedbackService(),
    edgeConnectionService: EdgeConnectionService(),
  );
}

void main() {
  testWidgets('home matches assistance-first layout and honest connection state', (tester) async {
    final controller = _controller();
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));

    expect(find.text('WVAB'), findsOneWidget);
    expect(find.byKey(const Key('start-assistance-button')), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('History'), findsOneWidget);
    expect(find.text('Not Connected'), findsOneWidget);
  });

  testWidgets('language selection changes the whole app interface', (tester) async {
    final controller = _controller();
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));
    await tester.tap(find.byKey(const Key('language-button')));
    await tester.pumpAndSettle();

    expect(find.text('Language'), findsOneWidget);
    await tester.tap(find.byKey(const Key('language-bn-BD')));
    await tester.pumpAndSettle();

    expect(controller.settings.languageCode, 'bn-BD');
    expect(find.text('সেটিংস'), findsOneWidget);
    expect(find.text('ইতিহাস'), findsOneWidget);
    expect(find.text('সংযুক্ত নয়'), findsOneWidget);
  });
}
