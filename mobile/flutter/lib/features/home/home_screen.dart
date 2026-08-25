import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/services/edge_connection_service.dart';
import '../camera/camera_screen.dart';
import '../settings/settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final endpoint = controller.edgeEndpoint;
    final configured = controller.edgeState == EdgeConfigurationState.configured;

    return Scaffold(
      appBar: AppBar(
        title: const Text('WVAB Mobile'),
        actions: [
          IconButton(
            tooltip: 'Settings',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => SettingsScreen(controller: controller),
              ),
            ),
            icon: const Icon(Icons.settings_accessibility),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Semantics(
              headingLevel: 1,
              child: Text(
                'Vision assistance',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Use the phone camera for accessible visual feedback. Edge streaming will only be enabled after Secure UDP Protocol v2 integration is complete.',
              style: TextStyle(fontSize: 18, height: 1.4),
            ),
            const SizedBox(height: 24),
            Semantics(
              button: true,
              label: 'Start camera assistance',
              hint: 'Opens the camera preview and enables local voice and vibration feedback.',
              child: FilledButton.icon(
                key: const Key('start-assistance-button'),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => CameraScreen(controller: controller),
                  ),
                ),
                icon: const Icon(Icons.visibility, size: 30),
                label: const Text('Start Assistance'),
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(56)),
              onPressed: () => controller.announce('WVAB Mobile feedback test'),
              icon: const Icon(Icons.record_voice_over),
              label: const Text('Test voice and vibration'),
            ),
            const SizedBox(height: 28),
            const Semantics(
              headingLevel: 2,
              child: Text('System status', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(height: 12),
            _StatusCard(
              icon: Icons.camera_alt,
              title: 'Camera',
              value: 'Ready to initialize',
            ),
            _StatusCard(
              icon: Icons.router,
              title: 'Edge server',
              value: configured && endpoint != null
                  ? 'Configured: $endpoint — transport not connected yet'
                  : 'Not configured',
            ),
            _StatusCard(
              icon: Icons.security,
              title: 'Secure transport',
              value: 'Protocol v2 integration pending',
            ),
            const SizedBox(height: 16),
            Text(
              'Safety: WVAB Mobile is an assistive research prototype and must not be treated as proof that a route is safe.',
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.icon, required this.title, required this.value});

  final IconData icon;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 30),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(value, style: Theme.of(context).textTheme.bodyLarge),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
