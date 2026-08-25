from collections import OrderedDict
import logging
import time

import pytest
from Crypto.Cipher import AES

from core.udp_auth_state import ReplayStateStore, encode_auth_payload
from core.udp_protocol import AUTH_FRAME_ID, NONCE_SIZE, TAG_SIZE, pack_header
from core.udp_runtime import _derive_nonce
from udp_streaming import UDPVisionServer


KEY = bytes(range(32))
TOKEN = "wvab-test-token-1234567890"
ADDR = ("192.168.4.2", 9999)


def _encrypt(header: bytes, plaintext: bytes, base_nonce: bytes) -> bytes:
    cipher = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    cipher.update(header)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return base_nonce + tag + ciphertext


def _bare_server(replay_path):
    server = UDPVisionServer.__new__(UDPVisionServer)
    server.require_auth = True
    server.encrypt_udp = True
    server.udp_key = KEY
    server.auth_token = TOKEN
    server.auth_ttl_s = 120.0
    server.AES = AES
    server.sessions = {}
    server.retired_sessions = OrderedDict()
    server.seen_auth_nonces = OrderedDict()
    server.last_completed_frame = {}
    server.last_valid_packet_mono = time.monotonic()
    server.replay_state = ReplayStateStore(replay_path)
    server.logger = logging.getLogger("wvab-test")
    return server


def _auth_packet(session_id, auth_counter, next_frame_id, base_nonce):
    cleartext = encode_auth_payload(TOKEN, auth_counter, next_frame_id)
    payload_size = NONCE_SIZE + TAG_SIZE + len(cleartext)
    header = pack_header(session_id, AUTH_FRAME_ID, 0, 0, payload_size)
    return header, _encrypt(header, cleartext, base_nonce)


def test_authenticated_session_accepts_valid_aes_gcm_packet_once(tmp_path):
    server = _bare_server(tmp_path / "replay.json")
    session_id = 101
    header, payload = _auth_packet(
        session_id,
        auth_counter=1,
        next_frame_id=50,
        base_nonce=bytes(range(NONCE_SIZE)),
    )

    assert server._handle_auth(session_id, header, payload, ADDR)
    assert server.sessions[ADDR]["session_id"] == session_id
    assert server.last_completed_frame[(ADDR, session_id)] == 49

    # Exact auth datagram replay is rejected in memory and persisted state.
    assert not server._handle_auth(session_id, header, payload, ADDR)


def test_auth_replay_stays_rejected_after_server_restart(tmp_path):
    replay_path = tmp_path / "replay.json"
    session_id = 202
    old_header, old_payload = _auth_packet(
        session_id,
        auth_counter=7,
        next_frame_id=120,
        base_nonce=b"abcdefghijkl",
    )

    first = _bare_server(replay_path)
    assert first._handle_auth(session_id, old_header, old_payload, ADDR)

    restarted = _bare_server(replay_path)
    assert not restarted._handle_auth(session_id, old_header, old_payload, ADDR)

    new_header, new_payload = _auth_packet(
        session_id,
        auth_counter=8,
        next_frame_id=150,
        base_nonce=b"mnopqrstuvwx",
    )
    assert restarted._handle_auth(session_id, new_header, new_payload, ADDR)
    assert restarted.last_completed_frame[(ADDR, session_id)] == 149


def test_gcm_rejects_authenticated_header_tampering():
    session_id = 303
    base_nonce = bytes(reversed(range(NONCE_SIZE)))
    payload_size = NONCE_SIZE + TAG_SIZE + 5
    header = pack_header(session_id, 7, 1, 0, payload_size)

    cipher = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    cipher.update(header)
    ciphertext, tag = cipher.encrypt_and_digest(b"frame")

    tampered_header = pack_header(session_id, 8, 1, 0, payload_size)
    verifier = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    verifier.update(tampered_header)
    with pytest.raises(ValueError):
        verifier.decrypt_and_verify(ciphertext, tag)


def test_gcm_rejects_session_id_tampering():
    base_nonce = b"abcdefghijkl"
    payload_size = NONCE_SIZE + TAG_SIZE + 5
    original = pack_header(404, 9, 1, 0, payload_size)

    cipher = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    cipher.update(original)
    ciphertext, tag = cipher.encrypt_and_digest(b"frame")

    tampered = pack_header(405, 9, 1, 0, payload_size)
    verifier = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    verifier.update(tampered)
    with pytest.raises(ValueError):
        verifier.decrypt_and_verify(ciphertext, tag)
