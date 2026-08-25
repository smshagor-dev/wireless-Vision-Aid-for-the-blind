import 'package:shared_preferences/shared_preferences.dart';

import 'wvab_udp_protocol.dart';

abstract class UdpReplayStore {
  Future<bool> recordIfFresh({required int sessionId, required int authCounter, required int nextFrameId});
}

void _validateReplayRecord({required int sessionId, required int authCounter, required int nextFrameId}) {
  if (sessionId <= 0 || sessionId > 0xFFFFFFFF) throw const FormatException('Invalid WVAB session id.');
  if (authCounter <= 0) throw const FormatException('Invalid WVAB auth counter.');
  if (nextFrameId < 0 || nextFrameId > wvabUdpMaxDataFrameId) {
    throw const FormatException('Invalid WVAB next frame id.');
  }
}

class SharedPreferencesUdpReplayStore implements UdpReplayStore {
  SharedPreferencesUdpReplayStore({SharedPreferencesAsync? preferences, this.maxSessions = 512})
      : _preferences = preferences ?? SharedPreferencesAsync();

  static const _prefix = 'wvab.udp.replay.';
  static const _orderKey = '${_prefix}order';
  static const _counterPrefix = '${_prefix}counter.';
  static const _nextPrefix = '${_prefix}next.';
  final SharedPreferencesAsync _preferences;
  final int maxSessions;

  @override
  Future<bool> recordIfFresh({required int sessionId, required int authCounter, required int nextFrameId}) async {
    _validateReplayRecord(sessionId: sessionId, authCounter: authCounter, nextFrameId: nextFrameId);

    final id = sessionId.toString();
    final existing = await _preferences.getString('$_counterPrefix$id');
    final previous = existing == null ? null : int.tryParse(existing);
    if (previous != null && authCounter <= previous) return false;

    // Persist counter before granting the sender session. Decimal strings avoid
    // platform integer-width differences for uint64 authentication counters.
    await _preferences.setString('$_counterPrefix$id', authCounter.toString());
    await _preferences.setInt('$_nextPrefix$id', nextFrameId);

    final order = await _preferences.getStringList(_orderKey) ?? <String>[];
    order.remove(id);
    order.add(id);
    while (order.length > maxSessions) {
      final evicted = order.removeAt(0);
      await _preferences.remove('$_counterPrefix$evicted');
      await _preferences.remove('$_nextPrefix$evicted');
    }
    await _preferences.setStringList(_orderKey, order);
    return true;
  }
}

class MemoryUdpReplayStore implements UdpReplayStore {
  final Map<int, int> _counters = {};

  @override
  Future<bool> recordIfFresh({required int sessionId, required int authCounter, required int nextFrameId}) async {
    _validateReplayRecord(sessionId: sessionId, authCounter: authCounter, nextFrameId: nextFrameId);
    final previous = _counters[sessionId];
    if (previous != null && authCounter <= previous) return false;
    _counters[sessionId] = authCounter;
    return true;
  }
}
