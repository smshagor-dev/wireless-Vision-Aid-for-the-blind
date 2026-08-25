import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/models/app_settings.dart';
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
  late CameraSourceType _cameraSource;

  @override
  void initState() {
    super.initState();
    final settings = widget.controller.settings;
    _speechEnabled = settings.speechEnabled;
    _vibrationEnabled = settings.vibrationEnabled;
    _cameraSource = settings.cameraSource;
  }

  Future<void> _save() async {
    try {
      await widget.controller.updateSettings(widget.controller.settings.copyWith(
        speechEnabled: _speechEnabled,
        vibrationEnabled: _vibrationEnabled,
        cameraSource: _cameraSource,
      ));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(widget.controller.strings.get('saveChanges'))));
    } on FormatException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    }
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
    final standalone = widget.controller.standaloneStrings;
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
                _SectionLabel(standalone.get('cameraSource')),
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
                          icon: Icons.smartphone_rounded,
                          label: standalone.get('phoneCamera'),
                          selected: _cameraSource == CameraSourceType.phone,
                          onTap: () => setState(() => _cameraSource = CameraSourceType.phone),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: _ModeButton(
                          icon: Icons.wifi_tethering_rounded,
                          label: standalone.get('esp32Camera'),
                          selected: _cameraSource == CameraSourceType.esp32,
                          onTap: () => setState(() => _cameraSource = CameraSourceType.esp32),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => ConnectionScreen(controller: widget.controller)),
                  ),
                  icon: const Icon(Icons.tune_rounded),
                  label: Text(standalone.get('esp32Pairing')),
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
                            Text(selectedLanguage.split('-').first.toUpperCase(),
                                style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w700)),
                            const SizedBox(width: 5),
                            const Icon(Icons.chevron_right_rounded, color: AppTheme.muted),
                          ],
                        ),
                        onTap: _openLanguage,
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
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                _SectionLabel(standalone.get('localRuntime')),
                const SizedBox(height: 10),
                _SettingsCard(
                  padding: EdgeInsets.zero,
                  child: _SettingsTile(
                    icon: Icons.memory_rounded,
                    title: switch (widget.controller.runtimeState) {
                      LocalRuntimeState.ready => standalone.get('runtimeReady'),
                      LocalRuntimeState.initializing => standalone.get('runtimeStarting'),
                      LocalRuntimeState.error => standalone.get('runtimeUnavailable'),
                      LocalRuntimeState.idle => standalone.get('localRuntime'),
                    },
                    trailing: const Icon(Icons.chevron_right_rounded, color: AppTheme.muted),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => DetectionSettingsScreen(controller: widget.controller)),
                    ),
                  ),
                ),
                const SizedBox(height: 22),
                FilledButton.icon(
                  key: const Key('settings-save-button'),
                  onPressed: _save,
                  icon: const Icon(Icons.save_outlined),
                  label: Text(strings.get('saveChanges')),
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
                  Expanded(child: _BottomTab(icon: Icons.settings_rounded, label: strings.get('general'), active: true, onTap: () {})),
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
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 15, letterSpacing: 0.15),
      );
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.child, this.padding = const EdgeInsets.all(16)});
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Material(
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

class _TileIcon extends StatelessWidget {
  const _TileIcon({required this.icon});
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(color: const Color(0xFFEAF3FF), borderRadius: BorderRadius.circular(12)),
        child: Icon(icon, color: AppTheme.blue, size: 21),
      );
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({required this.icon, required this.title, this.trailing, this.onTap});
  final IconData icon;
  final String title;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => ListTile(
        minTileHeight: 62,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16),
        leading: _TileIcon(icon: icon),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        trailing: trailing,
        onTap: onTap,
      );
}

class _ModeButton extends StatelessWidget {
  const _ModeButton({required this.icon, required this.label, required this.selected, required this.onTap});
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
        onTap: onTap,
        child: Container(
          height: 48,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? AppTheme.blue : Colors.transparent,
            borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
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
                  style: TextStyle(color: selected ? Colors.white : const Color(0xFF303746), fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
        ),
      );
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
            Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: color, fontSize: 11, fontWeight: active ? FontWeight.w800 : FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
