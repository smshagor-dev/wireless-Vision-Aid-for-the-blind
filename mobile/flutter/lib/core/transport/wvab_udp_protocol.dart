import 'dart:convert';
import 'dart:typed_data';

const wvabUdpHeaderSize = 14;
const wvabUdpNonceSize = 12;
const wvabUdpTagSize = 16;
const wvabUdpMaxPayload = 1450;
const wvabUdpAuthFrameId = 0xFFFFFFFF;
const wvabUdpMaxDataFrameId = 0xFFFFFFFE;
const wvabUdpMaxFrameChunks = 1024;
const wvabUdpMaxFrameBytes = 2 * 1024 * 1024;
const wvabUdpAuthPayloadVersion = 2;
const wvabUdpAuthPrefixSize = 13;

class WvabUdpHeader {
  const WvabUdpHeader({
    required this.sessionId,
    required this.frameId,
    required this.totalChunks,
    required this.chunkIndex,
    required this.payloadSize,
  });

  final int sessionId;
  final int frameId;
  final int totalChunks;
  final int chunkIndex;
  final int payloadSize;

  bool get isAuth => frameId == wvabUdpAuthFrameId;

  static WvabUdpHeader parse(Uint8List bytes) {
    if (bytes.length != wvabUdpHeaderSize) throw const FormatException('Invalid WVAB UDP header length.');
    final data = ByteData.sublistView(bytes);
    final header = WvabUdpHeader(
      sessionId: data.getUint32(0, Endian.big),
      frameId: data.getUint32(4, Endian.big),
      totalChunks: data.getUint16(8, Endian.big),
      chunkIndex: data.getUint16(10, Endian.big),
      payloadSize: data.getUint16(12, Endian.big),
    );
    if (header.sessionId == 0) throw const FormatException('WVAB session id must be non-zero.');
    return header;
  }

  Uint8List encode() {
    if (sessionId <= 0 || sessionId > 0xFFFFFFFF) throw const FormatException('Invalid WVAB session id.');
    final data = ByteData(wvabUdpHeaderSize)
      ..setUint32(0, sessionId, Endian.big)
      ..setUint32(4, frameId, Endian.big)
      ..setUint16(8, totalChunks, Endian.big)
      ..setUint16(10, chunkIndex, Endian.big)
      ..setUint16(12, payloadSize, Endian.big);
    return data.buffer.asUint8List();
  }

  bool validPacketShape(int packetSize) {
    if (isAuth) return totalChunks == 0 && chunkIndex == 0 && packetSize == wvabUdpHeaderSize + payloadSize;
    return totalChunks >= 1 &&
        totalChunks <= wvabUdpMaxFrameChunks &&
        chunkIndex >= 0 &&
        chunkIndex < totalChunks &&
        payloadSize > 0 &&
        packetSize == wvabUdpHeaderSize + payloadSize &&
        packetSize <= wvabUdpMaxPayload;
  }
}

class WvabAuthPayload {
  const WvabAuthPayload({required this.token, required this.authCounter, required this.nextFrameId});

  final String token;
  final int authCounter;
  final int nextFrameId;

  static WvabAuthPayload parse(Uint8List bytes) {
    if (bytes.length <= wvabUdpAuthPrefixSize) throw const FormatException('WVAB auth payload is too short.');
    final data = ByteData.sublistView(bytes);
    final version = data.getUint8(0);
    if (version != wvabUdpAuthPayloadVersion) throw const FormatException('Unsupported WVAB auth version.');
    final authCounter = data.getUint64(1, Endian.big);
    final nextFrameId = data.getUint32(9, Endian.big);
    if (authCounter <= 0) throw const FormatException('Invalid WVAB auth counter.');
    if (nextFrameId > wvabUdpMaxDataFrameId) throw const FormatException('Invalid WVAB next frame id.');
    final token = utf8.decode(bytes.sublist(wvabUdpAuthPrefixSize), allowMalformed: false).trim();
    if (token.isEmpty) throw const FormatException('WVAB auth token is empty.');
    return WvabAuthPayload(token: token, authCounter: authCounter, nextFrameId: nextFrameId);
  }
}

Uint8List deriveWvabNonce(Uint8List baseNonce, int chunkIndex) {
  if (baseNonce.length != wvabUdpNonceSize) throw const FormatException('Invalid WVAB base nonce length.');
  final nonce = Uint8List.fromList(baseNonce);
  final data = ByteData.sublistView(nonce);
  final counter = data.getUint32(8, Endian.big);
  data.setUint32(8, (counter + chunkIndex) & 0xFFFFFFFF, Endian.big);
  return nonce;
}

bool wvabFrameIdIsNewer(int candidate, int? previous) {
  if (previous == null) return true;
  final delta = (candidate - previous) & 0xFFFFFFFF;
  return delta > 0 && delta < 0x80000000;
}

int previousWvabFrameId(int nextFrameId) {
  if (nextFrameId < 0 || nextFrameId > wvabUdpMaxDataFrameId) {
    throw const FormatException('WVAB next frame id is outside data range.');
  }
  return nextFrameId == 0 ? wvabUdpMaxDataFrameId : nextFrameId - 1;
}
