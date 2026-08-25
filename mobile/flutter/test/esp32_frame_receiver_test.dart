import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/services/esp32_credentials_store.dart';
import 'package:wvab_mobile/core/transport/esp32_frame_receiver.dart';
import 'package:wvab_mobile/core/transport/udp_replay_store.dart';
import 'package:wvab_mobile/core/transport/wvab_udp_protocol.dart';

const _keyHex = '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f';
const _token = 'wvab-mobile-test-token-2026';

List<int> _hexDecode(String value) => List<int>.generate(
      value.length ~/ 2,
      (index) => int.parse(value.substring(index * 2, index * 2 + 2), radix: 16),
    );

Uint8List _concat(Iterable<List<int>> parts) {
  final length = parts.fold<int>(0, (sum, part) => sum + part.length);
  final output = Uint8List(length);
  var offset = 0;
  for (final part in parts) {
    output.setRange(offset, offset + part.length, part);
    offset += part.length;
  }
  return output;
}

Uint8List _authCleartext({required int counter, required int nextFrameId}) {
  final tokenBytes = utf8.encode(_token);
  final bytes = Uint8List(wvabUdpAuthPrefixSize + tokenBytes.length);
  ByteData.sublistView(bytes)
    ..setUint8(0, wvabUdpAuthPayloadVersion)
    ..setUint64(1, counter, Endian.big)
    ..setUint32(9, nextFrameId, Endian.big);
  bytes.setRange(wvabUdpAuthPrefixSize, bytes.length, tokenBytes);
  return bytes;
}

Future<Uint8List> _encryptedPacket({
  required int sessionId,
  required int frameId,
  required int totalChunks,
  required int chunkIndex,
  required Uint8List cleartext,
  required Uint8List baseNonce,
}) async {
  final payloadSize = wvabUdpNonceSize + wvabUdpTagSize + cleartext.length;
  final header = WvabUdpHeader(
    sessionId: sessionId,
    frameId: frameId,
    totalChunks: totalChunks,
    chunkIndex: chunkIndex,
    payloadSize: payloadSize,
  ).encode();
  final algorithm = AesGcm.with256bits();
  final box = await algorithm.encrypt(
    cleartext,
    secretKey: SecretKey(_hexDecode(_keyHex)),
    nonce: deriveWvabNonce(baseNonce, chunkIndex),
    aad: header,
  );
  return _concat([header, baseNonce, box.mac.bytes, box.cipherText]);
}

Future<int> _freeUdpPort() async {
  final socket = await RawDatagramSocket.bind(InternetAddress.loopbackIPv4, 0);
  final port = socket.port;
  socket.close();
  await Future<void>.delayed(const Duration(milliseconds: 10));
  return port;
}

void main() {
  test('encrypted ESP32 auth and out-of-order chunks reassemble locally', () async {
    final port = await _freeUdpPort();
    final replay = MemoryUdpReplayStore();
    final receiver = Esp32FrameReceiver(
      credentials: const Esp32Credentials(keyHex: _keyHex, token: _token),
      port: port,
      replayStore: replay,
    );
    final sender = await RawDatagramSocket.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() async {
      sender.close();
      await receiver.dispose();
    });

    await receiver.start();
    final authFuture = receiver.stats.firstWhere((stats) => stats.authenticated).timeout(const Duration(seconds: 2));
    final auth = await _encryptedPacket(
      sessionId: 11,
      frameId: wvabUdpAuthFrameId,
      totalChunks: 0,
      chunkIndex: 0,
      cleartext: _authCleartext(counter: 1, nextFrameId: 0),
      baseNonce: Uint8List.fromList(List<int>.generate(12, (index) => index + 1)),
    );
    sender.send(auth, InternetAddress.loopbackIPv4, port);
    await authFuture;

    final original = Uint8List.fromList(List<int>.generate(120, (index) => index & 0xff));
    final chunks = [
      Uint8List.fromList(original.sublist(0, 55)),
      Uint8List.fromList(original.sublist(55)),
    ];
    final frameNonce = Uint8List.fromList(List<int>.generate(12, (index) => 20 + index));
    final packets = <Uint8List>[];
    for (var index = 0; index < chunks.length; index++) {
      packets.add(await _encryptedPacket(
        sessionId: 11,
        frameId: 0,
        totalChunks: chunks.length,
        chunkIndex: index,
        cleartext: chunks[index],
        baseNonce: frameNonce,
      ));
    }

    final frameFuture = receiver.frames.first.timeout(const Duration(seconds: 2));
    sender.send(packets[1], InternetAddress.loopbackIPv4, port);
    sender.send(packets[0], InternetAddress.loopbackIPv4, port);
    final received = await frameFuture;
    expect(received, orderedEquals(original));
  });

  test('fresh ESP32 session starts at frame zero without inheriting old baseline', () async {
    final port = await _freeUdpPort();
    final receiver = Esp32FrameReceiver(
      credentials: const Esp32Credentials(keyHex: _keyHex, token: _token),
      port: port,
      replayStore: MemoryUdpReplayStore(),
    );
    final sender = await RawDatagramSocket.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() async {
      sender.close();
      await receiver.dispose();
    });
    await receiver.start();

    Future<void> authenticate(int sessionId, int nonceOffset) async {
      final ready = receiver.stats.firstWhere((stats) => stats.authenticated).timeout(const Duration(seconds: 2));
      final packet = await _encryptedPacket(
        sessionId: sessionId,
        frameId: wvabUdpAuthFrameId,
        totalChunks: 0,
        chunkIndex: 0,
        cleartext: _authCleartext(counter: 1, nextFrameId: 0),
        baseNonce: Uint8List.fromList(List<int>.generate(12, (index) => nonceOffset + index)),
      );
      sender.send(packet, InternetAddress.loopbackIPv4, port);
      await ready;
    }

    Future<Uint8List> sendFrame(int sessionId, int nonceOffset, int marker) async {
      final expected = Uint8List.fromList([0xff, 0xd8, marker, 0xff, 0xd9]);
      final packet = await _encryptedPacket(
        sessionId: sessionId,
        frameId: 0,
        totalChunks: 1,
        chunkIndex: 0,
        cleartext: expected,
        baseNonce: Uint8List.fromList(List<int>.generate(12, (index) => nonceOffset + index)),
      );
      final future = receiver.frames.first.timeout(const Duration(seconds: 2));
      sender.send(packet, InternetAddress.loopbackIPv4, port);
      expect(await future, orderedEquals(expected));
      return expected;
    }

    await authenticate(1001, 40);
    await sendFrame(1001, 60, 1);
    await authenticate(2002, 80);
    await sendFrame(2002, 100, 2);
  });

  test('replay store rejects equal and lower authentication counters', () async {
    final store = MemoryUdpReplayStore();
    expect(await store.recordIfFresh(sessionId: 55, authCounter: 2, nextFrameId: 0), isTrue);
    expect(await store.recordIfFresh(sessionId: 55, authCounter: 2, nextFrameId: 0), isFalse);
    expect(await store.recordIfFresh(sessionId: 55, authCounter: 1, nextFrameId: 0), isFalse);
    expect(await store.recordIfFresh(sessionId: 55, authCounter: 3, nextFrameId: 1), isTrue);
  });
}
