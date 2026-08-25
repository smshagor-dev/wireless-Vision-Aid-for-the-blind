import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/models/app_settings.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';
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
    final standalone = controller.standaloneStrings;
    final usingPhone = controller.settings.cameraSource == CameraSourceType.phone;
    final sourceReady = usingPhone || controller.esp32Configured;
    final sourceLabel = usingPhone
        ? standalone.get('phoneCamera')
        : controller.esp32Configured
            ? standalone.get('esp32Camera')
            : standalone.get('pairingRequired');
    return Scaffold(
      backgroundColor: AppTheme.navy,
      body: SafeArea(
        child: DecoratedBox(
          decoration: const BoxDecoration(gradient: AppTheme.homeGradient),
          child: Padding(
            padding: UiMetrics.homePadding,
            child: Column(
              children: [
                Align(
                  alignment: Alignment.centerRight,
                  child: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.06),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                    ),
                    child: IconButton(
                      key: const Key('language-button'),
                      padding: EdgeInsets.zero,
                      style: IconButton.styleFrom(foregroundColor: Colors.white),
                      tooltip: strings.get('languageTitle'),
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => LanguageScreen(controller: controller)),
                      ),
                      icon: const Icon(Icons.language_rounded, size: 25),
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  strings.get('appName'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 40,
                    height: 1,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 1.6,
                  ),
                ),
                const SizedBox(height: 9),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Text(
                    strings.get('appSubtitle'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Color(0xFFF3F6FF),
                      fontSize: 19,
                      height: 1.3,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                const Spacer(),
                Semantics(
                  button: true,
                  label: strings.get('startAssistance').replaceAll('\n', ' '),
                  child: InkWell(
                    key: const Key('start-assistance-button'),
                    customBorder: const CircleBorder(),
                    onTap: sourceReady
                        ? () => Navigator.of(context).push(
                              MaterialPageRoute<void>(builder: (_) => CameraScreen(controller: controller)),
                            )
                        : () => Navigator.of(context).push(
                              MaterialPageRoute<void>(builder: (_) => ConnectionScreen(controller: controller)),
                            ),
                    child: Container(
                      key: const Key('home-start-circle'),
                      width: UiMetrics.homeActionDiameter,
                      height: UiMetrics.homeActionDiameter,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: AppTheme.startGradient,
                        border: Border.all(color: AppTheme.greenBorder, width: 4),
                        boxShadow: const [
                          BoxShadow(color: Color(0x3034C77C), blurRadius: 40, spreadRadius: 8),
                          BoxShadow(color: Color(0x5534C77C), blurRadius: 20, spreadRadius: 1),
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
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              height: 1.15,
                              fontWeight: FontWeight.w800,
                            ),
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
                        key: const Key('home-settings-tile'),
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
                        key: const Key('home-history-tile'),
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
                  key: const Key('home-status-bar'),
                  constraints: const BoxConstraints(minHeight: 54),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                  decoration: BoxDecoration(
                    color: AppTheme.navyCard,
                    borderRadius: BorderRadius.circular(UiMetrics.statusRadius),
                    border: Border.all(color: AppTheme.navyBorder),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 9,
                        height: 9,
                        decoration: BoxDecoration(
                          color: sourceReady ? AppTheme.greenBorder : const Color(0xFFFFA726),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          sourceLabel,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 14),
                        ),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        tooltip: standalone.get('cameraSource'),
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => ConnectionScreen(controller: controller)),
                        ),
                        icon: Icon(usingPhone ? Icons.smartphone_rounded : Icons.wifi_tethering_rounded,
                            color: Colors.white, size: 22),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        tooltip: strings.get('languageTitle'),
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => LanguageScreen(controller: controller)),
                        ),
                        icon: const Icon(Icons.translate_rounded, color: Colors.white, size: 22),
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

class _HomeTile extends StatelessWidget {
  const _HomeTile({super.key, required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
      onTap: onTap,
      child: Container(
        height: UiMetrics.homeTileHeight,
        decoration: BoxDecoration(
          gradient: AppTheme.homeTileGradient,
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          border: Border.all(color: AppTheme.tileBorder),
          boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 10, offset: Offset(0, 4))],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 34),
            const SizedBox(height: 8),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15),
            ),
          ],
        ),
      ),
    );
  }
}
