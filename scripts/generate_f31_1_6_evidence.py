#!/usr/bin/env python3
"""Generate F31.1.6 module registry final evidence."""
from __future__ import annotations

import ast
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "custom"
EVIDENCE = ROOT / "evidence" / "f31-1-6-module-registry-final"
SKIP = {"justech_modules_test", "justech_report_templates_test"}


def load_manifests():
    out = {}
    for path in sorted(CUSTOM.glob("*/__manifest__.py")):
        name = path.parent.name
        if name in SKIP:
            continue
        out[name] = ast.literal_eval(path.read_text())
    return out


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifests = load_manifests()
    rows = []
    missing_register = []
    for name, m in sorted(manifests.items()):
        reg = m.get("justech_register") or {}
        if not reg and name not in SKIP:
            missing_register.append(name)
        feats = reg.get("features") or []
        rows.append(
            {
                "technical_name": name,
                "module_code": reg.get("module_code", name),
                "version": m.get("version", ""),
                "always_enabled": reg.get("always_enabled", False),
                "has_justech_register": bool(reg),
                "feature_codes": "|".join(f.get("code", "") for f in feats),
                "commercial_deps": "|".join(reg.get("dependencies") or []),
            }
        )
    with (EVIDENCE / "MODULE_REGISTRY.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    result = {
        "phase": "F31.1.6",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "production_modules": len(rows),
        "with_justech_register": sum(1 for r in rows if r["has_justech_register"]),
        "missing_register": missing_register,
        "all_registered": not missing_register,
    }
    (EVIDENCE / "REGISTRY_RESULT.json").write_text(json.dumps(result, indent=2))
    (EVIDENCE / "README.md").write_text(
        f"# F31.1.6 Module Registry Final\n\n"
        f"- Modules: {result['production_modules']}\n"
        f"- With justech_register: {result['with_justech_register']}\n"
        f"- Status: {'PASS' if result['all_registered'] else 'FAIL'}\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
