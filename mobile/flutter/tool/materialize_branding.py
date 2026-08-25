#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / "tool" / "branding"
GENERATED = ROOT / ".generated"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_SIZE = (192, 192)

# These are the hashes produced by the regressed code-drawn launcher. They must
# never be accepted as the WVAB uploaded/committed launcher artwork again.
BLOCKED_OLD_HASHES = {
    "wvab_launcher.png": "b1a3b209775db713543a5c81ab28212edcf5c2dcfe39a60d33f917f03315296a",
    "wvab_launcher_foreground.png": "ad4cbb708b8aa3380129c7c65fc0ecc4409dce2d4fdf4ebe8d83847e9a8caf69",
}


def _decode(payload: str, output_name: str) -> dict[str, object]:
    compact = "".join(payload.split())
    compact += "=" * (-len(compact) % 4)
    try:
        data = base64.b64decode(compact, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Invalid Base64 branding source for {output_name}: {exc}") from exc

    if not data.startswith(PNG_SIGNATURE) or len(data) < 24:
        raise SystemExit(f"Branding source for {output_name} is not a PNG")

    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != EXPECTED_SIZE:
        raise SystemExit(
            f"Unexpected {output_name} dimensions: {width}x{height}; expected 192x192"
        )

    digest = hashlib.sha256(data).hexdigest()
    if digest == BLOCKED_OLD_HASHES[output_name]:
        raise SystemExit(
            f"Refusing regressed old launcher artwork for {output_name}: {digest}"
        )

    GENERATED.mkdir(parents=True, exist_ok=True)
    target = GENERATED / output_name
    target.write_bytes(data)
    print(
        f"Materialized {target.relative_to(ROOT)} "
        f"({len(data)} bytes, {width}x{height}, sha256={digest})"
    )
    return {
        "path": str(target.relative_to(ROOT)),
        "sha256": digest,
        "width": width,
        "height": height,
        "bytes": len(data),
    }


def main() -> None:
    launcher_parts = sorted(BRANDING.glob("wvab_launcher.b64.part*"))
    if not launcher_parts:
        raise SystemExit("No WVAB launcher icon source chunks found")

    launcher_payload = "".join(path.read_text(encoding="ascii") for path in launcher_parts)
    foreground_path = BRANDING / "wvab_launcher_foreground.b64"
    if not foreground_path.is_file():
        raise SystemExit("Adaptive launcher foreground source is missing")

    manifest = {
        "source": "committed-wvab-branding",
        "launcher": _decode(launcher_payload, "wvab_launcher.png"),
        "foreground": _decode(
            foreground_path.read_text(encoding="ascii"),
            "wvab_launcher_foreground.png",
        ),
    }
    manifest_path = GENERATED / "branding_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
