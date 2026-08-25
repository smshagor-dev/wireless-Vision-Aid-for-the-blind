#!/usr/bin/env python3
"""Generate a matched, private ESP32/Raspberry Pi WVAB credential pair."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import shutil
import tempfile


def c_string(value):
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("values may not contain NUL/newline characters")
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _write_temp(parent: Path, prefix: str, content: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=prefix, dir=str(parent), text=True)
    path = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return path
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    fd, name = tempfile.mkstemp(prefix=path.name + ".backup-", dir=str(path.parent))
    os.close(fd)
    backup = Path(name)
    shutil.copy2(path, backup)
    try:
        os.chmod(backup, 0o600)
    except OSError:
        pass
    return backup


def write_pair_atomic(files: list[tuple[Path, str]]) -> None:
    """Replace a credential pair with rollback if either final replace fails."""
    temps: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    try:
        for target, content in files:
            temps[target] = _write_temp(target.parent, target.name + ".tmp-", content)
            backups[target] = _backup(target)

        for target, _ in files:
            os.replace(temps[target], target)
            replaced.append(target)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass

    except Exception:
        for target in reversed(replaced):
            backup = backups.get(target)
            try:
                if backup is not None and backup.exists():
                    os.replace(backup, target)
                elif target.exists():
                    target.unlink()
            except OSError:
                pass
        raise
    finally:
        for temp in temps.values():
            try:
                if temp.exists():
                    temp.unlink()
            except OSError:
                pass
        for backup in backups.values():
            try:
                if backup is not None and backup.exists():
                    backup.unlink()
            except OSError:
                pass


def build_parser():
    parser = argparse.ArgumentParser(description="Generate matching WVAB ESP32 and Raspberry Pi credentials")
    parser.add_argument("--server-ip", default="192.168.4.2", help="Raspberry Pi/server host reachable from the ESP32")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--station", action="store_true", help="Use station mode instead of ESP32 access-point mode")
    parser.add_argument("--ssid", default="", help="Station-mode Wi-Fi SSID")
    parser.add_argument("--wifi-password", default="", help="Station-mode Wi-Fi password")
    parser.add_argument("--ap-ssid", default="WVAB_CAM")
    parser.add_argument("--ap-password", default="", help="AP password; generated when omitted")
    parser.add_argument("--force", action="store_true", help="Rotate/overwrite both existing local credential files")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not (1 <= args.port <= 65535):
        parser.error("--port must be between 1 and 65535")
    if not str(args.server_ip).strip():
        parser.error("--server-ip must not be empty")

    use_ap = not args.station
    if args.station and (not args.ssid or len(args.wifi_password) < 8):
        parser.error("station mode requires --ssid and a Wi-Fi password of at least 8 characters")

    ap_password = args.ap_password or secrets.token_urlsafe(12)
    if use_ap and (not args.ap_ssid or len(ap_password) < 8):
        parser.error("AP mode requires a non-empty SSID and password of at least 8 characters")

    root = Path(__file__).resolve().parent.parent
    header_path = root / "esp32_secrets.h"
    env_path = root / "deployment" / "rpi" / "wvab_edge.env"
    existing = [path for path in (header_path, env_path) if path.exists()]
    if existing and not args.force:
        parser.error(
            "refusing to overwrite existing credentials: "
            + ", ".join(str(path) for path in existing)
            + "; pass --force to rotate both files"
        )

    key = os.urandom(32)
    udp_token = secrets.token_urlsafe(32)
    ws_token = secrets.token_urlsafe(32)
    byte_list = ", ".join(f"0x{byte:02X}" for byte in key)

    header = f'''#pragma once\n#include <stdint.h>\n\n#define WVAB_SECRETS_CONFIGURED 1\n#define WVAB_USE_AP_MODE {str(use_ap).lower()}\n#define WVAB_AP_SSID {c_string(args.ap_ssid)}\n#define WVAB_AP_PASSWORD {c_string(ap_password)}\n#define WVAB_WIFI_SSID {c_string(args.ssid)}\n#define WVAB_WIFI_PASSWORD {c_string(args.wifi_password)}\n#define WVAB_UDP_HOST {c_string(str(args.server_ip).strip())}\n#define WVAB_UDP_PORT {args.port}\n#define WVAB_UDP_TOKEN {c_string(udp_token)}\n\nstatic const uint8_t WVAB_AES_KEY[32] = {{{byte_list}}};\n'''

    env = f'''WVAB_OFFLINE=1\nWVAB_UDP_ENCRYPT=1\nWVAB_UDP_AUTH=1\nWVAB_ALLOW_INSECURE_UDP=0\nWVAB_UDP_KEY_HEX={key.hex()}\nWVAB_UDP_TOKEN={udp_token}\nWVAB_UDP_AUTH_TTL_S=120\nWVAB_UDP_HEADLESS=1\nWVAB_UDP_TTS=1\nWVAB_UDP_TTS_RATE=170\nWVAB_UDP_LOG_PATH=wvab_udp_rpi.log\nWVAB_UDP_HEALTH_PATH=wvab_udp_server_health.json\nWVAB_UDP_WATCHDOG_SERVER_IDLE_S=30\nWVAB_UDP_TRACKING=1\nWVAB_WS_CONTROL=1\nWVAB_WS_CONTROL_HOST=127.0.0.1\nWVAB_WS_CONTROL_PORT=8765\nWVAB_WS_TOKEN={ws_token}\n'''

    write_pair_atomic([(header_path, header), (env_path, env)])

    print(f"Created {header_path}")
    print(f"Created {env_path}")
    print("Both files are git-ignored. Keep them private and rotate both with --force if exposed.")
    if use_ap:
        print(f"ESP32 AP SSID: {args.ap_ssid}")
        print("AP password is stored only in esp32_secrets.h; it is not printed here.")


if __name__ == "__main__":
    main()
