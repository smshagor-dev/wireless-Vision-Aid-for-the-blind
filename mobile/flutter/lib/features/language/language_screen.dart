import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

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
          padding: UiMetrics.lightPagePadding,
          child: Column(
            children: [
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
                  border: Border.all(color: AppTheme.border),
                  boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 10, offset: Offset(0, 3))],
                ),
                child: Column(
                  children: AppStrings.supportedLanguages.entries.map((entry) {
                    final active = entry.key == selected;
                    final index = AppStrings.supportedLanguages.keys.toList().indexOf(entry.key);
                    return Column(
                      children: [
                        InkWell(
                          key: Key('language-${entry.key}'),
                          borderRadius: BorderRadius.vertical(
                            top: index == 0 ? const Radius.circular(UiMetrics.cardRadius) : Radius.zero,
                            bottom: index == AppStrings.supportedLanguages.length - 1
                                ? const Radius.circular(UiMetrics.cardRadius)
                                : Radius.zero,
                          ),
                          onTap: () async {
                            await controller.setLanguage(entry.key);
                            if (context.mounted) Navigator.of(context).pop();
                          },
                          child: Container(
                            minHeight: 64,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            color: active ? const Color(0xFFF1F6FF) : Colors.transparent,
                            child: Row(
                              children: [
                                Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: active ? AppTheme.blue : const Color(0xFFF0F2F6),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Icon(
                                    Icons.translate_rounded,
                                    color: active ? Colors.white : const Color(0xFF697386),
                                    size: 21,
                                  ),
                                ),
                                const SizedBox(width: 13),
                                Expanded(
                                  child: Text(
                                    entry.value,
                                    style: TextStyle(
                                      fontSize: 17,
                                      fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                                      color: AppTheme.text,
                                    ),
                                  ),
                                ),
                                Container(
                                  width: 24,
                                  height: 24,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: active ? AppTheme.blue : Colors.transparent,
                                    border: Border.all(color: active ? AppTheme.blue : const Color(0xFFC9CED8), width: 2),
                                  ),
                                  child: active ? const Icon(Icons.check_rounded, color: Colors.white, size: 16) : null,
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (index != AppStrings.supportedLanguages.length - 1)
                          const Divider(height: 1, indent: 69),
                      ],
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
                  borderRadius: BorderRadius.circular(UiMetrics.compactRadius),
                  border: Border.all(color: const Color(0xFFDCE8FB)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline_rounded, color: AppTheme.blue, size: 22),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        strings.get('languageHint'),
                        style: const TextStyle(color: Color(0xFF526070), height: 1.35),
                      ),
                    ),
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
