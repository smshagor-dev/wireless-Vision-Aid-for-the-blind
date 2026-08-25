import json

import pytest

from core.udp_auth_state import (
    AUTH_PAYLOAD_PREFIX,
    AUTH_PAYLOAD_VERSION,
    ReplayStateStore,
    decode_auth_payload,
    encode_auth_payload,
    previous_frame_id,
)
from core.udp_protocol import MAX_DATA_FRAME_ID


TOKEN = "wvab-auth-state-test-token"


def test_auth_payload_round_trip_binds_counter_and_next_frame():
    payload = encode_auth_payload(TOKEN, 7, 123)
    assert payload[0] == AUTH_PAYLOAD_VERSION
    assert len(payload) == AUTH_PAYLOAD_PREFIX.size + len(TOKEN.encode())
    assert decode_auth_payload(payload) == (TOKEN, 7, 123)


def test_legacy_token_only_auth_payload_is_rejected():
    with pytest.raises(ValueError, match="authentication payload"):
        decode_auth_payload(TOKEN.encode())


def test_previous_frame_baseline_handles_start_and_wrap():
    assert previous_frame_id(1) == 0
    assert previous_frame_id(55) == 54
    assert previous_frame_id(0) == MAX_DATA_FRAME_ID


def test_replay_counter_persists_across_store_restart(tmp_path):
    path = tmp_path / "replay.json"
    first = ReplayStateStore(path)
    assert first.record_if_fresh(101, 1, 50)
    assert not first.record_if_fresh(101, 1, 50)

    restarted = ReplayStateStore(path)
    assert not restarted.record_if_fresh(101, 1, 50)
    assert restarted.record_if_fresh(101, 2, 75)

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["sessions"][-1]["auth_counter"] == 2
    assert persisted["sessions"][-1]["next_frame_id"] == 75


def test_replay_state_is_bounded(tmp_path):
    store = ReplayStateStore(tmp_path / "replay.json", max_sessions=2)
    assert store.record_if_fresh(1, 1, 0)
    assert store.record_if_fresh(2, 1, 0)
    assert store.record_if_fresh(3, 1, 0)
    assert list(store.sessions) == ["2", "3"]


def test_corrupt_replay_state_fails_closed(tmp_path):
    path = tmp_path / "replay.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="replay state"):
        ReplayStateStore(path)
