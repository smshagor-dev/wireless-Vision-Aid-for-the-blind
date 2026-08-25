#!/usr/bin/env python3
"""Compatibility entrypoint for the WVAB secure UDP runtime.

This wrapper applies the canonical mobility-class policy and protocol-v2
restart replay protection while ``core.udp_runtime`` owns the shared transport,
watchdog, restart, and frame-processing implementation.
"""

import os
import time

from core import udp_runtime as _runtime
from core.object_policy import CriticalObjectPolicy, label_candidates
from core.security import verify_secret
from core.udp_auth_state import (
    MAX_AUTH_COUNTER,
    ReplayStateStore,
    decode_auth_payload,
    encode_auth_payload,
    previous_frame_id,
)
from core.udp_protocol import (
    AUTH_FRAME_ID,
    HEADER_SIZE,
    MAX_DATA_FRAME_ID,
    NONCE_SIZE,
    TAG_SIZE,
    frame_id_is_newer,
    pack_header,
    unpack_header,
)


SimpleTracker = _runtime.SimpleTracker
_build_parser = _runtime._build_parser
_derive_nonce = _runtime._derive_nonce
_new_session_id = _runtime._new_session_id
_secure_transport_settings = _runtime._secure_transport_settings


class UDPVisionServer(_runtime.UDPVisionServer):
    """Secure UDP server with mobility policy and persistent auth replay state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.critical_objects = CriticalObjectPolicy()
        replay_path = os.environ.get(
            "WVAB_UDP_REPLAY_STATE_PATH",
            "state/udp_replay_state.json",
        ).strip()
        if not replay_path:
            raise RuntimeError("WVAB_UDP_REPLAY_STATE_PATH must not be empty")
        replay_limit = int(os.environ.get("WVAB_UDP_REPLAY_MAX_SESSIONS", "4096"))
        self.replay_state = ReplayStateStore(replay_path, max_sessions=replay_limit)
        self.logger.info("Persistent UDP replay state: %s", replay_path)

    def _translate(self, class_name, language=None):
        language = language or self.language
        for candidate in label_candidates(class_name):
            entry = self.multilingual_labels.get(candidate)
            if isinstance(entry, dict):
                return entry.get(language, entry.get("en", candidate.replace("_", " ")))
        return str(class_name or "object").replace("_", " ")

    def _handle_auth(self, session_id: int, header: bytes, payload: bytes, addr) -> bool:
        if not self.require_auth:
            return self._bind_session(addr, session_id, time.monotonic())

        try:
            if self.encrypt_udp:
                if len(payload) <= NONCE_SIZE + TAG_SIZE:
                    return False
                base_nonce = payload[:NONCE_SIZE]
                if base_nonce in self.seen_auth_nonces:
                    return False
                tag = payload[NONCE_SIZE : NONCE_SIZE + TAG_SIZE]
                ciphertext = payload[NONCE_SIZE + TAG_SIZE :]
                cipher = self.AES.new(
                    self.udp_key,
                    self.AES.MODE_GCM,
                    nonce=_runtime._derive_nonce(base_nonce, 0),
                )
                cipher.update(header)
                cleartext = cipher.decrypt_and_verify(ciphertext, tag)
            else:
                base_nonce = None
                cleartext = payload
            token, auth_counter, next_frame_id = decode_auth_payload(cleartext)
        except Exception:
            return False

        if not verify_secret(token, self.auth_token):
            return False
        if (addr, session_id) in self.retired_sessions:
            return False

        replay_key = (addr, session_id)
        baseline = previous_frame_id(next_frame_id)
        current_frame = self.last_completed_frame.get(replay_key)

        # Persist the monotonic authentication counter before granting/renewing
        # the session. A server/process restart therefore does not make an old
        # captured authentication datagram valid again.
        try:
            if not self.replay_state.record_if_fresh(
                session_id,
                auth_counter,
                next_frame_id,
            ):
                return False
        except Exception as exc:
            self.logger.error("Persistent UDP replay-state update failed: %s", exc)
            return False

        # A delayed refresh may arrive after newer frames. Record its auth
        # counter above so it cannot be replayed later, but never move the
        # in-memory completed-frame baseline backwards.
        if (
            current_frame is not None
            and baseline != current_frame
            and not frame_id_is_newer(baseline, current_frame)
        ):
            return False

        now = time.monotonic()
        if not self._bind_session(addr, session_id, now):
            return False
        if current_frame is None or frame_id_is_newer(baseline, current_frame):
            self.last_completed_frame[replay_key] = baseline
        elif baseline == current_frame:
            self.last_completed_frame[replay_key] = current_frame

        if base_nonce is not None:
            self._remember_bounded(
                self.seen_auth_nonces,
                base_nonce,
                _runtime.MAX_AUTH_NONCES,
            )
        self.last_valid_packet_mono = now
        return True


class UDPCameraClient(_runtime.UDPCameraClient):
    """Python sender using protocol-v2 auth counters and frame baselines."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_counter = 0
        self.next_frame_id = 0

    def _send_packet(self, packet: bytes):
        header_fields = None
        if len(packet) >= HEADER_SIZE:
            try:
                header_fields = unpack_header(packet[:HEADER_SIZE])
            except ValueError:
                header_fields = None
        super()._send_packet(packet)
        if header_fields is None:
            return
        _session_id, frame_id, total_chunks, chunk_index, _payload_size = header_fields
        if (
            frame_id != AUTH_FRAME_ID
            and total_chunks > 0
            and chunk_index == total_chunks - 1
        ):
            self.next_frame_id = 0 if frame_id >= MAX_DATA_FRAME_ID else frame_id + 1

    def _send_auth(self):
        if not self.require_auth:
            self.force_auth = False
            return
        if self.auth_counter >= MAX_AUTH_COUNTER:
            raise RuntimeError("authentication counter exhausted; start a fresh sender session")
        self.auth_counter += 1
        cleartext = encode_auth_payload(
            self.auth_token,
            self.auth_counter,
            self.next_frame_id,
        )
        if self.encrypt_udp:
            base_nonce = self.get_random_bytes(NONCE_SIZE)
            payload_size = NONCE_SIZE + TAG_SIZE + len(cleartext)
            header = pack_header(self.session_id, AUTH_FRAME_ID, 0, 0, payload_size)
            cipher = self.AES.new(
                self.udp_key,
                self.AES.MODE_GCM,
                nonce=_runtime._derive_nonce(base_nonce, 0),
            )
            cipher.update(header)
            ciphertext, tag = cipher.encrypt_and_digest(cleartext)
            payload = base_nonce + tag + ciphertext
        else:
            payload = cleartext
            header = pack_header(self.session_id, AUTH_FRAME_ID, 0, 0, len(payload))
        self._send_packet(header + payload)
        self.force_auth = False


def main():
    # core.udp_runtime owns parsing/restart/session orchestration. Supply both
    # protocol-v2 subclasses so source-checkout, systemd, Docker, and main.py
    # launch paths use the same security behavior.
    original_server = _runtime.UDPVisionServer
    original_client = _runtime.UDPCameraClient
    _runtime.UDPVisionServer = UDPVisionServer
    _runtime.UDPCameraClient = UDPCameraClient
    try:
        return _runtime.main()
    finally:
        _runtime.UDPVisionServer = original_server
        _runtime.UDPCameraClient = original_client


__all__ = [
    "SimpleTracker",
    "UDPCameraClient",
    "UDPVisionServer",
    "_build_parser",
    "_derive_nonce",
    "_new_session_id",
    "_secure_transport_settings",
    "main",
]


if __name__ == "__main__":
    main()
