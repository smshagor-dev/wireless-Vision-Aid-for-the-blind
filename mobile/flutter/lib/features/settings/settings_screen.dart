import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late String _languageCode;
  late bool _speechEnabled;
  late bool _vibrationEnabled;
  late final TextEditingController _hostController;
  late final TextEditingController _portController;

  static const _languages = <String, String>{
    'en-US': 'English',
    'bn-BD': 'বাংলা',
    'ru-RU': 'Русский',
    'hi-IN': 'हिन्दी',
  };

  @override
  void initState() {
    super.initState();
    final settings = widget.controller.settings;
    _languageCode = settings.languageCode;
    _speechEnabled = settings.speechEnabled;
    _vibrationEnabled = settings.vibrationEnabled;
    _hostController = TextEditingController(text: settings.edgeHost);
    _portController = TextEditingController(text: settings.edgePort.toString());
  }

  @override
  void dispose() {
    _hostController.dispose();
    _portController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final port = int.tryParse(_portController.text.trim());
    if (port == null) {
      _showError('Enter a numeric port.');
      return;
    }

    final updated = widget.controller.settings.copyWith(
      languageCode: _languageCode,
      speechEnabled: _speechEnabled,
      vibrationEnabled: _vibrationEnabled,
      edgeHost: _hostController.text.trim(),
      edgePort: port,
    );

    try {
      await widget.controller.updateSettings(updated);
    } on FormatException catch (error) {
      _showError(error.message);
      return;
    }

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Settings saved')));
    Navigator.of(context).pop();
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Accessibility settings')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Semantics(
              headingLevel: 1,
              child: const Text('Feedback', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _languageCode,
              decoration: const InputDecoration(labelText: 'Speech language', border: OutlineInputBorder()),
              items: _languages.entries
                  .map((entry) => DropdownMenuItem(value: entry.key, child: Text(entry.value)))
                  .toList(),
              onChanged: (value) {
                if (value != null) setState(() => _languageCode = value);
              },
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              title: const Text('Voice guidance'),
              subtitle: const Text('Speak assistive feedback through the selected Android TTS voice.'),
              value: _speechEnabled,
              onChanged: (value) => setState(() => _speechEnabled = value),
            ),
            SwitchListTile(
              title: const Text('Vibration feedback'),
              value: _vibrationEnabled,
              onChanged: (value) => setState(() => _vibrationEnabled = value),
            ),
            const SizedBox(height: 24),
            Semantics(
              headingLevel: 2,
              child: const Text('Edge server', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _hostController,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: const InputDecoration(
                labelText: 'Host or IP address',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _portController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'UDP port', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            const Text('Saving an endpoint does not establish a network connection. Secure UDP Protocol v2 integration is a separate implementation step.'),
            const SizedBox(height: 28),
            FilledButton.icon(
              onPressed: _save,
              icon: const Icon(Icons.save),
              label: const Text('Save settings'),
            ),
          ],
        ),
      ),
    );
  }
}
