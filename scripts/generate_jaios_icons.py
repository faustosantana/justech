#!/usr/bin/env python3
"""Genera iconos oficiales JAIOS — J grande azul Justech sobre fondo claro."""

from __future__ import annotations

import platform
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "desktop" / "src-tauri" / "icons"
DESKTOP = ROOT / "desktop"

# Justech / JAIOS brand
J_BLUE = (37, 99, 235)
J_BLUE_DARK = (29, 78, 216)
BG_TOP = (255, 255, 255)
BG_BOTTOM = (239, 246, 255)
BORDER = (191, 219, 254)


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def inside_rounded_rect(x: float, y: float, size: int, radius: float) -> bool:
    r = radius
    if x < r and y < r:
        return (x - r) ** 2 + (y - r) ** 2 <= r * r
    if x > size - 1 - r and y < r:
        return (x - (size - 1 - r)) ** 2 + (y - r) ** 2 <= r * r
    if x < r and y > size - 1 - r:
        return (x - r) ** 2 + (y - (size - 1 - r)) ** 2 <= r * r
    if x > size - 1 - r and y > size - 1 - r:
        return (x - (size - 1 - r)) ** 2 + (y - (size - 1 - r)) ** 2 <= r * r
    return True


def in_bold_j(x: float, y: float, size: int) -> bool:
    """Letra J grande, bold, centrada — legible en Dock y bandeja Windows."""
    s = size
    cx = s * 0.5
    # Barra superior
    top_y0, top_y1 = s * 0.18, s * 0.30
    top_x0, top_x1 = s * 0.28, s * 0.72
    # Tallo vertical
    stem_x0, stem_x1 = s * 0.44, s * 0.56
    stem_y0, stem_y1 = s * 0.18, s * 0.62
    # Gancho inferior
    hook_cy = s * 0.68
    hook_rx, hook_ry = s * 0.20, s * 0.14
    hook_thick = s * 0.055

    if top_x0 <= x <= top_x1 and top_y0 <= y <= top_y1:
        return True
    if stem_x0 <= x <= stem_x1 and stem_y0 <= y <= stem_y1:
        return True

    # Elipse del gancho (parte inferior de la J)
    dx = (x - cx) / max(hook_rx, 1)
    dy = (y - hook_cy) / max(hook_ry, 1)
    dist = dx * dx + dy * dy
    if 0.55 <= dist <= 1.35 and y >= hook_cy - hook_thick and x <= stem_x1 + hook_thick:
        return True
    # Conector gancho → tallo
    if stem_x0 - hook_thick <= x <= stem_x1 and hook_cy - hook_ry <= y <= hook_cy + hook_thick:
        return True
    return False


def render_icon(size: int) -> bytes:
    radius = size * 0.215
    pad = size * 0.04
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        t = y / max(size - 1, 1)
        br = lerp(BG_TOP[0], BG_BOTTOM[0], t)
        bg = lerp(BG_TOP[1], BG_BOTTOM[1], t)
        bb = lerp(BG_TOP[2], BG_BOTTOM[2], t)
        for x in range(size):
            if not inside_rounded_rect(x, y, size, radius):
                raw.extend((0, 0, 0, 0))
                continue
            # Borde sutil
            on_edge = (
                x <= pad or y <= pad or x >= size - 1 - pad or y >= size - 1 - pad
            ) and inside_rounded_rect(x, y, size, radius)
            if on_edge:
                raw.extend((*BORDER, 255))
                continue
            if in_bold_j(float(x), float(y), size):
                jt = (y - size * 0.18) / max(size * 0.62, 1)
                jr = lerp(J_BLUE[0], J_BLUE_DARK[0], min(1.0, jt))
                jg = lerp(J_BLUE[1], J_BLUE_DARK[1], min(1.0, jt))
                jb = lerp(J_BLUE[2], J_BLUE_DARK[2], min(1.0, jt))
                raw.extend((jr, jg, jb, 255))
            else:
                raw.extend((br, bg, bb, 255))
    return bytes(raw)


def write_png(path: Path, size: int) -> None:
    raw = render_icon(size)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def resize_png(src: Path, dest: Path, size: int) -> None:
    if shutil.which("sips"):
        subprocess.run(["sips", "-z", str(size), str(size), str(src), "--out", str(dest)], check=True)
        return
    write_png(dest, size)


def build_icns(master: Path, out_icns: Path) -> None:
    if platform.system() != "Darwin":
        return
    iconset = ICONS / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()
    mapping = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for name, size in mapping.items():
        if size == 1024:
            shutil.copy(master, iconset / name)
        else:
            resize_png(master, iconset / name, size)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out_icns)], check=True)
    shutil.rmtree(iconset)


def run_tauri_icon() -> None:
    npm = "npm.cmd" if platform.system() == "Windows" else "npm"
    subprocess.run(
        [npm, "run", "tauri", "icon", "src-tauri/icons/icon.png"],
        cwd=DESKTOP,
        check=True,
        shell=(platform.system() == "Windows"),
    )


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    master = ICONS / "icon.png"
    print("→ Render icon.png 1024px (J azul, fondo claro)…")
    write_png(master, 1024)
    for name, size in [("32x32.png", 32), ("128x128.png", 128), ("128x128@2x.png", 256)]:
        resize_png(master, ICONS / name, size)
    if platform.system() == "Darwin":
        print("→ icon.icns…")
        build_icns(master, ICONS / "icon.icns")
    print("→ tauri icon (icon.ico + tamaños Windows)…")
    run_tauri_icon()
    print(f"✓ Iconos listos: {ICONS}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR generando iconos: {exc}", file=sys.stderr)
        sys.exit(1)
