#!/usr/bin/env python3
import argparse
import os
import secrets
from pathlib import Path


def c_string(value):
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("values may not contain NUL/newline characters")
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def write_private(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    parser = argparse.ArgumentParser(description="Generate matching WVAB ESP32 and Raspberry Pi credentials")
    parser.add_argument("--server-ip", default="192.168.4.2", help="Raspberry Pi/server IP reachable from the ESP32")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--station", action="store_true", help="Use station mode instead of ESP32 access-point mode")
    parser.add_argument("--ssid", default="", help="Station-mode Wi-Fi SSID")
    parser.add_argument("--wifi-password", default="", help="Station-mode Wi-Fi password")
    parser.add_argument("--ap-ssid", default="WVAB_CAM")
    parser.add_argument("--ap-password", default="", help="AP password; generated when omitted")
    parser.add_argument("--force", action="store_true", help="Rotate/overwrite existing local credentials")
    args = parser.parse_args()

    if not (1 <= args.port <= 65535):
        parser.error("--port must be between 1 and 65535")
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
    header = f'''#pragma once\n#include <stdint.h>\n\n#define WVAB_SECRETS_CONFIGURED 1\n#define WVAB_USE_AP_MODE {str(use_ap).lower()}\n#define WVAB_AP_SSID {c_string(args.ap_ssid)}\n#define WVAB_AP_PASSWORD {c_string(ap_password)}\n#define WVAB_WIFI_SSID {c_string(args.ssid)}\n#define WVAB_WIFI_PASSWORD {c_string(args.wifi_password)}\n#define WVAB_UDP_HOST {c_string(args.server_ip)}\n#define WVAB_UDP_PORT {args.port}\n#define WVAB_UDP_TOKEN {c_string(udp_token)}\n\nstatic const uint8_t WVAB_AES_KEY[32] = {{{byte_list}}};\n'''

    env = f'''WVAB_UDP_ENCRYPT=1\nWVAB_UDP_AUTH=1\nWVAB_UDP_KEY_HEX={key.hex()}\nWVAB_UDP_TOKEN={udp_token}\nWVAB_UDP_HEADLESS=1\nWVAB_UDP_TTS=1\nWVAB_UDP_TTS_RATE=170\nWVAB_UDP_LOG_PATH=wvab_udp_rpi.log\nWVAB_UDP_HEALTH_PATH=wvab_udp_server_health.json\nWVAB_UDP_WATCHDOG_SERVER_IDLE_S=30\nWVAB_UDP_TRACKING=1\nWVAB_WS_CONTROL=1\nWVAB_WS_CONTROL_HOST=127.0.0.1\nWVAB_WS_CONTROL_PORT=8765\nWVAB_WS_TOKEN={ws_token}\n'''

    write_private(header_path, header)
    try:
        write_private(env_path, env)
    except Exception:
        # Avoid leaving a newly rotated ESP32 secret without its matching Pi secret.
        try:
            header_path.unlink()
        except OSError:
            pass
        raise

    print(f"Created {header_path}")
    print(f"Created {env_path}")
    print("Both files are git-ignored. Keep them private and rotate with --force if exposed.")
    if use_ap:
        print(f"ESP32 AP SSID: {args.ap_ssid}")
        print("AP password is stored only in esp32_secrets.h; it is not printed here.")
