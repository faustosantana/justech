#!/usr/bin/env python3
"""
Generate a complete inventory of official Odoo 19 modules from filesystem manifests.

Designed to run inside the Odoo Docker container (or any host with addon paths mounted).
Outputs JSON + CSV + text lists under evidence/.

Usage (VPS):
  docker exec hellenia-dev-odoo-1 python3 /opt/odoo/custom/../scripts/generate-odoo19-module-inventory.py
  # Or copy script and run with explicit paths:
  python3 generate-odoo19-module-inventory.py --output /tmp/evidence
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ADDON_ROOTS = [
    "/opt/odoo/enterprise/addons",
    "/usr/lib/python3/dist-packages/odoo/addons",
]

KEYWORDS = [
    "NCF", "ncf", "DGII", "dgii", "Fiscal", "fiscal", "LATAM", "latam", "l10n_latam",
    "Dominican", "dominican", "República", "document_type", "document.type",
    "Invoice Document", "Fiscal Localization", "fiscal_localization", "invoice_document",
    "B01", "B02", "B03", "B04", "B11", "B13", "E31", "E32", "E33", "E34",
    "606", "607", "608", "l10n_do_edi", "comprobante", "ncf_sequence",
]

FILE_BUCKETS = {
    "models": lambda p: p.parts[-2] == "models" and p.suffix == ".py" and p.name != "__init__.py",
    "views": lambda p: p.parts[-2] == "views" and p.suffix == ".xml",
    "wizard": lambda p: p.parts[-2] == "wizard" and p.suffix == ".py",
    "report": lambda p: p.parts[-2] == "report" and p.suffix in {".xml", ".py"},
    "security": lambda p: p.name == "ir.model.access.csv",
    "data": lambda p: p.parts[-2] == "data" and p.suffix == ".xml" and "template" not in p.parts,
    "csv": lambda p: p.suffix == ".csv",
    "xml": lambda p: p.suffix == ".xml",
}


def parse_manifest(manifest_path: Path) -> dict[str, Any]:
    raw = manifest_path.read_text(encoding="utf-8", errors="replace")
    # Strip coding header if present
    raw = re.sub(r"^#.*coding.*\n", "", raw)
    data = ast.literal_eval(raw)
    return data if isinstance(data, dict) else {}


def classify_module(name: str, manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    category = manifest.get("category") or ""
    license_ = manifest.get("license", "")
    auto_install = manifest.get("auto_install", False)
    is_enterprise = "enterprise" in str(manifest_path)
    is_hidden = category.startswith("Hidden")
    is_l10n = name.startswith("l10n_")
    is_accounting = "Accounting" in category
    fiscal_kw = any(k in json.dumps(manifest).lower() for k in ("fiscal", "ncf", "dgii", "latam"))

    if auto_install is True:
        auto_kind = "true"
    elif isinstance(auto_install, list):
        auto_kind = "conditional"
    else:
        auto_kind = "false"

    return {
        "origin": "enterprise" if is_enterprise else "community",
        "license": license_,
        "enterprise": is_enterprise,
        "community": not is_enterprise,
        "auto_install": auto_kind,
        "hidden": is_hidden,
        "localization": is_l10n or "Localizations" in category,
        "accounting": is_accounting,
        "fiscal": fiscal_kw,
    }


def scan_module_files(module_dir: Path) -> tuple[dict[str, int], dict[str, list[str]]]:
    counts: dict[str, int] = defaultdict(int)
    samples: dict[str, list[str]] = defaultdict(list)
    for root, _, files in os.walk(module_dir):
        for fname in files:
            if fname.endswith(".pyc") or fname.endswith(".po") or fname.endswith(".pot"):
                continue
            rel = Path(root, fname).relative_to(module_dir)
            for bucket, pred in FILE_BUCKETS.items():
                if pred(rel):
                    counts[bucket] += 1
                    if len(samples[bucket]) < 12:
                        samples[bucket].append(str(rel))
    return dict(counts), dict(samples)


def content_keyword_hits(module_dir: Path, keywords: list[str], max_files: int = 30) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    for root, _, files in os.walk(module_dir):
        for fname in files:
            if not fname.endswith((".py", ".xml", ".csv", ".js", ".json")):
                continue
            path = Path(root, fname)
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            found = sorted(set(m.group(0) for m in pattern.finditer(text)))
            if found:
                hits.append({
                    "file": str(path.relative_to(module_dir)),
                    "snippets": found[:20],
                })
                if len(hits) >= max_files:
                    return hits
    return hits


def discover_modules(addon_roots: list[str]) -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for root in addon_roots:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        for entry in sorted(root_path.iterdir()):
            if not entry.is_dir():
                continue
            manifest = entry / "__manifest__.py"
            if manifest.is_file():
                modules[entry.name] = manifest
    return modules


def build_inventory(addon_roots: list[str]) -> dict[str, Any]:
    manifests = discover_modules(addon_roots)
    modules_out: list[dict[str, Any]] = []
    keyword_index: dict[str, list[str]] = defaultdict(list)

    for name in sorted(manifests):
        manifest_path = manifests[name]
        module_dir = manifest_path.parent
        try:
            manifest = parse_manifest(manifest_path)
        except (SyntaxError, ValueError) as exc:
            modules_out.append({
                "technical_name": name,
                "manifest_error": str(exc),
                "manifest_path": str(manifest_path),
            })
            continue

        classification = classify_module(name, manifest, manifest_path)
        depends = manifest.get("depends", [])
        data_files = manifest.get("data", []) + manifest.get("demo", [])
        file_counts, files_sample = scan_module_files(module_dir)

        kw_in_manifest = [k for k in KEYWORDS if k.lower() in json.dumps(manifest).lower()]
        for k in kw_in_manifest:
            keyword_index[k].append(name)

        entry = {
            "technical_name": name,
            "name": manifest.get("name", ""),
            "version": manifest.get("version", ""),
            "category": manifest.get("category", ""),
            "license": manifest.get("license", ""),
            "depends": depends,
            "auto_install": manifest.get("auto_install", False),
            "application": manifest.get("application", False),
            "installable": manifest.get("installable", True),
            "external_dependencies": manifest.get("external_dependencies", {}),
            "data_files": data_files,
            "manifest_path": str(manifest_path),
            "classification": classification,
            "keyword_hits": kw_in_manifest,
            "file_counts": file_counts,
            "files_sample": files_sample,
        }
        modules_out.append(entry)

    # Deep scan: modules with fiscal/LATAM relevance
    fiscal_names = {
        m["technical_name"]
        for m in modules_out
        if m.get("classification", {}).get("localization")
        or m.get("classification", {}).get("fiscal")
        or m["technical_name"].startswith("l10n_")
        or any(k in (m.get("keyword_hits") or []) for k in ("NCF", "DGII", "latam", "fiscal"))
    }
    deep_scan: list[dict[str, Any]] = []
    for m in modules_out:
        tn = m.get("technical_name")
        if tn not in fiscal_names:
            continue
        module_dir = Path(m["manifest_path"]).parent
        content_hits = content_keyword_hits(module_dir, KEYWORDS)
        deep_scan.append({
            "technical_name": tn,
            "manifest": {
                k: m.get(k) if k != "manifest_path" else None
                for k in (
                    "name", "version", "license", "category", "depends",
                    "auto_install", "external_dependencies", "data_files",
                )
            },
            "file_counts": m.get("file_counts", {}),
            "files_sample": m.get("files_sample", {}),
            "content_keyword_hits": content_hits,
            "content_hit_files": len(content_hits),
            "origin": m.get("classification", {}).get("origin"),
        })

    classifications = [m.get("classification", {}) for m in modules_out if m.get("classification")]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "addon_roots": addon_roots,
        "total_modules": len(modules_out),
        "by_origin": dict(Counter(c.get("origin") for c in classifications)),
        "by_license": dict(Counter(m.get("license") for m in modules_out)),
        "auto_install_true": sum(1 for c in classifications if c.get("auto_install") == "true"),
        "auto_install_conditional": sum(1 for c in classifications if c.get("auto_install") == "conditional"),
        "hidden": sum(1 for c in classifications if c.get("hidden")),
        "localization_modules": sorted(
            m["technical_name"] for m in modules_out
            if m.get("classification", {}).get("localization")
        ),
    }

    return {
        "summary": summary,
        "modules": modules_out,
        "keyword_index": dict(keyword_index),
        "deep_scan_count": len(deep_scan),
        "deep_scan": deep_scan,
    }


def write_outputs(inv: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "odoo19-module-inventory.json", "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=2, ensure_ascii=False, default=str)

    fiscal = {
        "deep_scan_count": inv["deep_scan_count"],
        "all_l10n_modules": [
            m["technical_name"] for m in inv["modules"]
            if m.get("technical_name", "").startswith("l10n_")
        ],
        "modules": inv["deep_scan"],
    }
    with open(output_dir / "odoo19-fiscal-deep-scan.json", "w", encoding="utf-8") as f:
        json.dump(fiscal, f, indent=2, ensure_ascii=False, default=str)

    with open(output_dir / "odoo19-all-modules.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "technical_name", "display_name", "origin", "license", "category", "version",
            "auto_install", "application", "installable", "depends", "data_files_count", "keyword_hits",
        ])
        for m in inv["modules"]:
            c = m.get("classification", {})
            writer.writerow([
                m.get("technical_name"),
                m.get("name"),
                c.get("origin"),
                m.get("license"),
                m.get("category"),
                m.get("version"),
                m.get("auto_install"),
                m.get("application"),
                m.get("installable"),
                "|".join(m.get("depends", [])),
                len(m.get("data_files", [])),
                "|".join(m.get("keyword_hits", [])),
            ])

    enterprise = sorted(
        m["technical_name"] for m in inv["modules"]
        if m.get("classification", {}).get("enterprise")
    )
    (output_dir / "odoo19-enterprise-modules.txt").write_text(
        "\n".join(enterprise) + "\n", encoding="utf-8"
    )

    l10n = sorted(
        m["technical_name"] for m in inv["modules"]
        if m.get("technical_name", "").startswith("l10n_")
    )
    (output_dir / "odoo19-l10n-modules.txt").write_text(
        "\n".join(l10n) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Odoo 19 official module inventory")
    parser.add_argument(
        "--addon-root", action="append", dest="addon_roots",
        help="Addon root path (repeatable). Defaults to Enterprise + Community paths.",
    )
    parser.add_argument(
        "--output", default="evidence",
        help="Output directory (default: evidence)",
    )
    args = parser.parse_args()
    roots = args.addon_roots or DEFAULT_ADDON_ROOTS
    output_dir = Path(args.output)

    inv = build_inventory(roots)
    write_outputs(inv, output_dir)

    s = inv["summary"]
    print(f"OK: {s['total_modules']} modules scanned")
    print(f"  Enterprise: {s['by_origin'].get('enterprise', 0)}")
    print(f"  Community:  {s['by_origin'].get('community', 0)}")
    print(f"  Auto-install true: {s['auto_install_true']}")
    print(f"  Auto-install conditional: {s['auto_install_conditional']}")
    print(f"  Hidden: {s['hidden']}")
    print(f"  l10n_*: {len(s['localization_modules'])}")
    print(f"  Deep fiscal scan: {inv['deep_scan_count']}")
    print(f"  Output: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
