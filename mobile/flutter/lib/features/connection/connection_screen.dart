import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';

class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    final settings = widget.controller.settings;
    return Scaffold(
      appBar: AppBar(
        title: Text(strings.get('connection')),
        actions: [
          IconButton(
            onPressed: () => setState(() {}),
            icon: const Icon(Icons.refresh),
            tooltip: strings.get('connection'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFFFA726), Color(0xFFFB8C00)]),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                const Icon(Icons.wifi_off_rounded, color: Colors.white, size: 34),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        strings.get('endpointConfigured'),
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 18),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${settings.edgeHost}:${settings.edgePort}',
                        style: const TextStyle(color: Colors.white, fontSize: 16),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(strings.get('transportPending'), style: const TextStyle(color: Color(0xFF6C7280))),
          const SizedBox(height: 22),
          Text(strings.get('connectionHealth'), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                children: [
                  _MetricRow(label: strings.get('packetsSent'), value: '—'),
                  _MetricRow(label: strings.get('packetsReceived'), value: '—'),
                  _MetricRow(label: strings.get('packetLoss'), value: '—'),
                  _MetricRow(label: strings.get('lastUpdate'), value: '—', showDivider: false),
                ],
              ),
            ),
          ),
          const SizedBox(height: 22),
          Text(strings.get('reconnection'), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                SwitchListTile(
                  title: Text(strings.get('autoReconnect')),
                  value: settings.autoReconnect,
                  onChanged: (value) async {
                    await widget.controller.updateSettings(settings.copyWith(autoReconnect: value));
                    if (mounted) setState(() {});
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  title: Text(strings.get('reconnectInterval')),
                  trailing: Text(strings.get('seconds5')),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.blue,
              minimumSize: const Size.fromHeight(56),
              side: const BorderSide(color: AppTheme.blue),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(strings.get('endpointValid'))));
            },
            icon: const Icon(Icons.wifi_find),
            label: Text(strings.get('testConnection')),
          ),
        ],
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value, this.showDivider = true});

  final String label;
  final String value;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Row(
            children: [
              Expanded(child: Text(label)),
              Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1),
      ],
    );
  }
}
