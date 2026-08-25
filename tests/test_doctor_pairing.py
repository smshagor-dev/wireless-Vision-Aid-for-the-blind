import test_system
from test_system import Doctor


def _write_pair(root, *, port=9999, env_port=None, token="abcdefghijklmnop1234567890", key_hex=None):
    key_hex = key_hex or ("ab" * 32)
    env_port = port if env_port is None else env_port
    header_bytes = ", ".join(f"0x{key_hex[i:i+2].upper()}" for i in range(0, len(key_hex), 2))
    (root / "deployment" / "rpi").mkdir(parents=True)
    (root / "esp32_secrets.h").write_text(
        "#define WVAB_SECRETS_CONFIGURED 1\n"
        f"#define WVAB_UDP_PORT {port}\n"
        f'#define WVAB_UDP_TOKEN "{token}"\n'
        f"static const uint8_t WVAB_AES_KEY[32] = {{{header_bytes}}};\n",
        encoding="utf-8",
    )
    (root / "deployment" / "rpi" / "wvab_edge.env").write_text(
        "WVAB_OFFLINE=1\n"
        "WVAB_UDP_ENCRYPT=1\n"
        "WVAB_UDP_AUTH=1\n"
        "WVAB_ALLOW_INSECURE_UDP=0\n"
        f"WVAB_UDP_PORT={env_port}\n"
        f"WVAB_UDP_KEY_HEX={key_hex}\n"
        f"WVAB_UDP_TOKEN={token}\n"
        "WVAB_WS_TOKEN=separate-websocket-token-12345\n",
        encoding="utf-8",
    )


def test_doctor_accepts_exact_device_pair(tmp_path, monkeypatch):
    _write_pair(tmp_path, port=12001)
    monkeypatch.setattr(test_system, "ROOT", tmp_path)
    doctor = Doctor()
    assert doctor.check_device_pair(required=True)
    assert doctor.results[-1]["status"] == "PASS"
    assert "port 12001" in doctor.results[-1]["message"]


def test_doctor_rejects_port_mismatch(tmp_path, monkeypatch):
    _write_pair(tmp_path, port=12001, env_port=9999)
    monkeypatch.setattr(test_system, "ROOT", tmp_path)
    doctor = Doctor()
    assert not doctor.check_device_pair(required=True)
    assert "ports" in doctor.results[-1]["message"]


def test_doctor_rejects_key_mismatch(tmp_path, monkeypatch):
    _write_pair(tmp_path)
    env_path = tmp_path / "deployment" / "rpi" / "wvab_edge.env"
    env_path.write_text(env_path.read_text(encoding="utf-8").replace("ab" * 32, "cd" * 32), encoding="utf-8")
    monkeypatch.setattr(test_system, "ROOT", tmp_path)
    doctor = Doctor()
    assert not doctor.check_device_pair(required=True)
    assert "AES keys do not match" in doctor.results[-1]["message"]


def test_doctor_rejects_token_mismatch(tmp_path, monkeypatch):
    _write_pair(tmp_path)
    env_path = tmp_path / "deployment" / "rpi" / "wvab_edge.env"
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "WVAB_UDP_TOKEN=abcdefghijklmnop1234567890",
            "WVAB_UDP_TOKEN=zyxwvutsrqponmlk1234567890",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(test_system, "ROOT", tmp_path)
    doctor = Doctor()
    assert not doctor.check_device_pair(required=True)
    assert "UDP tokens do not match" in doctor.results[-1]["message"]
