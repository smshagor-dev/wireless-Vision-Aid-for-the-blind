#!/usr/bin/env python3
from __future__ import annotations

import binascii
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / ".generated"
WIDTH = 192
HEIGHT = 192
SUPERSAMPLE = 4
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED = {
    "wvab_launcher.png": "b1a3b209775db713543a5c81ab28212edcf5c2dcfe39a60d33f917f03315296a",
    "wvab_launcher_foreground.png": "ad4cbb708b8aa3380129c7c65fc0ecc4409dce2d4fdf4ebe8d83847e9a8caf69",
}

NAVY = (7, 17, 47)
NAVY_LIGHT = (10, 26, 69)
CYAN = (56, 189, 248)
WHITE = (255, 255, 255)


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def _adler32(data: bytes) -> int:
    modulus = 65521
    a = 1
    b = 0
    for value in data:
        a = (a + value) % modulus
        b = (b + a) % modulus
    return (b << 16) | a


def _stored_zlib(data: bytes) -> bytes:
    """Return a deterministic zlib stream using uncompressed DEFLATE blocks."""
    output = bytearray(b"\x78\x01")
    offset = 0
    while offset < len(data):
        block = data[offset : offset + 65535]
        offset += len(block)
        output.append(1 if offset == len(data) else 0)
        size = len(block)
        output.extend(struct.pack("<H", size))
        output.extend(struct.pack("<H", 0xFFFF - size))
        output.extend(block)
    output.extend(struct.pack(">I", _adler32(data)))
    return bytes(output)


def _png(pixels: bytes) -> bytes:
    rows = b"".join(
        b"\x00" + pixels[y * WIDTH * 4 : (y + 1) * WIDTH * 4]
        for y in range(HEIGHT)
    )
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", _stored_zlib(rows))
        + _chunk(b"IEND", b"")
    )


def _background(x: int, y: int) -> tuple[int, int, int]:
    dx = abs(x - 384)
    dy = abs(y - 392)
    radius = max(dx * 100 // 384, dy * 100 // 440)
    radius = min(radius, 100)
    blend = (100 - radius) * 45 // 100
    return tuple(
        (NAVY[index] * (100 - blend) + NAVY_LIGHT[index] * blend + 50) // 100
        for index in range(3)
    )


def _inside_eye(x: int, y: int) -> bool:
    center_x = 376
    center_y = 416
    half_width = 244
    dx = x - center_x
    if abs(dx) >= half_width:
        return False
    extent = 106 * (half_width * half_width - dx * dx) // (half_width * half_width)
    middle = center_y - dx // 22
    return abs(y - middle) <= extent


def _inside_circle(x: int, y: int, center_x: int, center_y: int, radius: int) -> bool:
    dx = x - center_x
    dy = y - center_y
    return dx * dx + dy * dy <= radius * radius


def _inside_upper_ring(
    x: int,
    y: int,
    center_x: int,
    center_y: int,
    radius: int,
    thickness: int,
) -> bool:
    if y >= center_y:
        return False
    dx = x - center_x
    dy = y - center_y
    distance_squared = dx * dx + dy * dy
    inner = radius - thickness // 2
    outer = radius + thickness // 2
    return inner * inner <= distance_squared <= outer * outer


def _symbol(x: int, y: int) -> tuple[int, int, int, int] | None:
    if _inside_eye(x, y):
        color = WHITE
        if _inside_circle(x, y, 380, 408, 70):
            color = CYAN
        if _inside_circle(x, y, 380, 408, 37):
            color = NAVY
        if _inside_circle(x, y, 362, 389, 13):
            color = WHITE
        return (*color, 255)

    if _inside_upper_ring(x, y, 504, 330, 112, 18):
        return (*CYAN, 255)
    if _inside_upper_ring(x, y, 504, 330, 156, 18):
        return (*WHITE, 255)
    if _inside_circle(x, y, 504, 330, 17):
        return (*CYAN, 255)
    return None


def _render(*, foreground: bool) -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 4)
    samples = SUPERSAMPLE * SUPERSAMPLE

    for pixel_y in range(HEIGHT):
        for pixel_x in range(WIDTH):
            totals = [0, 0, 0, 0]
            for sample_y in range(SUPERSAMPLE):
                for sample_x in range(SUPERSAMPLE):
                    x = pixel_x * SUPERSAMPLE + sample_x
                    y = pixel_y * SUPERSAMPLE + sample_y
                    symbol = _symbol(x, y)
                    if symbol is not None:
                        color = symbol
                    elif foreground:
                        color = (0, 0, 0, 0)
                    else:
                        color = (*_background(x, y), 255)
                    for index, value in enumerate(color):
                        totals[index] += value

            rgba = tuple((value + samples // 2) // samples for value in totals)
            offset = (pixel_y * WIDTH + pixel_x) * 4
            pixels[offset : offset + 4] = bytes(rgba)

    return _png(bytes(pixels))


def _write(output_name: str, *, foreground: bool) -> None:
    data = _render(foreground=foreground)
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED[output_name]:
        raise SystemExit(f"Branding checksum mismatch for {output_name}: {digest}")

    if not data.startswith(PNG_SIGNATURE):
        raise SystemExit(f"Generated branding for {output_name} is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (WIDTH, HEIGHT):
        raise SystemExit(f"Unexpected {output_name} dimensions: {width}x{height}")

    GENERATED.mkdir(parents=True, exist_ok=True)
    target = GENERATED / output_name
    target.write_bytes(data)
    print(
        f"Generated {target.relative_to(ROOT)} "
        f"({len(data)} bytes, sha256={digest})"
    )


def main() -> None:
    _write("wvab_launcher.png", foreground=False)
    _write("wvab_launcher_foreground.png", foreground=True)


if __name__ == "__main__":
    main()
