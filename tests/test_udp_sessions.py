from collections import OrderedDict

from core.udp_runtime import UDPVisionServer


def _bare_server():
    server = UDPVisionServer.__new__(UDPVisionServer)
    server.sessions = {}
    server.retired_sessions = OrderedDict()
    server.last_completed_frame = {}
    return server


def test_new_sender_session_retires_previous_session():
    server = _bare_server()
    addr = ("192.168.4.2", 9999)

    assert server._bind_session(addr, 101, 1.0)
    assert server.sessions[addr]["session_id"] == 101

    assert server._bind_session(addr, 202, 2.0)
    assert server.sessions[addr]["session_id"] == 202
    assert (addr, 101) in server.retired_sessions


def test_retired_session_cannot_replace_current_session():
    server = _bare_server()
    addr = ("192.168.4.2", 9999)

    assert server._bind_session(addr, 101, 1.0)
    assert server._bind_session(addr, 202, 2.0)
    assert not server._bind_session(addr, 101, 3.0)
    assert server.sessions[addr]["session_id"] == 202


def test_reauth_same_session_does_not_reset_replay_state():
    server = _bare_server()
    addr = ("192.168.4.2", 9999)
    replay_key = (addr, 303)

    assert server._bind_session(addr, 303, 1.0)
    server.last_completed_frame[replay_key] = 77
    assert server._bind_session(addr, 303, 2.0)
    assert server.last_completed_frame[replay_key] == 77
