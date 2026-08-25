import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final strings = controller.strings;
    return Scaffold(
      appBar: AppBar(title: Text(strings.get('about'))),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const SizedBox(height: 12),
          Center(
            child: Container(
              width: 112,
              height: 112,
              decoration: BoxDecoration(
                color: AppTheme.blue,
                borderRadius: BorderRadius.circular(28),
              ),
              child: const Icon(Icons.accessibility_new_rounded, color: Colors.white, size: 64),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            strings.get('appName'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          Text(
            strings.get('appSubtitle').replaceAll('\n', ' '),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 17),
          ),
          const SizedBox(height: 8),
          Text(
            strings.get('version'),
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFF7B8290)),
          ),
          const SizedBox(height: 28),
          Card(
            child: Column(
              children: [
                _AboutTile(icon: Icons.privacy_tip_outlined, title: strings.get('privacyPolicy')),
                const Divider(height: 1),
                _AboutTile(icon: Icons.code_rounded, title: strings.get('openSourceLicenses')),
                const Divider(height: 1),
                _AboutTile(icon: Icons.help_outline_rounded, title: strings.get('howItWorks')),
                const Divider(height: 1),
                _AboutTile(icon: Icons.mail_outline_rounded, title: strings.get('contact')),
              ],
            ),
          ),
          const SizedBox(height: 26),
          Text(
            strings.get('madeForAccessibility'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          Text(
            strings.get('prototypeNotice'),
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFF737B8C)),
          ),
        ],
      ),
    );
  }
}

class _AboutTile extends StatelessWidget {
  const _AboutTile({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppTheme.blue),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: () {},
    );
  }
}
