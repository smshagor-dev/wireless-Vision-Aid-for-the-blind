import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/localization/language_catalog.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';

class LanguageScreen extends StatefulWidget {
  const LanguageScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<LanguageScreen> createState() => _LanguageScreenState();
}

class _LanguageScreenState extends State<LanguageScreen> {
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    final selected = widget.controller.settings.languageCode;
    final entries = LanguageCatalog.supported.entries.where((entry) {
      final query = _query.trim().toLowerCase();
      return query.isEmpty ||
          entry.key.toLowerCase().contains(query) ||
          entry.value.toLowerCase().contains(query);
    }).toList(growable: false);

    return Scaffold(
      appBar: AppBar(title: Text(strings.get('languageTitle'))),
      body: SafeArea(
        child: ListView(
          padding: UiMetrics.lightPagePadding,
          children: [
            TextField(
              key: const Key('language-search'),
              controller: _searchController,
              onChanged: (value) => setState(() => _query = value),
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search_rounded),
                labelText: 'Search language',
                hintText: 'English, বাংলা, Русский…',
              ),
            ),
            const SizedBox(height: 14),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
                border: Border.all(color: AppTheme.border),
                boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 10, offset: Offset(0, 3))],
              ),
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
                  for (var index = 0; index < entries.length; index++) ...[
                    _LanguageTile(
                      entry: entries[index],
                      active: entries[index].key == selected,
                      onTap: () async {
                        await widget.controller.setLanguage(entries[index].key);
                        if (mounted) setState(() {});
                      },
                    ),
                    if (index != entries.length - 1) const Divider(height: 1, indent: 69),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),
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
                      '${strings.get('languageHint')} For locales without a full WVAB translation, interface text falls back to English. Voice uses the selected Android TTS voice when installed and otherwise falls back to English.',
                      style: const TextStyle(color: Color(0xFF526070), height: 1.35),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LanguageTile extends StatelessWidget {
  const _LanguageTile({required this.entry, required this.active, required this.onTap});

  final MapEntry<String, String> entry;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      key: Key('language-${entry.key}'),
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 64),
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.value,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                      color: AppTheme.text,
                    ),
                  ),
                  if (!LanguageCatalog.hasFullInterface(entry.key))
                    const Text(
                      'English interface fallback',
                      style: TextStyle(fontSize: 12, color: AppTheme.muted),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 8),
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
    );
  }
}
