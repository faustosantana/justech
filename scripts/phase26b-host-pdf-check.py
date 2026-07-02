#!/usr/bin/env python3
"""Complementa validation.json con checks pdftotext en el host (post-descarga)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    evidence = Path(sys.argv[1])
    val_path = evidence / "validation.json"
    if not val_path.is_file():
        print("validation.json missing", file=sys.stderr)
        return 1

    parts = []
    for name in (
        "01_picking_done.pdf",
        "03_from_sale_order.pdf",
        "04_from_invoice.pdf",
    ):
        pdf = evidence / name
        if pdf.is_file():
            parts.append(
                subprocess.check_output(
                    ["pdftotext", str(pdf), "-"], stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
            )
    sample = "\n".join(parts)

    with val_path.open() as f:
        data = json.load(f)

    checks = {
        "host_observations": "OBSERVACIONES" in sample,
        "host_legal_legend": "certifica" in sample.lower()
        and "factura fiscal" in sample.lower(),
        "host_responsable_vendedor": "RESPONSABLE" in sample.upper()
        and "VENDEDOR" in sample.upper(),
        "host_green_band": "No. Conduce" in sample and "Fecha entrega" in sample,
        "host_warehouse_not_company_name": "Almacén: Hellenia, S.R.L." not in sample,
    }
    for key, ok in checks.items():
        data["tests"][key] = {
            "status": "PASS" if ok else "FAIL",
            "detail": "host pdftotext",
        }
        if not ok:
            data["ok"] = False
            data["pass"] = False

    with val_path.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(json.dumps({"host_checks": checks, "pass": data.get("pass")}))
    return 0 if data.get("pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
