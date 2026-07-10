#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera informe markdown por empresa desde snapshots y validación."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 4:
        print("Usage: fiscal-standard-report.py pre.json validate.json post.json", file=sys.stderr)
        sys.exit(1)

    pre = load(sys.argv[1])
    val = load(sys.argv[2])
    post = load(sys.argv[3])

    company = val.get("company", pre.get("company", {}).get("name", "?"))
    cid = val.get("company_id", pre.get("company", {}).get("id", "?"))
    approved = val.get("approved", False)
    status = "APROBADO" if approved else "NO APROBADO"
    errors = val.get("errors", [])
    tests = val.get("tests", [])
    passed = sum(1 for t in tests if t.get("ok"))
    failed = [t for t in tests if not t.get("ok")]

    lines = [
        f"# Validación Estándar Fiscal — {company} (id={cid})",
        "",
        f"**Estado:** {status}",
        f"**Fecha:** {datetime.now(timezone.utc).isoformat()}",
        f"**Entorno:** erp.justech.do / justech_dev",
        "",
        "## Resumen pruebas",
        "",
        f"- Total: {len(tests)} | PASS: {passed} | FAIL: {len(failed)}",
        "",
    ]

    if errors:
        lines += ["## Errores", ""]
        for e in errors:
            lines.append(f"- `{e}`")
        lines.append("")

    lines += [
        "## Secuencias utilizadas (prueba)",
        "",
    ]
    for seq in val.get("sequences_used", []):
        lines.append(f"- `{seq}`")
    lines.append("")

    lines += ["## Último / Próximo NCF por prefijo", "", "| Prefijo | Último | Próximo |", "|---------|--------|---------|"]
    last = val.get("last_ncf_by_prefix", {})
    nxt = val.get("next_ncf_by_prefix", {})
    for prefix in sorted(set(list(last.keys()) + list(nxt.keys()))):
        lines.append(f"| {prefix} | {last.get(prefix, '—')} | {nxt.get(prefix, '—')} |")
    lines.append("")

    lines += [
        "## Métricas pre → post",
        "",
        "| Métrica | Pre | Post |",
        "|---------|-----|------|",
    ]
    pg = pre.get("global", {})
    pog = post.get("global", {})
    for key in ("posted_moves", "reconciles", "payments", "ncf_justech_total"):
        lines.append(f"| {key} | {pg.get(key, '—')} | {pog.get(key, '—')} |")
    lines.append(f"| GL balanceado | {pg.get('gl_balanced')} | {pog.get('gl_balanced')} |")
    lines.append("")

    lines += ["## Resultado detallado", "", "| Prueba | OK | Detalle |", "|--------|----|---------|"]
    for t in tests:
        detail = t.get("detail")
        if isinstance(detail, (dict, list)):
            detail = json.dumps(detail, ensure_ascii=False)[:120]
        lines.append(f"| {t['name']} | {'✓' if t['ok'] else '✗'} | {detail or ''} |")
    lines.append("")

    lines += [
        "## Riesgos",
        "",
    ]
    if approved:
        lines.append("- Bajo a medio: documentos de prueba creados en dev (reversibles con backup).")
        lines.append("- Histórico Adel verificado sin modificación.")
    else:
        lines.append("- **ALTO:** Validación fallida — no continuar a siguiente empresa.")
        lines.append("- Restaurar backup de esta empresa antes de reintentar.")
    lines.append("")

    rec = "Continuar a siguiente empresa." if approved else "**DETENER** — corregir y revalidar."
    lines += [f"## Recomendación", "", rec, ""]

    print("\n".join(lines))


if __name__ == "__main__":
    main()
