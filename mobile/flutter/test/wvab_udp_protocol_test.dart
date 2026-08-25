import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/transport/wvab_udp_protocol.dart';

void main() {
  test('WVAB UDP header round-trips in network byte order', () {
    const header = WvabUdpHeader(
      sessionId: 0x01020304,
      frameId: 0x05060708,
      totalChunks: 3,
      chunkIndex: 1,
      payloadSize: 1200,
    );
    final encoded = header.encode();
    expect(encoded, hasLength(14));
    expect(encoded.sublist(0, 4), [1, 2, 3, 4]);
    final parsed = WvabUdpHeader.parse(encoded);
    expect(parsed.sessionId, header.sessionId);
    expect(parsed.frameId, header.frameId);
    expect(parsed.totalChunks, 3);
    expect(parsed.chunkIndex, 1);
    expect(parsed.payloadSize, 1200);
  });

  test('nonce derivation increments the final big-endian uint32', () {
    final base = Uint8List.fromList([0, 1, 2, 3, 4, 5, 6, 7, 0, 0, 0, 0xFE]);
    final derived = deriveWvabNonce(base, 3);
    expect(derived.sublist(0, 8), base.sublist(0, 8));
    expect(derived.sublist(8), [0, 0, 1, 1]);
    expect(base.sublist(8), [0, 0, 0, 0xFE]);
  });

  test('protocol-v2 auth payload parses and legacy payload is rejected', () {
    final token = utf8.encode('0123456789abcdef');
    final data = ByteData(wvabUdpAuthPrefixSize + token.length)
      ..setUint8(0, 2)
      ..setUint64(1, 7, Endian.big)
      ..setUint32(9, 12, Endian.big);
    final bytes = data.buffer.asUint8List();
    bytes.setRange(wvabUdpAuthPrefixSize, bytes.length, token);
    final auth = WvabAuthPayload.parse(bytes);
    expect(auth.authCounter, 7);
    expect(auth.nextFrameId, 12);
    expect(auth.token, '0123456789abcdef');
    expect(() => WvabAuthPayload.parse(Uint8List.fromList(token)), throwsFormatException);
  });

  test('frame ordering handles wrap from max data frame id to zero', () {
    expect(wvabFrameIdIsNewer(0, wvabUdpMaxDataFrameId), isTrue);
    expect(wvabFrameIdIsNewer(wvabUdpMaxDataFrameId, 0), isFalse);
    expect(previousWvabFrameId(0), wvabUdpMaxDataFrameId);
  });
}
