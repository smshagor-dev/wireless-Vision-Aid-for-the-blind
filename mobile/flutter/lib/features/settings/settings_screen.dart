import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../about/about_screen.dart';
import '../connection/connection_screen.dart';
import '../detection/detection_settings_screen.dart';
import '../language/language_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late bool _speechEnabled;
  late bool _vibrationEnabled;
  late bool _edgeMode;
  late final TextEditingController _hostController;
  late final TextEditingController _portController;

  @override
  void initState() {
    super.initState();
    final settings = widget.controller.settings;
    _speechEnabled = settings.speechEnabled;
    _vibrationEnabled = settings.vibrationEnabled;
    _edgeMode = settings.edgeMode;
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
    if (port == null || port < 1 || port > 65535) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a valid UDP port.')));
      return;
    }
    final updated = widget.controller.settings.copyWith(
      speechEnabled: _speechEnabled,
      vibrationEnabled: _vibrationEnabled,
      edgeHost: _hostController.text.trim(),
      edgePort: port,
      edgeMode: _edgeMode,
    );
    try {
      await widget.controller.updateSettings(updated);
    } on FormatException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      return;
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(widget.controller.strings.get('saveChanges'))));
  }

  Future<void> _openLanguage() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => LanguageScreen(controller: widget.controller)),
    );
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    final selectedLanguage = widget.controller.settings.languageCode;
    return Scaffold(
      appBar: AppBar(title: Text(strings.get('settings'))),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                _SectionLabel(strings.get('serverConnection')),
                const SizedBox(height: 10),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        TextField(
                          controller: _hostController,
                          autocorrect: false,
                          keyboardType: TextInputType.url,
                          decoration: InputDecoration(labelText: strings.get('serverIp')),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _portController,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(labelText: strings.get('port')),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                _SectionLabel(strings.get('mode')),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _ModeButton(
                        label: strings.get('edgeServer'),
                        selected: _edgeMode,
                        onTap: () => setState(() => _edgeMode = true),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _ModeButton(
                        label: strings.get('onDevice'),
                        selected: !_edgeMode,
                        onTap: () => setState(() => _edgeMode = false),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                _SectionLabel(strings.get('feedback')),
                const SizedBox(height: 10),
                Card(
                  child: Column(
                    children: [
                      ListTile(
                        leading: const Icon(Icons.language_rounded, color: AppTheme.blue),
                        title: Text(strings.get('language')),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(selectedLanguage.split('-').first.toUpperCase()),
                            const SizedBox(width: 6),
                            const Icon(Icons.chevron_right_rounded),
                          ],
                        ),
                        onTap: _openLanguage,
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.speed_rounded, color: AppTheme.blue),
                        title: Text(strings.get('speechRate')),
                        trailing: Text(strings.get('normal')),
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        secondary: const Icon(Icons.record_voice_over_outlined, color: AppTheme.blue),
                        title: Text(strings.get('voiceGuidance')),
                        value: _speechEnabled,
                        onChanged: (value) => setState(() => _speechEnabled = value),
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        secondary: const Icon(Icons.vibration_rounded, color: AppTheme.blue),
                        title: Text(strings.get('vibration')),
                        value: _vibrationEnabled,
                        onChanged: (value) => setState(() => _vibrationEnabled = value),
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.tune_rounded, color: AppTheme.blue),
                        title: Text(strings.get('hapticIntensity')),
                        trailing: Text(strings.get('medium')),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                FilledButton.icon(
                  onPressed: _save,
                  icon: const Icon(Icons.save_outlined),
                  label: Text(strings.get('saveChanges')),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => ConnectionScreen(controller: widget.controller)),
                  ),
                  icon: const Icon(Icons.cell_tower_rounded),
                  label: Text(strings.get('connection')),
                ),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Container(
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: Color(0xFFE6E8EF))),
              ),
              child: Row(
                children: [
                  Expanded(child: _BottomTab(icon: Icons.settings_outlined, label: strings.get('general'), active: true, onTap: () {})),
                  Expanded(
                    child: _BottomTab(
                      icon: Icons.center_focus_strong_outlined,
                      label: strings.get('detection'),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => DetectionSettingsScreen(controller: widget.controller)),
                      ),
                    ),
                  ),
                  Expanded(child: _BottomTab(icon: Icons.volume_up_outlined, label: strings.get('audio'), onTap: _openLanguage)),
                  Expanded(
                    child: _BottomTab(
                      icon: Icons.info_outline_rounded,
                      label: strings.get('about'),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => AboutScreen(controller: widget.controller)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text, style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 16));
  }
}

class _ModeButton extends StatelessWidget {
  const _ModeButton({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        height: 48,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? AppTheme.blue : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? AppTheme.blue : const Color(0xFFE1E4EC)),
        ),
        child: Text(
          label,
          style: TextStyle(color: selected ? Colors.white : const Color(0xFF303746), fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

class _BottomTab extends StatelessWidget {
  const _BottomTab({required this.icon, required this.label, required this.onTap, this.active = false});

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final color = active ? AppTheme.blue : const Color(0xFF747C8B);
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 23),
            const SizedBox(height: 3),
            Text(label, overflow: TextOverflow.ellipsis, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
