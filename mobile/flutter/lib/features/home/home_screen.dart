import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../camera/camera_screen.dart';
import '../connection/connection_screen.dart';
import '../history/history_screen.dart';
import '../language/language_screen.dart';
import '../settings/settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final strings = controller.strings;
    return Scaffold(
      backgroundColor: AppTheme.navy,
      body: SafeArea(
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xFF081438), Color(0xFF050D27)],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 14),
            child: Column(
              children: [
                Align(
                  alignment: Alignment.centerRight,
                  child: IconButton(
                    key: const Key('language-button'),
                    style: IconButton.styleFrom(foregroundColor: Colors.white),
                    tooltip: strings.get('languageTitle'),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => LanguageScreen(controller: controller)),
                    ),
                    icon: const Icon(Icons.language_rounded, size: 28),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  strings.get('appName'),
                  style: const TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.w900, letterSpacing: 1.5),
                ),
                const SizedBox(height: 8),
                Text(
                  strings.get('appSubtitle'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 19, height: 1.3, fontWeight: FontWeight.w500),
                ),
                const Spacer(),
                Semantics(
                  button: true,
                  label: strings.get('startAssistance').replaceAll('\n', ' '),
                  child: InkWell(
                    key: const Key('start-assistance-button'),
                    customBorder: const CircleBorder(),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => CameraScreen(controller: controller)),
                    ),
                    child: Container(
                      width: 168,
                      height: 168,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xFF147A50), Color(0xFF0E5B3D)],
                        ),
                        border: Border.all(color: const Color(0xFF34C77C), width: 4),
                        boxShadow: const [
                          BoxShadow(color: Color(0x5534C77C), blurRadius: 28, spreadRadius: 2),
                        ],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.graphic_eq_rounded, color: Colors.white, size: 44),
                          const SizedBox(height: 8),
                          Text(
                            strings.get('startAssistance'),
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white, fontSize: 16, height: 1.15, fontWeight: FontWeight.w800),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const Spacer(),
                Row(
                  children: [
                    Expanded(
                      child: _HomeTile(
                        icon: Icons.settings_outlined,
                        label: strings.get('settings'),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => SettingsScreen(controller: controller)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: _HomeTile(
                        icon: Icons.history_rounded,
                        label: strings.get('history'),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => HistoryScreen(controller: controller)),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
                  decoration: BoxDecoration(
                    color: const Color(0xFF091634),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFF142755)),
                  ),
                  child: Row(
                    children: [
                      const ContainerDot(),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          strings.get('notConnected'),
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                        ),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => ConnectionScreen(controller: controller)),
                        ),
                        icon: const Icon(Icons.cell_tower_rounded, color: Colors.white),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => LanguageScreen(controller: controller)),
                        ),
                        icon: const Icon(Icons.translate_rounded, color: Colors.white),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class ContainerDot extends StatelessWidget {
  const ContainerDot({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 9,
      height: 9,
      decoration: const BoxDecoration(color: AppTheme.red, shape: BoxShape.circle),
    );
  }
}

class _HomeTile extends StatelessWidget {
  const _HomeTile({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        height: 102,
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF0D3B67), Color(0xFF0A2854)]),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFF16497B)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 34),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15)),
          ],
        ),
      ),
    );
  }
}
