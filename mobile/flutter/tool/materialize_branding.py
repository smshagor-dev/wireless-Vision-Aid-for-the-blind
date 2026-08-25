#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / "tool" / "branding"
GENERATED = ROOT / ".generated"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_SIZE = (192, 192)
EXPECTED = {
    "wvab_launcher.png": "3dd7859dabcc70ea7b5b8069b46b532a85924239b29d27e7aa7344ebe6467c43",
    "wvab_launcher_foreground.png": "97aea4f3229f4fef747ab1d531dfec8e2bd3df5ea12157d5f3865190f10ea574",
}


def _decode(payload: str, output_name: str) -> None:
    compact = "".join(payload.split())
    try:
        data = base64.b64decode(compact, validate=True)
    except Exception as exc:  # noqa: BLE001 - turn malformed committed data into a clear build failure.
        raise SystemExit(f"Invalid Base64 branding source for {output_name}: {exc}") from exc

    if not data.startswith(PNG_SIGNATURE) or len(data) < 24:
        raise SystemExit(f"Branding source for {output_name} is not a PNG")

    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != EXPECTED_SIZE:
        raise SystemExit(
            f"Unexpected {output_name} dimensions: {width}x{height}; expected 192x192"
        )

    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED[output_name]:
        raise SystemExit(
            f"Branding checksum mismatch for {output_name}: {digest}"
        )

    GENERATED.mkdir(parents=True, exist_ok=True)
    target = GENERATED / output_name
    target.write_bytes(data)
    print(f"Materialized {target.relative_to(ROOT)} ({len(data)} bytes, sha256={digest})")


def main() -> None:
    launcher_parts = sorted(BRANDING.glob("wvab_launcher.b64.part*"))
    if not launcher_parts:
        raise SystemExit("No WVAB launcher icon source chunks found")

    launcher_payload = "".join(path.read_text(encoding="ascii") for path in launcher_parts)
    foreground_path = BRANDING / "wvab_launcher_foreground.b64"
    if not foreground_path.is_file():
        raise SystemExit("Adaptive launcher foreground source is missing")

    _decode(launcher_payload, "wvab_launcher.png")
    _decode(
        foreground_path.read_text(encoding="ascii"),
        "wvab_launcher_foreground.png",
    )


if __name__ == "__main__":
    main()
