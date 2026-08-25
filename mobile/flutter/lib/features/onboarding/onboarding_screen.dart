import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/standalone_strings.dart';
import '../../core/models/app_settings.dart';
import '../../core/services/esp32_credentials_store.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  late String _languageCode;
  late CameraSourceType _cameraSource;
  late final TextEditingController _portController;
  final _keyController = TextEditingController();
  final _tokenController = TextEditingController();
  bool _saving = false;

  StandaloneStrings get _strings => StandaloneStrings(_languageCode);

  @override
  void initState() {
    super.initState();
    _languageCode = widget.controller.settings.languageCode;
    _cameraSource = widget.controller.settings.cameraSource;
    _portController = TextEditingController(text: widget.controller.settings.esp32ListenPort.toString());
  }

  @override
  void dispose() {
    _portController.dispose();
    _keyController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _finish() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      var settings = widget.controller.settings.copyWith(
        languageCode: _languageCode,
        cameraSource: _cameraSource,
      );
      if (_cameraSource == CameraSourceType.esp32) {
        final port = int.tryParse(_portController.text.trim());
        if (port == null || port < 1 || port > 65535) {
          throw const FormatException('ESP32 UDP port must be in 1..65535.');
        }
        final credentials = Esp32Credentials(
          keyHex: _keyController.text,
          token: _tokenController.text,
        );
        if (!credentials.isConfigured) {
          throw FormatException(_strings.get('pairingRequired'));
        }
        await widget.controller.saveEsp32Credentials(credentials);
        settings = settings.copyWith(esp32ListenPort: port);
      }
      await widget.controller.updateSettings(settings);
      await widget.controller.completeOnboarding(
        languageCode: _languageCode,
        cameraSource: _cameraSource,
      );
    } on FormatException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = _strings;
    return Scaffold(
      backgroundColor: AppTheme.page,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(22, 28, 22, 24),
          children: [
            Center(
              child: Container(
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  gradient: AppTheme.homeTileGradient,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: const [BoxShadow(color: Color(0x241976D2), blurRadius: 18, offset: Offset(0, 8))],
                ),
                child: const Icon(Icons.visibility_rounded, color: Colors.white, size: 48),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              strings.get('welcome'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w900, color: AppTheme.text),
            ),
            const SizedBox(height: 10),
            Text(
              strings.get('welcomeBody'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16, height: 1.45, color: AppTheme.muted),
            ),
            const SizedBox(height: 28),
            _SectionTitle(strings.get('chooseLanguage')),
            const SizedBox(height: 10),
            _Card(
              child: Column(
                children: AppStrings.supportedLanguages.entries.map((entry) {
                  return RadioListTile<String>(
                    key: Key('onboarding-language-${entry.key}'),
                    value: entry.key,
                    groupValue: _languageCode,
                    activeColor: AppTheme.blue,
                    title: Text(entry.value, style: const TextStyle(fontWeight: FontWeight.w700)),
                    onChanged: (value) {
                      if (value != null) setState(() => _languageCode = value);
                    },
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 24),
            _SectionTitle(strings.get('chooseCamera')),
            const SizedBox(height: 10),
            _CameraChoice(
              key: const Key('onboarding-phone-camera'),
              icon: Icons.smartphone_rounded,
              title: strings.get('phoneCamera'),
              body: strings.get('phoneCameraBody'),
              selected: _cameraSource == CameraSourceType.phone,
              onTap: () => setState(() => _cameraSource = CameraSourceType.phone),
            ),
            const SizedBox(height: 12),
            _CameraChoice(
              key: const Key('onboarding-esp32-camera'),
              icon: Icons.wifi_tethering_rounded,
              title: strings.get('esp32Camera'),
              body: strings.get('esp32CameraBody'),
              selected: _cameraSource == CameraSourceType.esp32,
              onTap: () => setState(() => _cameraSource = CameraSourceType.esp32),
            ),
            if (_cameraSource == CameraSourceType.esp32) ...[
              const SizedBox(height: 16),
              _Card(
                child: Column(
                  children: [
                    TextField(
                      key: const Key('onboarding-esp32-port'),
                      controller: _portController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(labelText: strings.get('esp32Port')),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      key: const Key('onboarding-esp32-key'),
                      controller: _keyController,
                      autocorrect: false,
                      enableSuggestions: false,
                      decoration: InputDecoration(labelText: strings.get('aesKey')),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      key: const Key('onboarding-esp32-token'),
                      controller: _tokenController,
                      obscureText: true,
                      autocorrect: false,
                      enableSuggestions: false,
                      decoration: InputDecoration(labelText: strings.get('authToken')),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 28),
            FilledButton.icon(
              key: const Key('onboarding-finish'),
              onPressed: _saving ? null : _finish,
              icon: _saving
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.check_circle_outline_rounded),
              label: Text(strings.get('finishSetup')),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 16),
      );
}

class _Card extends StatelessWidget {
  const _Card({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          side: const BorderSide(color: AppTheme.border),
        ),
        clipBehavior: Clip.antiAlias,
        child: child,
      );
}

class _CameraChoice extends StatelessWidget {
  const _CameraChoice({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String body;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected ? const Color(0xFFF0F6FF) : Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          side: BorderSide(color: selected ? AppTheme.blue : AppTheme.border, width: selected ? 2 : 1),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: selected ? AppTheme.blue : const Color(0xFFEAF3FF),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: selected ? Colors.white : AppTheme.blue, size: 27),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
                      const SizedBox(height: 4),
                      Text(body, style: const TextStyle(color: AppTheme.muted, height: 1.35)),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(selected ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                    color: selected ? AppTheme.blue : AppTheme.muted),
              ],
            ),
          ),
        ),
      );
}
