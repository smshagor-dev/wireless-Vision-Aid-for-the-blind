import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class Esp32Credentials {
  const Esp32Credentials({required this.keyHex, required this.token});

  final String keyHex;
  final String token;

  bool get isConfigured {
    final cleanKey = keyHex.trim();
    final keyBytes = cleanKey.length ~/ 2;
    return RegExp(r'^[0-9a-fA-F]+$').hasMatch(cleanKey) &&
        cleanKey.length.isEven &&
        (keyBytes == 16 || keyBytes == 24 || keyBytes == 32) &&
        token.trim().length >= 16;
  }
}

abstract class Esp32CredentialsStore {
  Future<Esp32Credentials?> read();
  Future<void> write(Esp32Credentials credentials);
  Future<void> clear();
}

class SecureEsp32CredentialsStore implements Esp32CredentialsStore {
  SecureEsp32CredentialsStore({FlutterSecureStorage? storage})
      : _storage = storage ?? FlutterSecureStorage(aOptions: AndroidOptions());

  static const _keyName = 'wvab.esp32.aes_key_hex';
  static const _tokenName = 'wvab.esp32.token';
  final FlutterSecureStorage _storage;

  @override
  Future<Esp32Credentials?> read() async {
    final key = await _storage.read(key: _keyName);
    final token = await _storage.read(key: _tokenName);
    if (key == null || token == null) return null;
    final credentials = Esp32Credentials(keyHex: key, token: token);
    return credentials.isConfigured ? credentials : null;
  }

  @override
  Future<void> write(Esp32Credentials credentials) async {
    if (!credentials.isConfigured) {
      throw const FormatException('ESP32 credentials are invalid.');
    }
    await _storage.write(key: _keyName, value: credentials.keyHex.trim().toLowerCase());
    await _storage.write(key: _tokenName, value: credentials.token.trim());
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _keyName);
    await _storage.delete(key: _tokenName);
  }
}

class MemoryEsp32CredentialsStore implements Esp32CredentialsStore {
  MemoryEsp32CredentialsStore([this.value]);
  Esp32Credentials? value;

  @override
  Future<Esp32Credentials?> read() async => value;

  @override
  Future<void> write(Esp32Credentials credentials) async {
    if (!credentials.isConfigured) throw const FormatException('ESP32 credentials are invalid.');
    value = credentials;
  }

  @override
  Future<void> clear() async => value = null;
}
