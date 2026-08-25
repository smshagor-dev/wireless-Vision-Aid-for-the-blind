import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/app.dart';
import 'package:wvab_mobile/core/controllers/app_controller.dart';
import 'package:wvab_mobile/core/models/app_settings.dart';
import 'package:wvab_mobile/core/services/esp32_credentials_store.dart';
import 'package:wvab_mobile/core/services/feedback_service.dart';
import 'package:wvab_mobile/core/services/settings_store.dart';
import 'package:wvab_mobile/core/services/speech_service.dart';
import 'package:wvab_mobile/core/theme/ui_metrics.dart';
import 'package:wvab_mobile/core/vision/mobile_inference_engine.dart';

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

class _FakeInferenceEngine implements InferenceEngine {
  bool _ready = false;

  @override
  bool get isReady => _ready;

  @override
  Future<void> initialize() async => _ready = true;

  @override
  Future<MobileInferenceResult> run(
    Float32List nchwInput, {
    required double confidenceThreshold,
  }) async {
    return const MobileInferenceResult(
      detections: [],
      inferenceDuration: Duration(milliseconds: 1),
    );
  }

  @override
  Future<void> close() async => _ready = false;
}

AppController _controller({bool onboarded = true}) {
  return AppController(
    speechService: _FakeSpeechService(),
    feedbackService: _FakeFeedbackService(),
    settingsStore: MemorySettingsStore(AppSettings(firstRunCompleted: onboarded)),
    credentialsStore: MemoryEsp32CredentialsStore(),
    inferenceEngine: _FakeInferenceEngine(),
  );
}

void main() {
  testWidgets('first launch completes local onboarding without a backend', (tester) async {
    final controller = _controller(onboarded: false);
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));
    expect(find.byKey(const Key('onboarding-phone-camera')), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const Key('onboarding-finish')),
      300,
    );
    await tester.tap(find.byKey(const Key('onboarding-finish')));
    await tester.pumpAndSettle();

    expect(controller.settings.firstRunCompleted, isTrue);
    expect(controller.settings.cameraSource, CameraSourceType.phone);
    expect(find.byKey(const Key('start-assistance-button')), findsOneWidget);
  });

  testWidgets('home matches approved assistance-first proportions', (tester) async {
    final controller = _controller();
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));

    expect(find.text('WVAB'), findsOneWidget);
    expect(find.byKey(const Key('start-assistance-button')), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('History'), findsOneWidget);
    expect(find.text('Phone camera'), findsOneWidget);

    final circleSize = tester.getSize(find.byKey(const Key('home-start-circle')));
    expect(circleSize.width, UiMetrics.homeActionDiameter);
    expect(circleSize.height, UiMetrics.homeActionDiameter);
    expect(tester.getSize(find.byKey(const Key('home-settings-tile'))).height, UiMetrics.homeTileHeight);
    expect(tester.getSize(find.byKey(const Key('home-history-tile'))).height, UiMetrics.homeTileHeight);
  });

  testWidgets('home remains overflow-free on compact phone viewport', (tester) async {
    await tester.binding.setSurfaceSize(const Size(360, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final controller = _controller();
    await controller.initialize();
    await tester.pumpWidget(WvabMobileApp(controller: controller));

    expect(find.byKey(const Key('home-start-circle')), findsOneWidget);
    expect(find.byKey(const Key('home-status-bar')), findsOneWidget);
    expect(tester.takeException(), isNull);
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
    expect(find.text('ফোন ক্যামেরা'), findsOneWidget);
  });

  testWidgets('settings keeps the fixed bottom navigation and save action', (tester) async {
    final controller = _controller();
    await controller.initialize();

    await tester.pumpWidget(WvabMobileApp(controller: controller));
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    final settingsList = find.byKey(const Key('settings-list'));
    expect(settingsList, findsOneWidget);
    expect(
      tester.getSize(find.byKey(const Key('settings-bottom-nav'))).height,
      UiMetrics.settingsBottomBarHeight,
    );

    await tester.scrollUntilVisible(
      find.byKey(const Key('settings-save-button')),
      300,
      scrollable: find.descendant(
        of: settingsList,
        matching: find.byType(Scrollable),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('settings-save-button')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
