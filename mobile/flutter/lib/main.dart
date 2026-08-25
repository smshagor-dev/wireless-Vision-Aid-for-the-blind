import 'package:flutter/material.dart';

import 'app.dart';
import 'core/controllers/app_controller.dart';
import 'core/services/edge_connection_service.dart';
import 'core/services/feedback_service.dart';
import 'core/services/speech_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final controller = AppController(
    speechService: FlutterTtsSpeechService(),
    feedbackService: FlutterHapticFeedbackService(),
    edgeConnectionService: EdgeConnectionService(),
  );
  await controller.initialize();

  runApp(WvabMobileApp(controller: controller));
}
