"""Pure helpers and bounds for the WVAB secure UDP transport."""

from __future__ import annotations

import struct


MAX_UDP_PAYLOAD = 1450
# session_id, frame_id, total_chunks, chunk_index, payload_size
HEADER_FORMAT = "!IIHHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
NONCE_SIZE = 12
TAG_SIZE = 16
AUTH_FRAME_ID = 0xFFFFFFFF
MAX_DATA_FRAME_ID = AUTH_FRAME_ID - 1
MAX_SESSION_ID = 0xFFFFFFFF
MAX_FRAME_CHUNKS = 1024
MAX_FRAME_BYTES = 2 * 1024 * 1024
MAX_INFLIGHT_FRAMES_PER_CLIENT = 8


def valid_session_id(session_id: int) -> bool:
    return 1 <= int(session_id) <= MAX_SESSION_ID


def pack_header(
    session_id: int,
    frame_id: int,
    total_chunks: int,
    chunk_index: int,
    payload_size: int,
) -> bytes:
    if not valid_session_id(session_id):
        raise ValueError("session_id must be a non-zero uint32")
    return struct.pack(
        HEADER_FORMAT,
        int(session_id) & 0xFFFFFFFF,
        int(frame_id) & 0xFFFFFFFF,
        int(total_chunks) & 0xFFFF,
        int(chunk_index) & 0xFFFF,
        int(payload_size) & 0xFFFF,
    )


def unpack_header(header: bytes):
    if len(header) != HEADER_SIZE:
        raise ValueError("invalid UDP header length")
    values = struct.unpack(HEADER_FORMAT, header)
    if not valid_session_id(values[0]):
        raise ValueError("invalid UDP session id")
    return values


def frame_id_is_newer(candidate: int, previous: int | None) -> bool:
    """RFC1982-style uint32 serial comparison, excluding equality."""
    if previous is None:
        return True
    candidate = int(candidate) & 0xFFFFFFFF
    previous = int(previous) & 0xFFFFFFFF
    delta = (candidate - previous) & 0xFFFFFFFF
    return 0 < delta < 0x80000000


def valid_frame_shape(total_chunks: int, chunk_index: int, payload_size: int, packet_size: int) -> bool:
    if not 1 <= int(total_chunks) <= MAX_FRAME_CHUNKS:
        return False
    if not 0 <= int(chunk_index) < int(total_chunks):
        return False
    if int(payload_size) <= 0:
        return False
    if int(packet_size) != HEADER_SIZE + int(payload_size):
        return False
    if int(packet_size) > MAX_UDP_PAYLOAD:
        return False
    return True
