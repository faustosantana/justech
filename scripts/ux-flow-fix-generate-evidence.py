#!/usr/bin/env python3
"""Generate UX-FLOW-FIX evidence deliverables."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "ux-flow-fix"

FIXES = [
    ("1", "Tipo de ingreso 607", "Campo visible en pestaña Información Fiscal con ayuda DGII"),
    ("2", "Alerta multimoneda", "Banner amigable en cotización y factura si falta tasa"),
    ("3", "Traducciones", "Menús contables EN + etiquetas factura en español"),
    ("4", "Void NCF", "Botón oculto EN; acción «Anular comprobante fiscal»"),
    ("5", "Vendor", "Etiqueta «Proveedor» en facturas de compra"),
    ("6", "RNC en contactos", "Columna RNC/Cédula visible; campo técnico oculto"),
    ("7", "Navegación NCF", "Menús numerados 1→2→3 + guías en formularios"),
    ("8", "Módulos del Cliente", "Renombrado «Licencias y Personalizaciones»"),
    ("9", "Auditorías", "«Auditoría Fiscal» vs «Auditoría de Cambios»"),
    ("10", "Config multimoneda", "Ayuda contextual en producto Venta/Compra"),
]


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    val_path = EVIDENCE / "UX_FLOW_FIX_VALIDATION.json"
    health_path = EVIDENCE / "UX_FLOW_FIX_HEALTHCHECK.json"
    validation = {}
    health = {"status": "UNKNOWN"}
    if val_path.exists():
        validation = json.loads(val_path.read_text(encoding="utf-8"))
    if health_path.exists():
        health = json.loads(health_path.read_text(encoding="utf-8"))

    checks = validation.get("checks", {})
    fixed = sum(1 for k, v in checks.items() if v.get("pass"))
    pending = validation.get("pending", [])

    (EVIDENCE / "UX_FLOW_FIX_REPORT.md").write_text(
        "\n".join([
            "# UX-FLOW-FIX — Informe de cierre",
            "",
            f"**Fecha:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Base:** `{validation.get('database', 'N/A')}`",
            f"**Resultado:** {validation.get('summary', 'N/A')}",
            "",
            "## Alcance (10 hallazgos)",
            "",
            "| # | Hallazgo | Estado |",
            "|---|----------|--------|",
        ] + [
            f"| {n} | {title} | {'✓' if f'fix_{n.zfill(2)}' in str(checks) and all(v.get('pass') for k,v in checks.items() if k.startswith(f'fix_{n.zfill(2)}')) else 'Ver validación'} |"
            for n, title, _ in FIXES
        ] + [
            "",
            f"**Validaciones PASS:** {fixed} / {len(checks)}",
            f"**Healthcheck:** {health.get('status', health.get('RESULTADO', 'N/A'))}",
            "",
        ]),
        encoding="utf-8",
    )

    (EVIDENCE / "UX_FLOW_FIX_SUMMARY.md").write_text(
        "\n".join([
            "# UX-FLOW-FIX — Resumen ejecutivo",
            "",
            f"- Hallazgos en alcance: **10**",
            f"- Validación global: **{validation.get('summary', 'N/A')}**",
            f"- Pendientes: **{len(pending)}** ({', '.join(pending) if pending else 'ninguno'})",
            f"- Healthcheck: **{health.get('status', 'N/A')}**",
            "",
            "## Módulos tocados (solo UX)",
            "- `hellenia_ux` 19.0.1.3.0",
            "- `hellenia_ui` 19.0.1.0.8",
            "- `justech_admin` (etiquetas visibles)",
            "- `justech_global_audit_log` (menú)",
            "- `justech_l10n_do_reports` (menú auditoría fiscal)",
            "",
            "## Sin cambios en",
            "COA, DGII lógica, NCF motor, impuestos, PDFs, licencias motor, permisos, API.",
        ]),
        encoding="utf-8",
    )

    (EVIDENCE / "UX_FLOW_FIX_BEFORE_AFTER.md").write_text(
        "\n".join([
            "# UX-FLOW-FIX — Antes / Después",
            "",
            "| # | Antes | Después |",
            "|---|-------|---------|",
            "| 1 | Campo 607 no visible | Tipo de ingreso (607) en pestaña fiscal con ayuda |",
            "| 2 | Sin aviso de tasa | Banner amigable con ruta a Tasas de cambio |",
            "| 3 | Reporting, Invoice Lines EN | Informes contables, Líneas de factura ES |",
            "| 4 | Void NCF | Anular comprobante fiscal (EN oculto) |",
            "| 5 | Vendor | Proveedor |",
            "| 6 | RNC oculto en lista | Columna RNC/Cédula visible por defecto |",
            "| 7 | Tipos/Rangos/Consumo ambiguos | 1→2→3 numerado + guías |",
            "| 8 | Módulos del Cliente | Licencias y Personalizaciones |",
            "| 9 | Dos «Auditoría» | Auditoría Fiscal / Auditoría de Cambios |",
            "| 10 | Precios sin contexto | Banner explicativo comercial vs contable |",
        ]),
        encoding="utf-8",
    )
    print(f"Evidence written to {EVIDENCE}")


if __name__ == "__main__":
    main()
