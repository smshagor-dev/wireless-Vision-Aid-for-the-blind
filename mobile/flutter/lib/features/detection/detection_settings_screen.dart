import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class DetectionSettingsScreen extends StatefulWidget {
  const DetectionSettingsScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<DetectionSettingsScreen> createState() => _DetectionSettingsScreenState();
}

class _DetectionSettingsScreenState extends State<DetectionSettingsScreen> {
  late double _confidence;
  late Set<String> _classes;

  static const _classKeys = <String>[
    'person',
    'vehicle',
    'bicycle',
    'motorcycle',
    'obstacle',
    'stairs',
    'curb',
  ];

  @override
  void initState() {
    super.initState();
    _confidence = widget.controller.settings.detectionConfidence;
    _classes = {...widget.controller.settings.detectedClasses};
  }

  Future<void> _save() async {
    await widget.controller.updateSettings(
      widget.controller.settings.copyWith(
        detectionConfidence: _confidence,
        detectedClasses: _classes,
      ),
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(widget.controller.strings.get('saveChanges'))));
  }

  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    return Scaffold(
      appBar: AppBar(title: Text(strings.get('detectionSettings'))),
      body: ListView(
        padding: UiMetrics.lightPagePadding,
        children: [
          _SectionTitle(strings.get('confidenceThreshold')),
          const SizedBox(height: 10),
          _Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        strings.get('medium'),
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEAF3FF),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        _confidence.toStringAsFixed(2),
                        style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    activeTrackColor: AppTheme.blue,
                    inactiveTrackColor: const Color(0xFFDDE3EC),
                    thumbColor: AppTheme.blue,
                    overlayColor: const Color(0x221976D2),
                    trackHeight: 4,
                  ),
                  child: Slider(
                    value: _confidence,
                    min: 0.1,
                    max: 1.0,
                    divisions: 18,
                    onChanged: (value) => setState(() => _confidence = value),
                  ),
                ),
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('0.1', style: TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w600)),
                    Text('1.0', style: TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w600)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          _SectionTitle(strings.get('detectClasses')),
          const SizedBox(height: 10),
          _Panel(
            padding: EdgeInsets.zero,
            child: Column(
              children: _classKeys.asMap().entries.map((entry) {
                final index = entry.key;
                final key = entry.value;
                return Column(
                  children: [
                    CheckboxListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 1),
                      value: _classes.contains(key),
                      title: Text(strings.get(key), style: const TextStyle(fontWeight: FontWeight.w700)),
                      activeColor: AppTheme.blue,
                      controlAffinity: ListTileControlAffinity.trailing,
                      secondary: Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEAF3FF),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.center_focus_strong_rounded, color: AppTheme.blue, size: 20),
                      ),
                      onChanged: (value) {
                        setState(() {
                          if (value == true) {
                            _classes.add(key);
                          } else {
                            _classes.remove(key);
                          }
                        });
                      },
                    ),
                    if (index != _classKeys.length - 1) const Divider(height: 1, indent: 70),
                  ],
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            key: const Key('detection-save-button'),
            onPressed: _save,
            icon: const Icon(Icons.save_outlined),
            label: Text(strings.get('saveChanges')),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text, style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 15));
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child, this.padding = const EdgeInsets.all(16)});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
        border: Border.all(color: AppTheme.border),
        boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 10, offset: Offset(0, 3))],
      ),
      child: child,
    );
  }
}
