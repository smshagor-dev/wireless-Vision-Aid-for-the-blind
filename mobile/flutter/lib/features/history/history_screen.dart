import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final strings = controller.strings;
    return Scaffold(
      appBar: AppBar(
        title: Text(strings.get('history')),
        actions: [
          IconButton(
            onPressed: null,
            icon: const Icon(Icons.delete_outline_rounded),
            tooltip: strings.get('history'),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: ListView(
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
                Text(
                  strings.get('historyHint'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppTheme.muted, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF0F5FF),
              borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
              border: Border.all(color: const Color(0xFFDCE8FB)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.lock_outline_rounded, color: AppTheme.blue, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    strings.get('prototypeNotice'),
                    style: const TextStyle(color: Color(0xFF526070), height: 1.35),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
