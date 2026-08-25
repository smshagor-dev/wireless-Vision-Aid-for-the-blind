"""Versioned UDP authentication payloads and persistent restart replay state."""

from __future__ import annotations

from collections import OrderedDict
import json
import os
from pathlib import Path
import struct
import tempfile

from core.udp_protocol import MAX_DATA_FRAME_ID


AUTH_PAYLOAD_VERSION = 2
AUTH_PAYLOAD_PREFIX = struct.Struct("!BQI")
MAX_AUTH_COUNTER = (1 << 64) - 1
DEFAULT_MAX_SESSIONS = 4096


def encode_auth_payload(token: str, auth_counter: int, next_frame_id: int) -> bytes:
    token_bytes = str(token).encode("utf-8")
    counter = int(auth_counter)
    next_id = int(next_frame_id)
    if not token_bytes:
        raise ValueError("authentication token must not be empty")
    if not 1 <= counter <= MAX_AUTH_COUNTER:
        raise ValueError("auth_counter must be in 1..2^64-1")
    if not 0 <= next_id <= MAX_DATA_FRAME_ID:
        raise ValueError("next_frame_id is outside the data-frame range")
    return AUTH_PAYLOAD_PREFIX.pack(AUTH_PAYLOAD_VERSION, counter, next_id) + token_bytes


def decode_auth_payload(payload: bytes) -> tuple[str, int, int]:
    if len(payload) <= AUTH_PAYLOAD_PREFIX.size:
        raise ValueError("authentication payload is too short")
    version, auth_counter, next_frame_id = AUTH_PAYLOAD_PREFIX.unpack(
        payload[: AUTH_PAYLOAD_PREFIX.size]
    )
    if version != AUTH_PAYLOAD_VERSION:
        raise ValueError("unsupported authentication payload version")
    if not 1 <= auth_counter <= MAX_AUTH_COUNTER:
        raise ValueError("invalid authentication counter")
    if not 0 <= next_frame_id <= MAX_DATA_FRAME_ID:
        raise ValueError("invalid next frame id")
    token = payload[AUTH_PAYLOAD_PREFIX.size :].decode("utf-8", "strict").strip()
    if not token:
        raise ValueError("authentication token is empty")
    return token, auth_counter, next_frame_id


def previous_frame_id(next_frame_id: int) -> int:
    next_id = int(next_frame_id)
    if not 0 <= next_id <= MAX_DATA_FRAME_ID:
        raise ValueError("next_frame_id is outside the data-frame range")
    return MAX_DATA_FRAME_ID if next_id == 0 else next_id - 1


class ReplayStateStore:
    """Persist the highest accepted auth counter for bounded sender sessions.

    The state contains no AES key or authentication token. Persistence is used
    so a captured authentication datagram cannot become valid again merely
    because the Python server process/container restarted.
    """

    def __init__(self, path: str | os.PathLike[str], max_sessions: int = DEFAULT_MAX_SESSIONS):
        self.path = Path(path)
        self.max_sessions = max(int(max_sessions), 1)
        self.sessions: OrderedDict[str, dict[str, int]] = OrderedDict()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"could not read UDP replay state: {self.path}") from exc
        if not isinstance(data, dict) or data.get("version") != 1:
            raise RuntimeError("unsupported or malformed UDP replay state")
        rows = data.get("sessions")
        if not isinstance(rows, list):
            raise RuntimeError("malformed UDP replay session list")
        for row in rows[-self.max_sessions :]:
            if not isinstance(row, dict):
                raise RuntimeError("malformed UDP replay session record")
            session_id = int(row.get("session_id"))
            auth_counter = int(row.get("auth_counter"))
            next_frame_id = int(row.get("next_frame_id"))
            if not 1 <= session_id <= 0xFFFFFFFF:
                raise RuntimeError("invalid persisted UDP session id")
            if not 1 <= auth_counter <= MAX_AUTH_COUNTER:
                raise RuntimeError("invalid persisted auth counter")
            if not 0 <= next_frame_id <= MAX_DATA_FRAME_ID:
                raise RuntimeError("invalid persisted next frame id")
            self.sessions[str(session_id)] = {
                "auth_counter": auth_counter,
                "next_frame_id": next_frame_id,
            }

    def _serialize(self) -> dict:
        return {
            "version": 1,
            "sessions": [
                {
                    "session_id": int(session_id),
                    "auth_counter": state["auth_counter"],
                    "next_frame_id": state["next_frame_id"],
                }
                for session_id, state in self.sessions.items()
            ],
        }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".tmp-",
            dir=str(self.path.parent),
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(self._serialize(), handle, separators=(",", ":"), sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

    def record_if_fresh(self, session_id: int, auth_counter: int, next_frame_id: int) -> bool:
        session = int(session_id)
        counter = int(auth_counter)
        next_id = int(next_frame_id)
        if not 1 <= session <= 0xFFFFFFFF:
            raise ValueError("session_id must be a non-zero uint32")
        if not 1 <= counter <= MAX_AUTH_COUNTER:
            raise ValueError("auth_counter is invalid")
        if not 0 <= next_id <= MAX_DATA_FRAME_ID:
            raise ValueError("next_frame_id is invalid")

        key = str(session)
        current = self.sessions.get(key)
        if current is not None and counter <= current["auth_counter"]:
            return False

        self.sessions[key] = {
            "auth_counter": counter,
            "next_frame_id": next_id,
        }
        self.sessions.move_to_end(key)
        while len(self.sessions) > self.max_sessions:
            self.sessions.popitem(last=False)
        self._save()
        return True
