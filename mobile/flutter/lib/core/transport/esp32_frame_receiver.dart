import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

import '../services/esp32_credentials_store.dart';
import 'udp_replay_store.dart';
import 'wvab_udp_protocol.dart';

class Esp32ReceiverStats {
  const Esp32ReceiverStats({this.authenticated = false, this.completedFrames = 0, this.lastFrameAt});

  final bool authenticated;
  final int completedFrames;
  final DateTime? lastFrameAt;
}

class Esp32FrameReceiver {
  Esp32FrameReceiver({
    required this.credentials,
    required this.port,
    required this.replayStore,
    this.authTtl = const Duration(seconds: 120),
  });

  final Esp32Credentials credentials;
  final int port;
  final UdpReplayStore replayStore;
  final Duration authTtl;

  final _frames = StreamController<Uint8List>.broadcast();
  final _stats = StreamController<Esp32ReceiverStats>.broadcast();
  final Map<String, _FrameBuffer> _inflight = {};
  final List<String> _inflightOrder = [];
  final Set<String> _seenAuthNonces = {};
  final List<String> _authNonceOrder = [];
  RawDatagramSocket? _socket;
  SecretKey? _secretKey;
  InternetAddress? _authorizedAddress;
  int? _authorizedPort;
  int? _authorizedSessionId;
  DateTime? _authorizedUntil;
  int? _lastCompletedFrameId;
  int _completedFrames = 0;
  DateTime? _lastFrameAt;

  Stream<Uint8List> get frames => _frames.stream;
  Stream<Esp32ReceiverStats> get stats => _stats.stream;
  bool get isRunning => _socket != null;

  Future<void> start() async {
    if (isRunning) return;
    if (!credentials.isConfigured) throw const FormatException('ESP32 credentials are not configured.');
    if (port < 1 || port > 65535) throw const FormatException('ESP32 UDP port must be in 1..65535.');
    _secretKey = SecretKey(_hexDecode(credentials.keyHex));
    final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, port, reuseAddress: false);
    socket.readEventsEnabled = true;
    _socket = socket;
    socket.listen(
      (event) {
        if (event == RawSocketEvent.read) {
          Datagram? datagram;
          while ((datagram = socket.receive()) != null) {
            unawaited(_handleDatagram(datagram!));
          }
        }
      },
      onError: (_) => unawaited(stop()),
      onDone: () => unawaited(stop()),
      cancelOnError: false,
    );
  }

  Future<void> stop() async {
    _socket?.close();
    _socket = null;
    _secretKey?.destroy();
    _secretKey = null;
    _authorizedAddress = null;
    _authorizedPort = null;
    _authorizedSessionId = null;
    _authorizedUntil = null;
    _lastCompletedFrameId = null;
    _inflight.clear();
    _inflightOrder.clear();
    _completedFrames = 0;
    _lastFrameAt = null;
    _emitStats(false);
  }

  Future<void> dispose() async {
    await stop();
    await _frames.close();
    await _stats.close();
  }

  Future<void> _handleDatagram(Datagram datagram) async {
    final packet = datagram.data;
    if (packet.length < wvabUdpHeaderSize || packet.length > wvabUdpMaxPayload) return;
    late final WvabUdpHeader header;
    try {
      header = WvabUdpHeader.parse(Uint8List.sublistView(packet, 0, wvabUdpHeaderSize));
    } on FormatException {
      return;
    }
    if (!header.validPacketShape(packet.length)) return;
    final headerBytes = Uint8List.sublistView(packet, 0, wvabUdpHeaderSize);
    final payload = Uint8List.sublistView(packet, wvabUdpHeaderSize);
    if (header.isAuth) {
      await _handleAuth(header, headerBytes, payload, datagram.address, datagram.port);
      return;
    }
    if (!_sessionAuthorized(datagram.address, datagram.port, header.sessionId)) return;
    if (!wvabFrameIdIsNewer(header.frameId, _lastCompletedFrameId)) return;

    Uint8List cleartext;
    try {
      cleartext = await _decryptPayload(headerBytes, payload, header.chunkIndex);
    } catch (_) {
      return;
    }
    final key = '${datagram.address.address}:${datagram.port}:${header.sessionId}:${header.frameId}';
    var buffer = _inflight[key];
    if (buffer == null) {
      _evictExpiredFrames();
      while (_inflight.length >= 8 && _inflightOrder.isNotEmpty) {
        _inflight.remove(_inflightOrder.removeAt(0));
      }
      buffer = _FrameBuffer(totalChunks: header.totalChunks);
      _inflight[key] = buffer;
      _inflightOrder.add(key);
    } else if (buffer.totalChunks != header.totalChunks) {
      _removeFrame(key);
      return;
    }
    if (!buffer.add(header.chunkIndex, cleartext)) {
      _removeFrame(key);
      return;
    }
    if (!buffer.complete) return;
    final frame = buffer.join();
    _removeFrame(key);
    if (frame.length > wvabUdpMaxFrameBytes) return;
    _lastCompletedFrameId = header.frameId;
    _completedFrames++;
    _lastFrameAt = DateTime.now();
    _frames.add(frame);
    _emitStats(true);
  }

  Future<void> _handleAuth(
    WvabUdpHeader header,
    Uint8List headerBytes,
    Uint8List payload,
    InternetAddress address,
    int sourcePort,
  ) async {
    if (payload.length <= wvabUdpNonceSize + wvabUdpTagSize) return;
    final nonceId = base64Url.encode(payload.sublist(0, wvabUdpNonceSize));
    if (_seenAuthNonces.contains(nonceId)) return;
    Uint8List cleartext;
    try {
      cleartext = await _decryptPayload(headerBytes, payload, 0);
    } catch (_) {
      return;
    }
    late final WvabAuthPayload auth;
    try {
      auth = WvabAuthPayload.parse(cleartext);
    } on FormatException {
      return;
    }
    if (!_constantTimeEquals(utf8.encode(auth.token), utf8.encode(credentials.token.trim()))) return;
    final accepted = await replayStore.recordIfFresh(
      sessionId: header.sessionId,
      authCounter: auth.authCounter,
      nextFrameId: auth.nextFrameId,
    );
    if (!accepted) return;

    final baseline = previousWvabFrameId(auth.nextFrameId);
    final sameSession = _authorizedAddress?.address == address.address &&
        _authorizedPort == sourcePort &&
        _authorizedSessionId == header.sessionId;
    if (sameSession &&
        _lastCompletedFrameId != null &&
        baseline != _lastCompletedFrameId &&
        !wvabFrameIdIsNewer(baseline, _lastCompletedFrameId)) {
      return;
    }

    if (!sameSession) {
      _inflight.clear();
      _inflightOrder.clear();
      _lastCompletedFrameId = null;
    }
    _authorizedAddress = address;
    _authorizedPort = sourcePort;
    _authorizedSessionId = header.sessionId;
    _authorizedUntil = DateTime.now().add(authTtl);
    if (_lastCompletedFrameId == null || wvabFrameIdIsNewer(baseline, _lastCompletedFrameId)) {
      _lastCompletedFrameId = baseline;
    }
    _rememberAuthNonce(nonceId);
    _emitStats(true);
  }

  Future<Uint8List> _decryptPayload(Uint8List header, Uint8List payload, int chunkIndex) async {
    if (payload.length <= wvabUdpNonceSize + wvabUdpTagSize) {
      throw const FormatException('Encrypted packet too short.');
    }
    final key = _secretKey;
    if (key == null) throw StateError('ESP32 receiver key is unavailable.');
    final baseNonce = Uint8List.fromList(payload.sublist(0, wvabUdpNonceSize));
    final tag = payload.sublist(wvabUdpNonceSize, wvabUdpNonceSize + wvabUdpTagSize);
    final ciphertext = payload.sublist(wvabUdpNonceSize + wvabUdpTagSize);
    final algorithm = switch (credentials.keyHex.trim().length ~/ 2) {
      16 => AesGcm.with128bits(),
      24 => AesGcm.with192bits(),
      32 => AesGcm.with256bits(),
      _ => throw const FormatException('Unsupported AES key size.'),
    };
    final clear = await algorithm.decrypt(
      SecretBox(ciphertext, nonce: deriveWvabNonce(baseNonce, chunkIndex), mac: Mac(tag)),
      secretKey: key,
      aad: header,
    );
    return Uint8List.fromList(clear);
  }

  bool _sessionAuthorized(InternetAddress address, int sourcePort, int sessionId) {
    final until = _authorizedUntil;
    if (until == null || DateTime.now().isAfter(until)) return false;
    return _authorizedAddress?.address == address.address &&
        _authorizedPort == sourcePort &&
        _authorizedSessionId == sessionId;
  }

  void _rememberAuthNonce(String nonce) {
    _seenAuthNonces.add(nonce);
    _authNonceOrder.add(nonce);
    while (_authNonceOrder.length > 4096) {
      _seenAuthNonces.remove(_authNonceOrder.removeAt(0));
    }
  }

  void _evictExpiredFrames() {
    final cutoff = DateTime.now().subtract(const Duration(seconds: 2));
    for (final key in List<String>.from(_inflightOrder)) {
      final buffer = _inflight[key];
      if (buffer != null && buffer.createdAt.isBefore(cutoff)) _removeFrame(key);
    }
  }

  void _removeFrame(String key) {
    _inflight.remove(key);
    _inflightOrder.remove(key);
  }

  void _emitStats(bool authenticated) {
    if (_stats.isClosed) return;
    _stats.add(Esp32ReceiverStats(
      authenticated: authenticated && _authorizedUntil != null && DateTime.now().isBefore(_authorizedUntil!),
      completedFrames: _completedFrames,
      lastFrameAt: _lastFrameAt,
    ));
  }

  List<int> _hexDecode(String value) {
    final clean = value.trim();
    if (!RegExp(r'^[0-9a-fA-F]+$').hasMatch(clean) || !clean.length.isEven) {
      throw const FormatException('AES key must be hexadecimal.');
    }
    return List<int>.generate(
      clean.length ~/ 2,
      (i) => int.parse(clean.substring(i * 2, i * 2 + 2), radix: 16),
    );
  }

  bool _constantTimeEquals(List<int> a, List<int> b) {
    var difference = a.length ^ b.length;
    final length = a.length > b.length ? a.length : b.length;
    for (var i = 0; i < length; i++) {
      difference |= (i < a.length ? a[i] : 0) ^ (i < b.length ? b[i] : 0);
    }
    return difference == 0;
  }
}

class _FrameBuffer {
  _FrameBuffer({required this.totalChunks}) : chunks = List<Uint8List?>.filled(totalChunks, null);

  final int totalChunks;
  final List<Uint8List?> chunks;
  final DateTime createdAt = DateTime.now();
  int bytes = 0;

  bool add(int index, Uint8List chunk) {
    if (index < 0 || index >= totalChunks) return false;
    final existing = chunks[index];
    if (existing != null) return _bytesEqual(existing, chunk);
    if (bytes + chunk.length > wvabUdpMaxFrameBytes) return false;
    chunks[index] = Uint8List.fromList(chunk);
    bytes += chunk.length;
    return true;
  }

  bool get complete => chunks.every((chunk) => chunk != null);

  Uint8List join() {
    if (!complete) throw StateError('WVAB frame is incomplete.');
    final output = Uint8List(bytes);
    var offset = 0;
    for (final chunk in chunks) {
      output.setRange(offset, offset + chunk!.length, chunk);
      offset += chunk.length;
    }
    return output;
  }

  bool _bytesEqual(Uint8List a, Uint8List b) {
    if (a.length != b.length) return false;
    var diff = 0;
    for (var i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
    return diff == 0;
  }
}
