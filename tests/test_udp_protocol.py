import pytest

from core.udp_protocol import (
    AUTH_FRAME_ID,
    HEADER_SIZE,
    MAX_DATA_FRAME_ID,
    MAX_FRAME_CHUNKS,
    MAX_UDP_PAYLOAD,
    frame_id_is_newer,
    pack_header,
    unpack_header,
    valid_frame_shape,
    valid_session_id,
)
from core.udp_runtime import _new_session_id


def test_header_round_trip_includes_authenticated_session_id():
    header = pack_header(7, 42, 3, 1, 100)
    assert len(header) == HEADER_SIZE == 14
    assert unpack_header(header) == (7, 42, 3, 1, 100)


def test_session_id_zero_is_rejected():
    assert not valid_session_id(0)
    assert valid_session_id(1)
    assert valid_session_id(0xFFFFFFFF)
    with pytest.raises(ValueError, match="session_id"):
        pack_header(0, 1, 1, 0, 10)


def test_generated_session_ids_are_nonzero_uint32():
    values = {_new_session_id() for _ in range(32)}
    assert values
    assert all(1 <= value <= 0xFFFFFFFF for value in values)


def test_frame_id_replay_comparison_handles_wrap():
    assert frame_id_is_newer(1, 0)
    assert not frame_id_is_newer(0, 0)
    assert not frame_id_is_newer(9, 10)
    assert frame_id_is_newer(0, MAX_DATA_FRAME_ID)
    assert frame_id_is_newer(5, MAX_DATA_FRAME_ID - 2)


def test_auth_id_is_reserved_above_data_range():
    assert AUTH_FRAME_ID == 0xFFFFFFFF
    assert MAX_DATA_FRAME_ID == AUTH_FRAME_ID - 1


def test_packet_shape_enforces_protocol_bounds():
    packet_size = HEADER_SIZE + 100
    assert valid_frame_shape(3, 1, 100, packet_size)
    assert not valid_frame_shape(0, 0, 100, packet_size)
    assert not valid_frame_shape(MAX_FRAME_CHUNKS + 1, 0, 100, packet_size)
    assert not valid_frame_shape(3, 3, 100, packet_size)
    assert not valid_frame_shape(3, 1, 0, HEADER_SIZE)
    assert not valid_frame_shape(3, 1, 100, MAX_UDP_PAYLOAD + 1)
