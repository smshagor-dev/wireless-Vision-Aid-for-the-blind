import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/theme/app_theme.dart';

class LanguageScreen extends StatelessWidget {
  const LanguageScreen({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final strings = controller.strings;
    final selected = controller.settings.languageCode;
    return Scaffold(
      appBar: AppBar(title: Text(strings.get('languageTitle'))),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              Card(
                child: Column(
                  children: AppStrings.supportedLanguages.entries.map((entry) {
                    final active = entry.key == selected;
                    return ListTile(
                      key: Key('language-${entry.key}'),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                      title: Text(entry.value, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600)),
                      trailing: Icon(
                        active ? Icons.radio_button_checked : Icons.radio_button_off,
                        color: active ? AppTheme.blue : Colors.grey,
                      ),
                      onTap: () async {
                        await controller.setLanguage(entry.key);
                        if (context.mounted) Navigator.of(context).pop();
                      },
                    );
                  }).toList(),
                ),
              ),
              const Spacer(),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0F5FF),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline, color: AppTheme.blue),
                    const SizedBox(width: 10),
                    Expanded(child: Text(strings.get('languageHint'))),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
