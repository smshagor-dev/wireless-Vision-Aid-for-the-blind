import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/models/detection_history_entry.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final strings = controller.strings;
        final entries = controller.history;
        return Scaffold(
          appBar: AppBar(
            title: Text(strings.get('history')),
            actions: [
              IconButton(
                key: const Key('history-clear-button'),
                onPressed: entries.isEmpty ? null : () => _confirmClear(context),
                icon: const Icon(Icons.delete_outline_rounded),
                tooltip: 'Clear history',
              ),
              const SizedBox(width: 6),
            ],
          ),
          body: entries.isEmpty
              ? _EmptyHistory(strings: strings)
              : ListView.separated(
                  key: const Key('history-list'),
                  padding: UiMetrics.lightPagePadding,
                  itemCount: entries.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (context, index) => _HistoryCard(
                    entry: entries[index],
                    objectName: controller.localizedObjectLabel(entries[index].label),
                  ),
                ),
        );
      },
    );
  }

  Future<void> _confirmClear(BuildContext context) async {
    final shouldClear = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear detection history?'),
        content: const Text('This permanently removes locally stored WVAB detection events from this device.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Clear')),
        ],
      ),
    );
    if (shouldClear == true) await controller.clearHistory();
  }
}

class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory({required this.strings});
  final AppStrings strings;

  @override
  Widget build(BuildContext context) => ListView(
        padding: UiMetrics.lightPagePadding,
        children: [
          Text(
            strings.get('today'),
            style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 15),
          ),
          const SizedBox(height: 10),
          Container(
            key: const Key('history-empty-card'),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 34),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
              border: Border.all(color: AppTheme.border),
              boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 10, offset: Offset(0, 3))],
            ),
            child: Column(
              children: [
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0F3F8),
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: const Icon(Icons.history_toggle_off_rounded, size: 42, color: Color(0xFF98A1B2)),
                ),
                const SizedBox(height: 16),
                Text(
                  strings.get('historyEmpty'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppTheme.text),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Detected objects will be stored locally on this device and appear here.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppTheme.muted, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const _PrivacyNotice(),
        ],
      );
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.entry, required this.objectName});
  final DetectionHistoryEntry entry;
  final String objectName;

  @override
  Widget build(BuildContext context) {
    final confidence = (entry.confidence * 100).round();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
        border: Border.all(color: AppTheme.border),
        boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 10, offset: Offset(0, 3))],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: const Color(0xFFEAF3FF),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.center_focus_strong_rounded, color: AppTheme.blue),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(objectName, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: AppTheme.text)),
                const SizedBox(height: 4),
                Text(
                  '${_pretty(entry.proximity.name)} • ${_pretty(entry.direction.name)} • $confidence%',
                  style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  '${_formatDate(entry.timestamp)} • ${entry.cameraSource == 'esp32' ? 'ESP32-CAM' : 'Phone camera'}',
                  style: const TextStyle(color: Color(0xFF7A8392), fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _pretty(String value) => '${value[0].toUpperCase()}${value.substring(1)}';

  static String _formatDate(DateTime value) {
    String two(int number) => number.toString().padLeft(2, '0');
    return '${value.year}-${two(value.month)}-${two(value.day)} ${two(value.hour)}:${two(value.minute)}:${two(value.second)}';
  }
}

class _PrivacyNotice extends StatelessWidget {
  const _PrivacyNotice();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F5FF),
          borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
          border: Border.all(color: const Color(0xFFDCE8FB)),
        ),
        child: const Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.lock_outline_rounded, color: AppTheme.blue, size: 22),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                'Detection history is stored locally in WVAB app storage. WVAB does not require a cloud account to keep this history.',
                style: TextStyle(color: Color(0xFF526070), height: 1.35),
              ),
            ),
          ],
        ),
      );
}
