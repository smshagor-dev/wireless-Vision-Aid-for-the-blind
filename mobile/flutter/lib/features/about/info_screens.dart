import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class PrivacyPolicyScreen extends StatelessWidget {
  const PrivacyPolicyScreen({super.key, required this.controller});
  final AppController controller;

  @override
  Widget build(BuildContext context) => const _InfoScaffold(
        title: 'Privacy Policy',
        children: [
          _Lead('WVAB Mobile v1.0.0 is designed as a local-first assistive vision application. This policy describes the data handled by the current mobile build.'),
          _Heading('Camera and visual processing'),
          _Body('When you start assistance, WVAB accesses the selected phone camera or locally paired ESP32-CAM. Phone-camera frames are processed on the Android device by the bundled ONNX object detector. WVAB does not intentionally upload phone-camera frames or detection results to a WVAB developer cloud service.'),
          _Heading('Information stored on this device'),
          _Body('WVAB stores your entered name, language and app preferences, selected detection classes, confidence setting, and recent detection-history events in the app’s local storage. Detection history contains object label, confidence, relative proximity/direction, camera source, and timestamp. It does not intentionally store camera photos or video frames.'),
          _Heading('ESP32-CAM credentials'),
          _Body('If you configure ESP32-CAM, its pairing key and authentication token are stored using Android secure-storage facilities. The app may use local-network/Internet permission for the ESP32 transport; this permission does not mean WVAB requires a cloud service.'),
          _Heading('Device services and permissions'),
          _Body('Camera permission is required for phone-camera assistance. Vibration is used for haptic feedback. Android text-to-speech is used for spoken guidance and may depend on voice packs installed on your device. Local-network communication is used only when you configure ESP32-CAM or another supported local endpoint.'),
          _Heading('Guidance estimates'),
          _Body('The mobile build estimates distance from a single camera view. Classes with a reasonably stable reference size may receive a coarse approximate meter estimate; other classes use broad visual range bands. WVAB also compares detected-object occupancy across the left, center, and right parts of the image. These values are estimates, not precision ranging or proof that a suggested walking surface is physically safe.'),
          _Heading('Analytics, advertising, and accounts'),
          _Body('The current WVAB mobile implementation does not include a WVAB account system, advertising SDK, or WVAB analytics/telemetry upload service.'),
          _Heading('Retention and deletion'),
          _Body('Detection history remains in local app storage until you clear it from the History screen, clear Android app storage, or uninstall WVAB. App preferences and your local profile are removed when Android app storage is cleared or the app is uninstalled. ESP32 credentials can be cleared from the connection/pairing controls.'),
          _Heading('Safety'),
          _Body('WVAB is an assistive prototype and is not a certified navigation, medical, emergency, or safety device. Object detection, distance estimation, and visual-clearance guidance can be wrong or incomplete; always use appropriate mobility and safety practices.'),
          _Heading('Contact'),
          _Body('Privacy questions: smshagor.dev@gmail.com\nWebsite: smshagor.com\nPhone: +79954949836'),
          _Heading('Policy version'),
          _Body('Effective for WVAB Mobile v1.0.0 — 26 August 2026.'),
        ],
      );
}

class OpenSourceLicensesScreen extends StatelessWidget {
  const OpenSourceLicensesScreen({super.key, required this.controller});
  final AppController controller;

  @override
  Widget build(BuildContext context) => _InfoScaffold(
        title: 'Open Source Licenses',
        children: const [
          _Lead('WVAB includes original project code and third-party packages, runtime libraries, fonts, and model assets. Third-party components remain subject to their own licenses.'),
          _Heading('WVAB source code'),
          _Body('Original WVAB repository code is provided under the MIT License. Copyright © 2026 Shahanur Islam.'),
          _Heading('Ultralytics YOLOv8 model asset'),
          _Body('The bundled YOLOv8n model is third-party material. The project’s third-party notice records Ultralytics open-source software/model licensing as AGPL-3.0 by default, with separate commercial/Enterprise licensing options. WVAB’s MIT license does not relicense that model or other third-party material.'),
          _Heading('ONNX Runtime'),
          _Body('WVAB uses ONNX Runtime on Android for local inference. ONNX Runtime is third-party software distributed under the MIT License.'),
          _Heading('Flutter packages and transitive dependencies'),
          _Body('Flutter, Dart packages, Android libraries, and their transitive dependencies keep their own upstream license terms. Use the button below to inspect the license registry included in this installed build.'),
        ],
        bottomBuilder: (context) => FilledButton.icon(
          key: const Key('flutter-license-page-button'),
          onPressed: () => showLicensePage(
            context: context,
            applicationName: 'WVAB',
            applicationVersion: '1.0.0',
            applicationLegalese: '© 2026 Shahanur Islam',
          ),
          icon: const Icon(Icons.description_outlined),
          label: const Text('Open package license registry'),
        ),
      );
}

class HowItWorksScreen extends StatelessWidget {
  const HowItWorksScreen({super.key, required this.controller});
  final AppController controller;

  @override
  Widget build(BuildContext context) => const _InfoScaffold(
        title: 'How It Works',
        children: [
          _Lead('WVAB turns camera frames into local object detections and focused spoken/haptic guidance without requiring a cloud inference server for phone-camera mode.'),
          _Step('1', 'Capture', 'Select the phone camera or a securely paired ESP32-CAM source.'),
          _Step('2', 'Prepare locally', 'WVAB converts the frame into the detector input format and letterboxes it to 320×320 while preserving coordinate mapping.'),
          _Step('3', 'Run local AI', 'The bundled YOLOv8n ONNX model runs on-device through ONNX Runtime. It supports the 80 COCO object classes included in this build.'),
          _Step('4', 'Estimate position and distance', 'WVAB locates each object as left, center, or right. For reference-size classes such as a person, car, chair, or bus it can provide a coarse approximate meter value. For other classes it reports broad visual bands: under about 1 m, about 1–2 m, about 2–4 m, or 4+ m.'),
          _Step('5', 'Choose one focus', 'Instead of reading every visible object, WVAB selects one current focus using range, visible size, corridor position, confidence, and focus stability. A genuinely closer new hazard can preempt the held focus.'),
          _Step('6', 'Suggest a clearer direction', 'WVAB compares detected-object occupancy on the left, center, and right and can suggest STOP, LEFT, RIGHT, or STRAIGHT. Guidance says a side appears clearer because the camera view alone cannot prove that the ground is traversable.'),
          _Step('7', 'Speak concise guidance', 'A typical instruction is: “Chair, about 1.5 meters away, left. Right side appears clearer. Keep right carefully.” Only the focused object is spoken at a time, and a speech lock prevents a stream of new non-urgent labels from cutting the sentence short.'),
          _Step('8', 'Store local history', 'Recent detected-object events are stored locally with timestamp, label, confidence, proximity, direction, and camera source. Other objects can still be recorded in history even while voice guidance stays focused on one object.'),
          _Heading('Detector scope'),
          _Body('The current local model recognizes the 80 COCO classes. Objects outside those classes—such as a custom pothole or curb class—require a compatible custom-trained model; the app must not invent labels the model was not trained to produce.'),
          _Heading('Distance and navigation limitation'),
          _Body('For genuinely calibrated metric distance, the system needs device-specific camera calibration or an additional depth source such as supported stereo/ToF/depth hardware. Current monocular distance and route hints should be treated as assistive estimates rather than guaranteed navigation commands.'),
        ],
      );
}

class ContactScreen extends StatelessWidget {
  const ContactScreen({super.key, required this.controller});
  final AppController controller;

  @override
  Widget build(BuildContext context) => const _InfoScaffold(
        title: 'Contact',
        children: [
          _Lead('WVAB project contact details'),
          _ContactRow(Icons.language_rounded, 'Website', 'smshagor.com'),
          _ContactRow(Icons.mail_outline_rounded, 'Email', 'smshagor.dev@gmail.com'),
          _ContactRow(Icons.phone_outlined, 'Mobile', '+79954949836'),
          _Heading('Support note'),
          _Body('When reporting a mobile detector issue, include the Android device model, Android version, whether phone camera or ESP32-CAM was used, and what happened immediately before the issue.'),
        ],
      );
}

class _InfoScaffold extends StatelessWidget {
  const _InfoScaffold({required this.title, required this.children, this.bottomBuilder});
  final String title;
  final List<Widget> children;
  final WidgetBuilder? bottomBuilder;

  @override
  Widget build(BuildContext context) {
    final items = <Widget>[...children];
    if (bottomBuilder != null) {
      items.add(const SizedBox(height: 8));
      items.add(bottomBuilder!(context));
    }
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ListView(
        padding: UiMetrics.lightPagePadding,
        children: items,
      ),
    );
  }
}

class _Lead extends StatelessWidget {
  const _Lead(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 18),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F5FF),
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          border: Border.all(color: const Color(0xFFDCE8FB)),
        ),
        child: SelectableText(text, style: const TextStyle(color: Color(0xFF465467), height: 1.45, fontSize: 15)),
      );
}

class _Heading extends StatelessWidget {
  const _Heading(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 12, bottom: 6),
        child: Text(text, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppTheme.text)),
      );
}

class _Body extends StatelessWidget {
  const _Body(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => SelectableText(
        text,
        style: const TextStyle(fontSize: 15, color: Color(0xFF526070), height: 1.5),
      );
}

class _Step extends StatelessWidget {
  const _Step(this.number, this.title, this.body);
  final String number;
  final String title;
  final String body;
  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          border: Border.all(color: AppTheme.border),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(backgroundColor: AppTheme.blue, foregroundColor: Colors.white, child: Text(number)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 4),
                  Text(body, style: const TextStyle(color: AppTheme.muted, height: 1.4)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ContactRow extends StatelessWidget {
  const _ContactRow(this.icon, this.label, this.value);
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          border: Border.all(color: AppTheme.border),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.blue),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 2),
                  SelectableText(value, style: const TextStyle(color: AppTheme.muted, fontSize: 15)),
                ],
              ),
            ),
          ],
        ),
      );
}
