#!/usr/bin/env python3
"""WVAB source-checkout command dispatcher."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent

COMMANDS = {
    "doctor": (ROOT / "test_system.py", []),
    "vision": (ROOT / "vision_server.py", []),
    "phone": (ROOT / "smartphone_camera.py", []),
    "udp-server": (ROOT / "udp_streaming.py", ["server"]),
    "udp-client": (ROOT / "udp_streaming.py", ["client"]),
    "navigation": (ROOT / "navigation_pipeline.py", []),
    "secrets": (ROOT / "tools" / "generate_device_secrets.py", []),
    "models": (ROOT / "tools" / "download_models.py", []),
}


def show_help():
    print("WVAB command dispatcher\n")
    print("Usage: python main.py <command> [arguments]\n")
    print("Commands:")
    print("  doctor       Offline-first host diagnostics")
    print("  vision       Local/USB/IP camera assistive runtime")
    print("  phone        Smartphone/IP-camera launcher; URL required")
    print("  udp-server   Authenticated/encrypted UDP vision server")
    print("  udp-client   Authenticated/encrypted Python camera sender")
    print("  navigation   Experimental fail-safe navigation pipeline")
    print("  secrets      Generate local ESP32/Raspberry Pi credentials")
    print("  models       Provision verified optional model assets")
    print("\nExamples:")
    print("  python main.py doctor --full --camera 0")
    print("  python main.py vision --camera 0")
    print("  python main.py phone http://192.168.1.20:8080/video --test-only")
    print("  python main.py udp-server --config wvab_config.sample.json")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        show_help()
        return 0
    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        show_help()
        return 2
    script, prefix = COMMANDS[command]
    if not script.exists():
        print(f"Command target is missing: {script}", file=sys.stderr)
        return 2
    completed = subprocess.run(
        [sys.executable, str(script), *prefix, *sys.argv[2:]],
        cwd=str(ROOT),
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
