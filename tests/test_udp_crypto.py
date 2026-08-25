from collections import OrderedDict
import time

import pytest
from Crypto.Cipher import AES

from core.udp_protocol import AUTH_FRAME_ID, NONCE_SIZE, TAG_SIZE, pack_header
from core.udp_runtime import UDPVisionServer, _derive_nonce


KEY = bytes(range(32))
TOKEN = "wvab-test-token-1234567890"
ADDR = ("192.168.4.2", 9999)


def _encrypt(header: bytes, plaintext: bytes, base_nonce: bytes) -> bytes:
    cipher = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    cipher.update(header)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return base_nonce + tag + ciphertext


def _bare_server():
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
    return server


def test_authenticated_session_accepts_valid_aes_gcm_packet_once():
    server = _bare_server()
    session_id = 101
    base_nonce = bytes(range(NONCE_SIZE))
    payload_size = NONCE_SIZE + TAG_SIZE + len(TOKEN.encode())
    header = pack_header(session_id, AUTH_FRAME_ID, 0, 0, payload_size)
    payload = _encrypt(header, TOKEN.encode(), base_nonce)

    assert server._handle_auth(session_id, header, payload, ADDR)
    assert server.sessions[ADDR]["session_id"] == session_id

    # Exact auth datagram replay is rejected by the nonce replay cache.
    assert not server._handle_auth(session_id, header, payload, ADDR)


def test_gcm_rejects_authenticated_header_tampering():
    session_id = 202
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
    original = pack_header(303, 9, 1, 0, payload_size)

    cipher = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    cipher.update(original)
    ciphertext, tag = cipher.encrypt_and_digest(b"frame")

    tampered = pack_header(304, 9, 1, 0, payload_size)
    verifier = AES.new(KEY, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
    verifier.update(tampered)
    with pytest.raises(ValueError):
        verifier.decrypt_and_verify(ciphertext, tag)
