import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';
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
      appBar: AppBar(
        title: Text(strings.get('settings')),
        actions: [
          IconButton(
            tooltip: strings.get('languageTitle'),
            onPressed: _openLanguage,
            icon: const Icon(Icons.language_rounded),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              key: const Key('settings-list'),
              padding: UiMetrics.lightPagePadding,
              children: [
                _SectionLabel(strings.get('serverConnection')),
                const SizedBox(height: 10),
                _SettingsCard(
                  child: Column(
                    children: [
                      TextField(
                        controller: _hostController,
                        autocorrect: false,
                        keyboardType: TextInputType.url,
                        decoration: InputDecoration(
                          labelText: strings.get('serverIp'),
                          prefixIcon: const Icon(Icons.dns_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _portController,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: strings.get('port'),
                          prefixIcon: const Icon(Icons.cable_rounded),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                _SectionLabel(strings.get('mode')),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF3F9),
                    borderRadius: BorderRadius.circular(UiMetrics.compactRadius + 2),
                    border: Border.all(color: const Color(0xFFE1E6EE)),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: _ModeButton(
                          icon: Icons.dns_outlined,
                          label: strings.get('edgeServer'),
                          selected: _edgeMode,
                          onTap: () => setState(() => _edgeMode = true),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: _ModeButton(
                          icon: Icons.smartphone_rounded,
                          label: strings.get('onDevice'),
                          selected: !_edgeMode,
                          onTap: () => setState(() => _edgeMode = false),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                _SectionLabel(strings.get('feedback')),
                const SizedBox(height: 10),
                _SettingsCard(
                  padding: EdgeInsets.zero,
                  child: Column(
                    children: [
                      _SettingsTile(
                        icon: Icons.language_rounded,
                        title: strings.get('language'),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              selectedLanguage.split('-').first.toUpperCase(),
                              style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(width: 5),
                            const Icon(Icons.chevron_right_rounded, color: AppTheme.muted),
                          ],
                        ),
                        onTap: _openLanguage,
                      ),
                      const Divider(height: 1),
                      _SettingsTile(
                        icon: Icons.speed_rounded,
                        title: strings.get('speechRate'),
                        trailing: Text(
                          strings.get('normal'),
                          style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w700),
                        ),
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
                        secondary: const _TileIcon(icon: Icons.record_voice_over_outlined),
                        title: Text(strings.get('voiceGuidance'), style: const TextStyle(fontWeight: FontWeight.w700)),
                        value: _speechEnabled,
                        onChanged: (value) => setState(() => _speechEnabled = value),
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
                        secondary: const _TileIcon(icon: Icons.vibration_rounded),
                        title: Text(strings.get('vibration'), style: const TextStyle(fontWeight: FontWeight.w700)),
                        value: _vibrationEnabled,
                        onChanged: (value) => setState(() => _vibrationEnabled = value),
                      ),
                      const Divider(height: 1),
                      _SettingsTile(
                        icon: Icons.tune_rounded,
                        title: strings.get('hapticIntensity'),
                        trailing: Text(
                          strings.get('medium'),
                          style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                FilledButton.icon(
                  key: const Key('settings-save-button'),
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
              key: const Key('settings-bottom-nav'),
              height: UiMetrics.settingsBottomBarHeight,
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: AppTheme.border)),
                boxShadow: [BoxShadow(color: Color(0x0D000000), blurRadius: 12, offset: Offset(0, -3))],
              ),
              child: Row(
                children: [
                  Expanded(
                    child: _BottomTab(
                      icon: Icons.settings_rounded,
                      label: strings.get('general'),
                      active: true,
                      onTap: () {},
                    ),
                  ),
                  Expanded(
                    child: _BottomTab(
                      icon: Icons.center_focus_strong_outlined,
                      label: strings.get('detection'),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => DetectionSettingsScreen(controller: widget.controller)),
                      ),
                    ),
                  ),
                  Expanded(
                    child: _BottomTab(
                      icon: Icons.volume_up_outlined,
                      label: strings.get('audio'),
                      onTap: _openLanguage,
                    ),
                  ),
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
    return Text(
      text,
      style: const TextStyle(
        color: AppTheme.blue,
        fontWeight: FontWeight.w800,
        fontSize: 15,
        letterSpacing: 0.15,
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.child, this.padding = const EdgeInsets.all(16)});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      elevation: 0.5,
      shadowColor: const Color(0x18000000),
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
        side: const BorderSide(color: AppTheme.border),
      ),
      child: Padding(padding: padding, child: child),
    );
  }
}

class _TileIcon extends StatelessWidget {
  const _TileIcon({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        color: const Color(0xFFEAF3FF),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: AppTheme.blue, size: 21),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({required this.icon, required this.title, this.trailing, this.onTap});

  final IconData icon;
  final String title;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      minTileHeight: 62,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16),
      leading: _TileIcon(icon: icon),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      trailing: trailing,
      onTap: onTap,
    );
  }
}

class _ModeButton extends StatelessWidget {
  const _ModeButton({required this.icon, required this.label, required this.selected, required this.onTap});

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
      onTap: onTap,
      child: Container(
        height: 48,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? AppTheme.blue : Colors.transparent,
          borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
          boxShadow: selected
              ? const [BoxShadow(color: Color(0x261976D2), blurRadius: 8, offset: Offset(0, 3))]
              : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: selected ? Colors.white : const Color(0xFF586174), size: 20),
            const SizedBox(width: 7),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: selected ? Colors.white : const Color(0xFF303746),
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
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
    final color = active ? AppTheme.blue : AppTheme.muted;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 23),
            const SizedBox(height: 3),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: color, fontSize: 11, fontWeight: active ? FontWeight.w800 : FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}
