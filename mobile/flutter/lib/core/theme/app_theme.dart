import 'package:flutter/material.dart';

import 'ui_metrics.dart';

class AppTheme {
  static const navy = Color(0xFF07112F);
  static const navyDeep = Color(0xFF050D27);
  static const navy2 = Color(0xFF0A1A45);
  static const navyCard = Color(0xFF091634);
  static const navyBorder = Color(0xFF142755);
  static const tileStart = Color(0xFF0D3B67);
  static const tileEnd = Color(0xFF0A2854);
  static const tileBorder = Color(0xFF16497B);
  static const blue = Color(0xFF1976D2);
  static const cyan = Color(0xFF38BDF8);
  static const green = Color(0xFF159A63);
  static const greenStart = Color(0xFF147A50);
  static const greenEnd = Color(0xFF0E5B3D);
  static const greenBorder = Color(0xFF34C77C);
  static const red = Color(0xFFE51B23);
  static const page = Color(0xFFF7F8FC);
  static const border = Color(0xFFE7E9F0);
  static const text = Color(0xFF172033);
  static const muted = Color(0xFF747C8B);

  static const LinearGradient homeGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF081438), navyDeep],
  );

  static const LinearGradient homeTileGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [tileStart, tileEnd],
  );

  static const LinearGradient startGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [greenStart, greenEnd],
  );

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: blue,
      brightness: Brightness.light,
      surface: Colors.white,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: page,
      visualDensity: VisualDensity.standard,
      appBarTheme: const AppBarTheme(
        backgroundColor: navy,
        foregroundColor: Colors.white,
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        toolbarHeight: 60,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.1,
        ),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w800, color: text),
        headlineMedium: TextStyle(fontWeight: FontWeight.w800, color: text),
        titleLarge: TextStyle(fontWeight: FontWeight.w800, color: text),
        titleMedium: TextStyle(fontWeight: FontWeight.w700, color: text),
        bodyLarge: TextStyle(fontSize: 17, height: 1.35, color: text),
        bodyMedium: TextStyle(height: 1.35, color: text),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 17),
        labelStyle: const TextStyle(color: Color(0xFF667085), fontWeight: FontWeight.w600),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
          borderSide: const BorderSide(color: blue, width: 2),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(UiMetrics.controlHeight),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(UiMetrics.compactRadius)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(UiMetrics.controlHeight),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          side: const BorderSide(color: Color(0xFFD7DCE6)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(UiMetrics.compactRadius)),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: Colors.white,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
          side: const BorderSide(color: border),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.selected) ? Colors.white : null),
        trackColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.selected) ? blue : null),
      ),
      dividerColor: border,
    );
  }
}
