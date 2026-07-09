#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera reporte HTML de auditoría visual DEV-1 (datos reales erp.justech.do)."""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_html(data: dict) -> str:
    checks = data.get("checks", [])
    rows = "".join(
        f"<tr><td>{html.escape(c['name'])}</td>"
        f"<td>{'✅' if c['ok'] else '❌'}</td>"
        f"<td>{html.escape(str(c.get('detail', '')))}</td></tr>"
        for c in checks
    )
    m = data.get("metrics", {})
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>DEV-1 Validación erp.justech.do</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; }}
h1 {{ color: #1B3A5C; }}
.pass {{ color: #059669; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; }}
th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: left; }}
th {{ background: #1B3A5C; color: #fff; }}
.metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }}
.card {{ background: #fff; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }}
</style></head><body>
<h1>Validación DEV-1 — erp.justech.do</h1>
<p>Generado: {html.escape(data.get('ts', ''))} · BD: {html.escape(data.get('database', ''))}</p>
<p class="pass">Resultado: {'PASS' if data.get('passed') else 'FAIL'}</p>
<div class="metrics">
  <div class="card"><strong>Asientos posted</strong><br>{m.get('posted_moves')}</div>
  <div class="card"><strong>NCF Adel</strong><br>{m.get('ncf_adel')}</div>
  <div class="card"><strong>Conciliaciones</strong><br>{m.get('reconciles')}</div>
  <div class="card"><strong>Pagos activos</strong><br>{m.get('payments')}</div>
  <div class="card"><strong>GL balanceado</strong><br>{'Sí' if m.get('gl_balanced') else 'No'}</div>
  <div class="card"><strong>Justech fiscal ON</strong><br>{m.get('fiscal_enabled_companies')} empresas</div>
</div>
<h2>Checks ({len(checks)})</h2>
<table><tr><th>Check</th><th>OK</th><th>Detalle</th></tr>{rows}</table>
<p><em>Nota: acceso web externo retorna 403; validación vía Odoo shell + ORM.</em></p>
</body></html>"""


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = json.loads(src.read_text())
    dst.write_text(build_html(data), encoding="utf-8")
    print(dst)
