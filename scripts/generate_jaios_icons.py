#!/usr/bin/env python3
"""Genera iconos oficiales JAIOS — funciona en Mac, Linux y Windows."""

from __future__ import annotations

import math
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

BLUE_TOP = (59, 130, 246)
BLUE_BOTTOM = (29, 78, 216)


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def render_icon(size: int) -> bytes:
    mask_r = size * 0.22
    j_left = 0.38 * size
    j_right = 0.62 * size
    j_top = 0.22 * size
    j_bottom = 0.78 * size
    j_thickness = 0.11 * size
    j_hook_bottom = 0.72 * size
    j_hook_left = 0.28 * size
    hook_cx = (j_left + j_right) / 2
    hook_rx = (j_right - j_hook_left) * 0.55
    hook_ry = (j_bottom - j_hook_bottom) * 0.9 + j_thickness

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        t = y / max(size - 1, 1)
        br, bg, bb = (
            lerp(BLUE_TOP[0], BLUE_BOTTOM[0], t),
            lerp(BLUE_TOP[1], BLUE_BOTTOM[1], t),
            lerp(BLUE_TOP[2], BLUE_BOTTOM[2], t),
        )
        for x in range(size):
            cx = min(x, size - 1 - x)
            cy = min(y, size - 1 - y)
            if cx < mask_r and cy < mask_r:
                dx = mask_r - cx
                dy = mask_r - cy
                if dx * dx + dy * dy > mask_r * mask_r:
                    raw.extend((0, 0, 0, 0))
                    continue

            in_stem = j_left <= x <= j_right and j_top <= y <= j_bottom
            in_top = j_left <= x <= j_right + 0.08 * size and j_top <= y <= j_top + j_thickness
            dxh = (x - hook_cx) / max(hook_rx, 1)
            dyh = (y - j_hook_bottom) / max(hook_ry, 1)
            in_hook = (
                dxh * dxh + dyh * dyh <= 1.0
                and y >= j_hook_bottom - j_thickness
                and x <= j_right + j_thickness * 0.3
            )
            if in_stem or in_top or in_hook:
                raw.extend((255, 255, 255, 255))
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
    print("→ Render icon.png 1024px…")
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
