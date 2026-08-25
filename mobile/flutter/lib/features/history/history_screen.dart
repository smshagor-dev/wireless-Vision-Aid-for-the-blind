import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';

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
            icon: const Icon(Icons.delete_outline),
            tooltip: strings.get('history'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(strings.get('today'), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 34),
              child: Column(
                children: [
                  const Icon(Icons.history_toggle_off, size: 58, color: Color(0xFF98A1B2)),
                  const SizedBox(height: 14),
                  Text(
                    strings.get('historyEmpty'),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    strings.get('historyHint'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Color(0xFF737B8C)),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF0F5FF),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                const Icon(Icons.lock_outline, color: Color(0xFF1976D2)),
                const SizedBox(width: 10),
                Expanded(child: Text(strings.get('prototypeNotice'))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
