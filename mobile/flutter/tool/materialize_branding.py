#!/usr/bin/env python3
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / "tool" / "branding"
GENERATED = ROOT / ".generated"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_SIZE = (192, 192)
LAUNCHER_CHUNK_SIZE = 7000

# Hashes produced by the regressed code-drawn launcher. The committed WVAB
# artwork must never silently fall back to these assets again.
BLOCKED_OLD_HASHES = {
    "wvab_launcher.png": "b1a3b209775db713543a5c81ab28212edcf5c2dcfe39a60d33f917f03315296a",
    "wvab_launcher_foreground.png": "ad4cbb708b8aa3380129c7c65fc0ecc4409dce2d4fdf4ebe8d83847e9a8caf69",
}


def _valid_png(data: bytes) -> bool:
    if not data.startswith(PNG_SIGNATURE) or len(data) < 33:
        return False
    try:
        width, height = struct.unpack(">II", data[16:24])
        if (width, height) != EXPECTED_SIZE:
            return False
        offset = len(PNG_SIGNATURE)
        saw_iend = False
        while offset + 12 <= len(data):
            length = struct.unpack(">I", data[offset : offset + 4])[0]
            chunk_type = data[offset + 4 : offset + 8]
            data_start = offset + 8
            data_end = data_start + length
            crc_end = data_end + 4
            if crc_end > len(data):
                return False
            stored_crc = struct.unpack(">I", data[data_end:crc_end])[0]
            actual_crc = zlib.crc32(chunk_type)
            actual_crc = zlib.crc32(data[data_start:data_end], actual_crc) & 0xFFFFFFFF
            if stored_crc != actual_crc:
                return False
            offset = crc_end
            if chunk_type == b"IEND":
                saw_iend = True
                break
        return saw_iend and offset == len(data)
    except (struct.error, ValueError):
        return False


def _canonical_decode(payload: str, output_name: str) -> tuple[bytes, bool]:
    compact = "".join(payload.split())
    data_chars = compact.rstrip("=")

    def decode(chars: str) -> bytes | None:
        normalized = chars + "=" * (-len(chars) % 4)
        try:
            candidate = base64.b64decode(normalized, validate=True)
        except (binascii.Error, ValueError):
            return None
        return candidate if _valid_png(candidate) else None

    data = decode(data_chars)
    if data is not None:
        return data, False

    # The uploaded launcher source had a historical single-character Base64
    # corruption. Recover only when exactly one deletion yields a CRC-valid,
    # complete 192x192 PNG. This is deterministic and refuses ambiguous repair.
    repaired: dict[bytes, int] = {}
    if len(data_chars) % 4 == 1:
        for index in range(len(data_chars)):
            candidate = decode(data_chars[:index] + data_chars[index + 1 :])
            if candidate is not None:
                repaired.setdefault(candidate, index)
                if len(repaired) > 1:
                    break

    if len(repaired) != 1:
        raise SystemExit(
            f"Invalid Base64 branding source for {output_name}; "
            f"could not uniquely recover a valid PNG"
        )

    data, removed_index = next(iter(repaired.items()))
    print(
        f"Recovered {output_name} by removing one corrupt Base64 character "
        f"at canonical index {removed_index}"
    )
    return data, True


def _materialize(payload: str, output_name: str) -> tuple[dict[str, object], bytes, bool]:
    data, repaired = _canonical_decode(payload, output_name)
    width, height = struct.unpack(">II", data[16:24])
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
    return (
        {
            "path": str(target.relative_to(ROOT)),
            "sha256": digest,
            "width": width,
            "height": height,
            "bytes": len(data),
            "source_repaired": repaired,
        },
        data,
        repaired,
    )


def _rewrite_launcher_parts(data: bytes, launcher_parts: list[Path]) -> None:
    canonical = base64.b64encode(data).decode("ascii")
    chunks = [
        canonical[index : index + LAUNCHER_CHUNK_SIZE]
        for index in range(0, len(canonical), LAUNCHER_CHUNK_SIZE)
    ]
    if len(chunks) != len(launcher_parts):
        raise SystemExit(
            f"Canonical launcher requires {len(chunks)} chunks; "
            f"repository contains {len(launcher_parts)}"
        )
    for path, chunk in zip(launcher_parts, chunks, strict=True):
        path.write_text(chunk + "\n", encoding="ascii")
    print("Canonicalized repaired launcher Base64 source chunks")


def main() -> None:
    launcher_parts = sorted(BRANDING.glob("wvab_launcher.b64.part*"))
    if not launcher_parts:
        raise SystemExit("No WVAB launcher icon source chunks found")

    launcher_payload = "".join(path.read_text(encoding="ascii") for path in launcher_parts)
    foreground_path = BRANDING / "wvab_launcher_foreground.b64"
    if not foreground_path.is_file():
        raise SystemExit("Adaptive launcher foreground source is missing")

    launcher_meta, launcher_data, launcher_repaired = _materialize(
        launcher_payload, "wvab_launcher.png"
    )
    foreground_meta, _, _ = _materialize(
        foreground_path.read_text(encoding="ascii"),
        "wvab_launcher_foreground.png",
    )

    if launcher_repaired:
        _rewrite_launcher_parts(launcher_data, launcher_parts)

    manifest = {
        "source": "committed-wvab-branding",
        "launcher": launcher_meta,
        "foreground": foreground_meta,
    }
    manifest_path = GENERATED / "branding_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
