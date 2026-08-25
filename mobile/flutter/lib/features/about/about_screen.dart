import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final strings = controller.strings;
    return Scaffold(
      appBar: AppBar(title: Text(strings.get('about'))),
      body: ListView(
        padding: UiMetrics.lightPagePadding,
        children: [
          const SizedBox(height: 4),
          Center(
            child: Container(
              width: 108,
              height: 108,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [AppTheme.tileStart, AppTheme.blue],
                ),
                borderRadius: BorderRadius.circular(28),
                boxShadow: const [BoxShadow(color: Color(0x241976D2), blurRadius: 18, offset: Offset(0, 8))],
              ),
              child: const Icon(Icons.accessibility_new_rounded, color: Colors.white, size: 60),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            strings.get('appName'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 30, height: 1, fontWeight: FontWeight.w900, color: AppTheme.text),
          ),
          const SizedBox(height: 8),
          Text(
            strings.get('appSubtitle').replaceAll('\n', ' '),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16, height: 1.4, color: Color(0xFF4C5566)),
          ),
          const SizedBox(height: 8),
          Container(
            alignment: Alignment.center,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFFF0F3F8),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                strings.get('version'),
                style: const TextStyle(color: AppTheme.muted, fontWeight: FontWeight.w700),
              ),
            ),
          ),
          const SizedBox(height: 26),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
              border: Border.all(color: AppTheme.border),
              boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 10, offset: Offset(0, 3))],
            ),
            child: Column(
              children: [
                _AboutTile(icon: Icons.privacy_tip_outlined, title: strings.get('privacyPolicy')),
                const Divider(height: 1, indent: 68),
                _AboutTile(icon: Icons.code_rounded, title: strings.get('openSourceLicenses')),
                const Divider(height: 1, indent: 68),
                _AboutTile(icon: Icons.help_outline_rounded, title: strings.get('howItWorks')),
                const Divider(height: 1, indent: 68),
                _AboutTile(icon: Icons.mail_outline_rounded, title: strings.get('contact')),
              ],
            ),
          ),
          const SizedBox(height: 26),
          Text(
            strings.get('madeForAccessibility'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800, color: AppTheme.text),
          ),
          const SizedBox(height: 8),
          Text(
            strings.get('prototypeNotice'),
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppTheme.muted, height: 1.4),
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
      minTileHeight: 62,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16),
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(color: const Color(0xFFEAF3FF), borderRadius: BorderRadius.circular(12)),
        child: Icon(icon, color: AppTheme.blue, size: 21),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      trailing: const Icon(Icons.chevron_right_rounded, color: AppTheme.muted),
      onTap: () {},
    );
  }
}
