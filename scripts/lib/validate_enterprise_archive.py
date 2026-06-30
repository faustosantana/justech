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

# República Dominicana — Etapa 1 (NCF tradicional)
RD_REQUIRED_MODULES = ("l10n_do", "l10n_do_reports")
RD_EXCLUDED_STAGE1 = ("l10n_do_edi",)
RD_LATAM_MODULES = (
    "l10n_latam_base",
    "l10n_latam_invoice_document",
    "l10n_latam_check",
)


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


def parse_manifest_dependencies(manifest_path: Path) -> list[str]:
    text = manifest_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"['\"]depends['\"]\s*:\s*\[([^\]]+)\]", text, re.DOTALL)
    if not m:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))


def parse_pkg_info_version(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^Version:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def parse_release_version(release_path: Path) -> str | None:
    text = release_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"version_info\s*=\s*\((\d+),\s*(\d+)", text)
    if not m:
        return None
    serial = re.search(r"version_info\s*=\s*\([^)]+\)", text)
    serial_val = ""
    if serial:
        sm = re.search(r",\s*''\)|,\s*'(\d+)'\)", serial.group(0))
        if sm and sm.group(1):
            serial_val = sm.group(1)
    base = f"{m.group(1)}.{m.group(2)}"
    return f"{base}-{serial_val}" if serial_val else base


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


def find_source_tree_root(work: Path) -> Path | None:
    for release in work.rglob("odoo/release.py"):
        return release.parent.parent
    return None


def count_enterprise_modules(root: Path) -> int:
    return sum(1 for p in root.iterdir() if p.is_dir() and (p / "__manifest__.py").is_file())


def detect_archive_type(work: Path, addons_root: Path | None) -> str:
    if addons_root and (addons_root.parent / "release.py").is_file():
        return "full_enterprise_source"
    if addons_root and addons_root.name == "addons":
        parent = addons_root.parent
        if (parent / "release.py").is_file() or (parent.parent / "setup.py").is_file():
            return "full_enterprise_source"
    if addons_root and not (work / "odoo-bin").exists():
        return "enterprise_addons_only"
    if (work / "odoo-bin").exists() or any(work.rglob("odoo-bin")):
        return "full_enterprise_source"
    return "unknown"


def scan_latam_models(addons_root: Path) -> dict[str, list[str]]:
    models: dict[str, list[str]] = {}
    for mod_name in RD_LATAM_MODULES:
        mod_dir = addons_root / mod_name
        if not mod_dir.is_dir():
            continue
        found: list[str] = []
        for py_file in mod_dir.rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in re.finditer(r"_name\s*=\s*['\"](l10n_latam[^'\"]+)['\"]", text):
                name = m.group(1)
                if name not in found:
                    found.append(name)
        if found:
            models[mod_name] = sorted(found)
    return models


def validate(path: Path, expected_version: str, rd_stage1: bool = False) -> dict:
    result = {
        "archive": str(path),
        "archive_name": path.name,
        "archive_size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "archive_type": "unknown",
        "pkg_version": None,
        "release_version": None,
        "checks": {},
        "rd": {
            "modules": {},
            "latam_modules": {},
            "latam_models": {},
            "l10n_do_edi": "absent",
        },
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

        archive_type = detect_archive_type(work, root)
        result["archive_type"] = archive_type
        ok("structure", f"tipo={archive_type}, raíz addons: {root.relative_to(work)}")

        tree_root = find_source_tree_root(work)
        if tree_root:
            pkg = tree_root / "PKG-INFO"
            release = tree_root / "odoo" / "release.py"
            if pkg.is_file():
                result["pkg_version"] = parse_pkg_info_version(pkg)
                ok("pkg_info", result["pkg_version"] or "presente")
            if release.is_file():
                result["release_version"] = parse_release_version(release)
                ok("release_py", result["release_version"] or "presente")
            if result["pkg_version"] and not result["pkg_version"].startswith(expected_version):
                fail(
                    "version_compat",
                    f"PKG-INFO Version={result['pkg_version']}, esperado {expected_version}.*",
                )
            elif result["pkg_version"]:
                ok("version_compat", f"PKG-INFO {result['pkg_version']}")

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
                if mod == "web_enterprise" and ver and archive_type == "enterprise_addons_only":
                    if not ver.startswith(expected_version):
                        fail(
                            "version_compat",
                            f"web_enterprise version={ver}, esperado {expected_version}.*",
                        )
            else:
                fail(f"module_{mod}", "no encontrado")

        for mod in RECOMMENDED_MODULES:
            if (root / mod / "__manifest__.py").is_file():
                ok(f"module_{mod}", "presente")
            else:
                warn(f"module_{mod}", "no encontrado (opcional pre-l10n)")

        if rd_stage1:
            for mod in RD_REQUIRED_MODULES:
                mp = root / mod / "__manifest__.py"
                if mp.is_file():
                    ver = parse_manifest_version(mp) or "presente"
                    deps = parse_manifest_dependencies(mp)
                    result["rd"]["modules"][mod] = {
                        "present": True,
                        "version": ver,
                        "depends": deps,
                    }
                    ok(f"rd_{mod}", ver)
                else:
                    result["rd"]["modules"][mod] = {"present": False}
                    fail(f"rd_{mod}", "requerido para RD Etapa 1 — no encontrado")

            for mod in RD_EXCLUDED_STAGE1:
                mp = root / mod / "__manifest__.py"
                if mp.is_file():
                    result["rd"]["l10n_do_edi"] = "present"
                    warn(
                        f"rd_{mod}",
                        "presente en tarball — fuera de alcance Etapa 1 (eNCF)",
                    )
                else:
                    result["rd"]["l10n_do_edi"] = "absent"
                    ok(f"rd_{mod}", "ausente (correcto Etapa 1)")

            for mod in RD_LATAM_MODULES:
                mp = root / mod / "__manifest__.py"
                present = mp.is_file()
                result["rd"]["latam_modules"][mod] = {
                    "present": present,
                    "version": parse_manifest_version(mp) if present else None,
                }
                if present:
                    ok(f"rd_latam_{mod}", parse_manifest_version(mp) or "presente")
                else:
                    warn(f"rd_latam_{mod}", "no presente (puede ser normal en 19.0)")

            latam_models = scan_latam_models(root)
            result["rd"]["latam_models"] = latam_models
            if latam_models:
                detail = "; ".join(f"{m}: {len(v)} modelos" for m, v in latam_models.items())
                ok("rd_latam_models", detail)
            else:
                warn(
                    "rd_latam_models",
                    "ningún modelo l10n_latam* detectado en módulos LATAM del tarball",
                )

            l10n_do_mp = root / "l10n_do" / "__manifest__.py"
            if l10n_do_mp.is_file():
                deps = parse_manifest_dependencies(l10n_do_mp)
                has_latam_dep = any(d.startswith("l10n_latam") for d in deps)
                result["rd"]["l10n_do_latam_dependency"] = has_latam_dep
                if has_latam_dep:
                    ok("rd_l10n_do_deps", f"depende de LATAM: {', '.join(d for d in deps if d.startswith('l10n_latam'))}")
                else:
                    warn(
                        "rd_l10n_do_deps",
                        f"l10n_do sin dependencias l10n_latam (deps: {', '.join(deps) or 'ninguna'})",
                    )

    finally:
        shutil.rmtree(work, ignore_errors=True)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validar archivo Enterprise Odoo")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--version", default=REQUIRED_VERSION_PREFIX)
    parser.add_argument("--rd-stage1", action="store_true", help="Validación RD Etapa 1 (l10n_do, LATAM)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.archive.is_file():
        print(f"ERROR: no existe {args.archive}", file=sys.stderr)
        return 1

    result = validate(args.archive.resolve(), args.version, rd_stage1=args.rd_stage1)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Archivo: {result['archive_name']}")
        print(f"Tamaño: {result['archive_size_bytes']} bytes")
        print(f"SHA256: {result['sha256']}")
        print(f"Tipo: {result['archive_type']}")
        if result.get("pkg_version"):
            print(f"PKG-INFO: {result['pkg_version']}")
        if result.get("release_version"):
            print(f"release.py: {result['release_version']}")
        for name, check in result["checks"].items():
            print(f"{check['status']:4} {name}: {check.get('detail', '')}")
        if args.rd_stage1 and result.get("rd", {}).get("latam_models"):
            print("--- Modelos l10n_latam ---")
            for mod, models in result["rd"]["latam_models"].items():
                print(f"  {mod}: {', '.join(models)}")
        for w in result["warnings"]:
            print(f"WARN {w}")
        for e in result["errors"]:
            print(f"FAIL {e}")
        print("RESULTADO:", "OK" if result["ok"] else "FALLOS")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
