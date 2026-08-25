import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/models/app_settings.dart';
import '../../core/services/esp32_credentials_store.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  late CameraSourceType _source;
  late final TextEditingController _portController;
  final _keyController = TextEditingController();
  final _tokenController = TextEditingController();
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _source = widget.controller.settings.cameraSource;
    _portController = TextEditingController(text: widget.controller.settings.esp32ListenPort.toString());
  }

  @override
  void dispose() {
    _portController.dispose();
    _keyController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() => _saving = true);
    final s = widget.controller.standaloneStrings;
    try {
      var settings = widget.controller.settings.copyWith(cameraSource: _source);
      if (_source == CameraSourceType.esp32) {
        final port = int.tryParse(_portController.text.trim());
        if (port == null || port < 1 || port > 65535) {
          throw const FormatException('ESP32 UDP port must be in 1..65535.');
        }
        final enteredKey = _keyController.text.trim();
        final enteredToken = _tokenController.text.trim();
        if (enteredKey.isNotEmpty || enteredToken.isNotEmpty) {
          final credentials = Esp32Credentials(keyHex: enteredKey, token: enteredToken);
          if (!credentials.isConfigured) throw FormatException(s.get('pairingRequired'));
          await widget.controller.saveEsp32Credentials(credentials);
        } else if (!widget.controller.esp32Configured) {
          throw FormatException(s.get('pairingRequired'));
        }
        settings = settings.copyWith(esp32ListenPort: port);
      }
      await widget.controller.updateSettings(settings);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s.get('finishSetup'))));
      setState(() {});
    } on FormatException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.controller.standaloneStrings;
    final configured = widget.controller.esp32Configured;
    return Scaffold(
      appBar: AppBar(title: Text(s.get('cameraSource'))),
      body: ListView(
        padding: UiMetrics.lightPagePadding,
        children: [
          _SourceTile(
            icon: Icons.smartphone_rounded,
            title: s.get('phoneCamera'),
            subtitle: s.get('phoneCameraBody'),
            selected: _source == CameraSourceType.phone,
            onTap: () => setState(() => _source = CameraSourceType.phone),
          ),
          const SizedBox(height: 12),
          _SourceTile(
            icon: Icons.wifi_tethering_rounded,
            title: s.get('esp32Camera'),
            subtitle: s.get('esp32CameraBody'),
            selected: _source == CameraSourceType.esp32,
            onTap: () => setState(() => _source = CameraSourceType.esp32),
          ),
          if (_source == CameraSourceType.esp32) ...[
            const SizedBox(height: 22),
            Text(s.get('esp32Pairing'), style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 10),
            Material(
              color: Colors.white,
              clipBehavior: Clip.antiAlias,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
                side: const BorderSide(color: AppTheme.border),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Icon(configured ? Icons.lock_rounded : Icons.lock_open_rounded,
                            color: configured ? AppTheme.green : const Color(0xFFFFA726)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            configured ? 'Secure credentials stored on device' : s.get('pairingRequired'),
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _portController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(labelText: s.get('esp32Port')),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _keyController,
                      autocorrect: false,
                      enableSuggestions: false,
                      decoration: InputDecoration(
                        labelText: s.get('aesKey'),
                        hintText: configured ? 'Leave blank to keep current key' : null,
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _tokenController,
                      obscureText: true,
                      autocorrect: false,
                      enableSuggestions: false,
                      decoration: InputDecoration(
                        labelText: s.get('authToken'),
                        hintText: configured ? 'Leave blank to keep current token' : null,
                      ),
                    ),
                    if (configured) ...[
                      const SizedBox(height: 10),
                      TextButton.icon(
                        onPressed: () async {
                          await widget.controller.clearEsp32Credentials();
                          if (mounted) setState(() {});
                        },
                        icon: const Icon(Icons.delete_outline_rounded),
                        label: const Text('Remove pairing'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.save_outlined),
            label: Text(s.get('savePairing')),
          ),
        ],
      ),
    );
  }
}

class _SourceTile extends StatelessWidget {
  const _SourceTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
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
                  child: Icon(icon, color: selected ? Colors.white : AppTheme.blue),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                      const SizedBox(height: 4),
                      Text(subtitle, style: const TextStyle(color: AppTheme.muted, height: 1.35)),
                    ],
                  ),
                ),
                Icon(selected ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                    color: selected ? AppTheme.blue : AppTheme.muted),
              ],
            ),
          ),
        ),
      );
}
