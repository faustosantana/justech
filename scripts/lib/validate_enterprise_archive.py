#!/usr/bin/env python3
"""Validación exhaustiva de archivo Enterprise del portal Odoo (sin instalar)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

REQUIRED_VERSION_PREFIX = "19.0"
MIN_ARCHIVE_BYTES = 500_000  # Enterprise addons suele ser >500KB
REQUIRED_MODULES = ("web_enterprise",)
RECOMMENDED_MODULES = ("l10n_do_edi", "l10n_do_reports")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest_version(manifest_path: Path) -> str | None:
    text = manifest_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"['\"]version['\"]\s*:\s*['\"]([^'\"]+)['\"]", text)
    return m.group(1) if m else None


def test_archive_integrity(path: Path) -> None:
    name = path.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad:
                raise ValueError(f"ZIP corrupto en entrada: {bad}")
    elif name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path, "r:gz") as tf:
            if not tf.getmembers():
                raise ValueError("TAR vacío")
    elif name.endswith(".gz"):
        with gzip.open(path, "rb") as gf:
            while gf.read(1024 * 1024):
                pass
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")


def extract_archive(path: Path, dest: Path) -> None:
    name = path.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest)
    elif name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path, "r:gz") as tf:
            tf.extractall(dest)
    else:
        raise ValueError(f"Formato no soportado: {path}")


def find_enterprise_root(work: Path) -> Path | None:
    if (work / "web_enterprise" / "__manifest__.py").is_file():
        return work
    for manifest in work.rglob("web_enterprise/__manifest__.py"):
        return manifest.parent.parent
    return None


def count_enterprise_modules(root: Path) -> int:
    return sum(1 for p in root.iterdir() if p.is_dir() and (p / "__manifest__.py").is_file())


def looks_like_community_full_tree(work: Path) -> bool:
    """Enterprise Sources = solo addons; no debe ser tarball Community completo."""
    markers = ("odoo-bin", "setup.py", "debian/odoo.conf")
    for m in markers:
        if (work / m).exists():
            return True
    return any(p.name == "odoo-bin" for p in work.rglob("odoo-bin"))


def validate(path: Path, expected_version: str) -> dict:
    result = {
        "archive": str(path),
        "archive_name": path.name,
        "archive_size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "checks": {},
        "ok": True,
        "errors": [],
        "warnings": [],
    }

    def ok(name: str, detail: str = ""):
        result["checks"][name] = {"status": "OK", "detail": detail}

    def fail(name: str, detail: str):
        result["checks"][name] = {"status": "FAIL", "detail": detail}
        result["errors"].append(f"{name}: {detail}")
        result["ok"] = False

    def warn(name: str, detail: str):
        result["checks"][name] = {"status": "WARN", "detail": detail}
        result["warnings"].append(f"{name}: {detail}")

    if path.stat().st_size < MIN_ARCHIVE_BYTES:
        fail("size", f"Archivo muy pequeño ({path.stat().st_size} bytes)")

    try:
        test_archive_integrity(path)
        ok("integrity", "sin corrupción detectada")
    except Exception as e:
        fail("integrity", str(e))

    work = Path(tempfile.mkdtemp(prefix="hellenia-ent-val-"))
    try:
        extract_archive(path, work)
        root = find_enterprise_root(work)
        if not root:
            fail("structure", "no se encontró web_enterprise/__manifest__.py")
            return result
        ok("structure", f"raíz addons: {root.relative_to(work)}")

        if looks_like_community_full_tree(work):
            warn(
                "archive_type",
                "parece tarball Community completo; se esperan solo addons Enterprise",
            )

        mod_count = count_enterprise_modules(root)
        if mod_count < 10:
            warn("module_count", f"solo {mod_count} módulos detectados (esperado >>10)")
        else:
            ok("module_count", str(mod_count))

        for mod in REQUIRED_MODULES:
            mp = root / mod / "__manifest__.py"
            if mp.is_file():
                ver = parse_manifest_version(mp)
                ok(f"module_{mod}", ver or "presente")
                if mod == "web_enterprise" and ver:
                    if not ver.startswith(expected_version):
                        fail(
                            "version_compat",
                            f"web_enterprise version={ver}, esperado {expected_version}.*",
                        )
                    else:
                        ok("version_compat", f"web_enterprise {ver}")
            else:
                fail(f"module_{mod}", "no encontrado")

        for mod in RECOMMENDED_MODULES:
            if (root / mod / "__manifest__.py").is_file():
                ok(f"module_{mod}", "presente")
            else:
                warn(f"module_{mod}", "no encontrado (opcional pre-l10n)")

    finally:
        shutil.rmtree(work, ignore_errors=True)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validar archivo Enterprise Odoo")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--version", default=REQUIRED_VERSION_PREFIX)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.archive.is_file():
        print(f"ERROR: no existe {args.archive}", file=sys.stderr)
        return 1

    result = validate(args.archive.resolve(), args.version)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Archivo: {result['archive_name']}")
        print(f"Tamaño: {result['archive_size_bytes']} bytes")
        print(f"SHA256: {result['sha256']}")
        for name, check in result["checks"].items():
            print(f"{check['status']:4} {name}: {check.get('detail', '')}")
        for w in result["warnings"]:
            print(f"WARN {w}")
        for e in result["errors"]:
            print(f"FAIL {e}")
        print("RESULTADO:", "OK" if result["ok"] else "FALLOS")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
