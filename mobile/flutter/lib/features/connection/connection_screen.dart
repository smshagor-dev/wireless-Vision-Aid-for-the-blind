import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

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
            icon: const Icon(Icons.refresh_rounded),
            tooltip: strings.get('connection'),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: ListView(
        padding: UiMetrics.lightPagePadding,
        children: [
          Container(
            key: const Key('connection-status-card'),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFFFFA726), Color(0xFFFB8C00)],
              ),
              borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
              boxShadow: const [BoxShadow(color: Color(0x22FB8C00), blurRadius: 16, offset: Offset(0, 6))],
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.wifi_off_rounded, color: Colors.white, size: 28),
                ),
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
                        style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            strings.get('transportPending'),
            style: const TextStyle(color: Color(0xFF6C7280), height: 1.35),
          ),
          const SizedBox(height: 22),
          _SectionTitle(strings.get('connectionHealth')),
          const SizedBox(height: 10),
          _Panel(
            child: Column(
              children: [
                _MetricRow(label: strings.get('packetsSent'), value: '—'),
                _MetricRow(label: strings.get('packetsReceived'), value: '—'),
                _MetricRow(label: strings.get('packetLoss'), value: '—'),
                _MetricRow(label: strings.get('lastUpdate'), value: '—', showDivider: false),
              ],
            ),
          ),
          const SizedBox(height: 22),
          _SectionTitle(strings.get('reconnection')),
          const SizedBox(height: 10),
          _Panel(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                SwitchListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
                  secondary: const _ConnectionIcon(icon: Icons.sync_rounded),
                  title: Text(strings.get('autoReconnect'), style: const TextStyle(fontWeight: FontWeight.w700)),
                  value: settings.autoReconnect,
                  onChanged: (value) async {
                    await widget.controller.updateSettings(settings.copyWith(autoReconnect: value));
                    if (mounted) setState(() {});
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  minTileHeight: 62,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                  leading: const _ConnectionIcon(icon: Icons.timer_outlined),
                  title: Text(strings.get('reconnectInterval'), style: const TextStyle(fontWeight: FontWeight.w700)),
                  trailing: Text(
                    strings.get('seconds5'),
                    style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: AppTheme.blue, side: const BorderSide(color: AppTheme.blue)),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(strings.get('endpointValid'))));
            },
            icon: const Icon(Icons.wifi_find_rounded),
            label: Text(strings.get('testConnection')),
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
    return Text(
      text,
      style: const TextStyle(color: AppTheme.blue, fontWeight: FontWeight.w800, fontSize: 15),
    );
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

class _ConnectionIcon extends StatelessWidget {
  const _ConnectionIcon({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(color: const Color(0xFFEAF3FF), borderRadius: BorderRadius.circular(12)),
      child: Icon(icon, color: AppTheme.blue, size: 21),
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
          padding: const EdgeInsets.symmetric(vertical: 11),
          child: Row(
            children: [
              Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))),
              Text(value, style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w800)),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1),
      ],
    );
  }
}
