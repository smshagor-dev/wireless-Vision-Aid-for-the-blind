import 'package:flutter/material.dart';

import 'core/controllers/app_controller.dart';
import 'core/theme/app_theme.dart';
import 'features/home/home_screen.dart';

class WvabMobileApp extends StatelessWidget {
  const WvabMobileApp({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'WVAB Mobile',
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: ThemeMode.system,
          home: HomeScreen(controller: controller),
        );
      },
    );
  }
}
