"""Generate simple solid-color PWA placeholder icons (pure stdlib, no Pillow)."""

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public"
OUT.mkdir(parents=True, exist_ok=True)


def make_png(size: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # Draw a rounded-square feel: solid bg with a lighter center "book" block
    bg = rgb
    fg = (56, 189, 248)  # accent
    rows = b""
    margin = size // 4
    for y in range(size):
        row = b"\x00"
        for x in range(size):
            inside = margin <= x < size - margin and margin <= y < size - margin
            row += bytes(fg if inside else bg)
        rows += row

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


for s in (192, 512):
    (OUT / f"icon-{s}.png").write_bytes(make_png(s, (15, 23, 42)))
    print(f"wrote icon-{s}.png")
