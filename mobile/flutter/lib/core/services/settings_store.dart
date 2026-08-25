import 'package:shared_preferences/shared_preferences.dart';

import '../models/app_settings.dart';

abstract class SettingsStore {
  Future<AppSettings> load();
  Future<void> save(AppSettings settings);
}

class SharedPreferencesSettingsStore implements SettingsStore {
  SharedPreferencesSettingsStore({SharedPreferencesAsync? preferences})
      : _preferences = preferences ?? SharedPreferencesAsync();

  static const _prefix = 'wvab.';
  final SharedPreferencesAsync _preferences;

  @override
  Future<AppSettings> load() async {
    final language = await _preferences.getString('${_prefix}language');
    final source = await _preferences.getString('${_prefix}camera_source');
    final classes = await _preferences.getStringList('${_prefix}detected_classes');
    return AppSettings(
      firstRunCompleted: await _preferences.getBool('${_prefix}first_run_completed') ?? false,
      languageCode: language ?? 'en-US',
      cameraSource: cameraSourceFromStorage(source),
      speechEnabled: await _preferences.getBool('${_prefix}speech_enabled') ?? true,
      vibrationEnabled: await _preferences.getBool('${_prefix}vibration_enabled') ?? true,
      esp32ListenPort: await _preferences.getInt('${_prefix}esp32_listen_port') ?? 9999,
      autoReconnect: await _preferences.getBool('${_prefix}auto_reconnect') ?? true,
      detectionConfidence: await _preferences.getDouble('${_prefix}detection_confidence') ?? 0.50,
      detectedClasses: classes == null ? const AppSettings().detectedClasses : classes.toSet(),
    );
  }

  @override
  Future<void> save(AppSettings settings) async {
    await _preferences.setBool('${_prefix}first_run_completed', settings.firstRunCompleted);
    await _preferences.setString('${_prefix}language', settings.languageCode);
    await _preferences.setString('${_prefix}camera_source', settings.cameraSource.storageValue);
    await _preferences.setBool('${_prefix}speech_enabled', settings.speechEnabled);
    await _preferences.setBool('${_prefix}vibration_enabled', settings.vibrationEnabled);
    await _preferences.setInt('${_prefix}esp32_listen_port', settings.esp32ListenPort);
    await _preferences.setBool('${_prefix}auto_reconnect', settings.autoReconnect);
    await _preferences.setDouble('${_prefix}detection_confidence', settings.detectionConfidence);
    await _preferences.setStringList(
      '${_prefix}detected_classes',
      settings.detectedClasses.toList()..sort(),
    );
  }
}

class MemorySettingsStore implements SettingsStore {
  MemorySettingsStore([AppSettings? initial]) : _settings = initial ?? const AppSettings();
  AppSettings _settings;

  @override
  Future<AppSettings> load() async => _settings;

  @override
  Future<void> save(AppSettings settings) async {
    _settings = settings;
  }
}
