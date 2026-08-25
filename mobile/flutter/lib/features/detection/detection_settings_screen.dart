import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';

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
        padding: const EdgeInsets.all(20),
        children: [
          Text(strings.get('confidenceThreshold'), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${strings.get('medium')} (${_confidence.toStringAsFixed(2)})', style: const TextStyle(fontWeight: FontWeight.w700)),
                  Slider(
                    value: _confidence,
                    min: 0.1,
                    max: 1.0,
                    divisions: 18,
                    activeColor: AppTheme.blue,
                    onChanged: (value) => setState(() => _confidence = value),
                  ),
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [Text('0.1'), Text('1.0')],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(strings.get('detectClasses'), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: _classKeys.map((key) {
                return CheckboxListTile(
                  value: _classes.contains(key),
                  title: Text(strings.get(key)),
                  activeColor: AppTheme.blue,
                  onChanged: (value) {
                    setState(() {
                      if (value == true) {
                        _classes.add(key);
                      } else {
                        _classes.remove(key);
                      }
                    });
                  },
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _save,
            child: Text(strings.get('saveChanges')),
          ),
        ],
      ),
    );
  }
}
