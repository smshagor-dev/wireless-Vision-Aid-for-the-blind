import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/detection_history_entry.dart';

abstract class DetectionHistoryStore {
  Future<List<DetectionHistoryEntry>> load();
  Future<void> save(List<DetectionHistoryEntry> entries);
  Future<void> clear();
}

class SharedPreferencesDetectionHistoryStore implements DetectionHistoryStore {
  SharedPreferencesDetectionHistoryStore({SharedPreferencesAsync? preferences})
      : _preferences = preferences ?? SharedPreferencesAsync();

  static const _key = 'wvab.detection_history.v1';
  static const maxEntries = 300;
  final SharedPreferencesAsync _preferences;

  @override
  Future<List<DetectionHistoryEntry>> load() async {
    final raw = await _preferences.getString(_key);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return const [];
      return decoded
          .whereType<Map>()
          .map((item) => DetectionHistoryEntry.fromJson(Map<String, dynamic>.from(item)))
          .whereType<DetectionHistoryEntry>()
          .take(maxEntries)
          .toList(growable: false);
    } on FormatException {
      return const [];
    }
  }

  @override
  Future<void> save(List<DetectionHistoryEntry> entries) async {
    final payload = entries.take(maxEntries).map((entry) => entry.toJson()).toList(growable: false);
    await _preferences.setString(_key, jsonEncode(payload));
  }

  @override
  Future<void> clear() async {
    await _preferences.remove(_key);
  }
}

class MemoryDetectionHistoryStore implements DetectionHistoryStore {
  MemoryDetectionHistoryStore([List<DetectionHistoryEntry>? initial])
      : _entries = List<DetectionHistoryEntry>.from(initial ?? const []);

  List<DetectionHistoryEntry> _entries;

  @override
  Future<List<DetectionHistoryEntry>> load() async => List.unmodifiable(_entries);

  @override
  Future<void> save(List<DetectionHistoryEntry> entries) async {
    _entries = List<DetectionHistoryEntry>.from(entries);
  }

  @override
  Future<void> clear() async {
    _entries = <DetectionHistoryEntry>[];
  }
}
