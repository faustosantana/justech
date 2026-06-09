#!/usr/bin/env python3
"""Genera reportes QA de auditoría de módulos JAIOS."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / ".qa"
FRONTEND = ROOT / "frontend" / "src"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8000")

MODULES = [
    ("Dashboard ejecutivo", "/dashboard", "Operativo", "KPIs parciales — ventas mes RD$ y borradores pendientes de enriquecer", "Ampliar executive dashboard service", "Media"),
    ("Búsqueda global", "/search", "Operativo", "M365 no conectado (mensaje honesto)", "Ninguna crítica", "Baja"),
    ("Documentos", "/documents", "Operativo", "—", "Ninguna", "Baja"),
    ("Inteligencia de precios", "/prices", "Operativo", "—", "Ninguna", "Baja"),
    ("Borradores cotización", "/prices/drafts", "Operativo", "—", "Ninguna", "Baja"),
    ("Centro de trabajo", "/work", "Operativo", "—", "Ninguna", "Baja"),
    ("Tareas", "/tasks", "Operativo", "—", "Ninguna", "Baja"),
    ("Notificaciones", "/notifications", "Operativo", "—", "Ninguna", "Baja"),
    ("DGCP", "/dgcp", "Operativo", "—", "Ninguna", "Baja"),
    ("Expedientes DGCP", "/oportunidades", "Operativo", "Renombrado — fuente DGCP explícita", "Documentar en onboarding", "Baja"),
    ("Odoo", "/odoo", "Operativo", "Depende conexión Odoo real", "Validar con tenant productivo", "Media"),
    ("Microsoft 365", "/m365", "Parcial", "OAuth no habilitado — estado honesto", "Conectar Azure AD cuando esté listo", "Media"),
    ("Empresas y proveedores", "/empresas", "Corrección aplicada", "CRUD mínimo implementado", "Seed datos reales + integración Odoo automática", "Alta"),
    ("Configuración", "/configuracion", "Corrección aplicada", "Preferencias locales + links integraciones", "Persistir prefs en backend", "Media"),
    ("Administración", "/admin", "Operativo", "Requiere rol admin", "Auditoría básica ampliar", "Media"),
]

SIDEBAR_READINESS = [
    ("Inicio / Dashboard", "/dashboard", "Listo para revisión", "Carga, KPIs, acciones rápidas"),
    ("Operaciones / Work", "/work", "Listo para revisión", "Hub operativo"),
    ("Operaciones / Tareas", "/tasks", "Listo para revisión", "CRUD tareas"),
    ("Operaciones / Notificaciones", "/notifications", "Listo para revisión", "Listado + marcar leídas"),
    ("Comercial / Odoo", "/odoo", "Validación parcial", "Requiere Odoo conectado"),
    ("Comercial / Cotizaciones", "/prices/drafts", "Listo para revisión", "Borradores"),
    ("Comercial / Precios", "/prices", "Listo para revisión", "Búsqueda precios"),
    ("Licitaciones / DGCP", "/dgcp", "Listo para revisión", "Dashboard + listado"),
    ("Licitaciones / Expedientes", "/oportunidades", "Listo para revisión", "Listado DGCP completo"),
    ("Documentos", "/documents", "Listo para revisión", "Repositorio"),
    ("Plataforma / Búsqueda", "/search", "Listo para revisión", "Enterprise search"),
    ("Plataforma / M365", "/m365", "Validación parcial", "No conectado — sin Próximamente"),
    ("Plataforma / Empresas", "/empresas", "Corrección aplicada", "CRUD mínimo"),
    ("Plataforma / Configuración", "/configuracion", "Corrección aplicada", "Prefs + integraciones"),
    ("Administración", "/admin", "Listo para revisión", "Solo usuarios admin"),
]

DEAD_BUTTONS = [
    ("M365", "/m365", "Conectar Microsoft 365", "Deshabilitado con tooltip OAuth pendiente", "OK — explicación clara"),
    ("Empresas detalle", "/empresas/[id]", "Ver en Odoo", "Solo si odoo_partner_id", "OK — condicional"),
    ("Empresas detalle", "/empresas/[id]", "Ver precios", "Solo si price_supplier_name", "OK — condicional"),
]

ASSISTANT_CASES = [
    ("cuantos faldos de papel le hemos vendido a Farma Trix", "sales_question", "test_sales_semantic.py"),
    ("cuantos rollos de papel 350 hemos vendido", "sales_question", "test_sales_semantic.py"),
    ("quien me sale mejor laptop 16GB 512GB", "price_compare", "test_assistant.py"),
    ("tenemos DGII vigente", "document_validity", "test_assistant.py"),
    ("que tareas tiene Jennipher", "work_tasks", "test_assistant.py"),
    ("que licitaciones hay de computadoras", "dgcp_search", "test_assistant.py"),
    ("busca todo sobre Banco Ademi", "enterprise_search", "test_assistant.py"),
    ("que pide esta licitacion", "dgcp_requirements", "test_assistant.py"),
]

DASHBOARD_ITEMS = [
    "Saludo ejecutivo con tenant activo",
    "Assistant proactivo con avatar",
    "KPIs con enlaces a módulos",
    "Resumen por módulos (parcial)",
    "Alertas críticas",
    "Acciones rápidas",
    "Actividad reciente",
    "Pendiente: ventas mes RD$, productos indexados, borradores cotización en KPIs",
]


def http_get(path: str) -> tuple[int, str]:
    url = f"{FRONTEND_URL}{path}"
    try:
        with urlopen(url, timeout=30) as resp:
            return resp.status, resp.read(12000).decode("utf-8", errors="replace")
    except HTTPError as e:
        body = e.read(4000).decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except URLError:
        return 0, ""


def scan_proximamente() -> list[str]:
    hits: list[str] = []
    for path in FRONTEND.rglob("*"):
        if path.suffix not in {".tsx", ".ts"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"pr[oó]ximamente", text, re.I):
            rel = path.relative_to(ROOT)
            hits.append(str(rel))
    return hits


def run_pytest_subset() -> str:
    try:
        proc = subprocess.run(
            ["docker", "compose", "exec", "-T", "backend", "pytest", "-q",
             "tests/test_assistant.py", "tests/test_sales_semantic.py",
             "tests/test_business_companies.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.stdout + proc.stderr
    except Exception as exc:
        return f"No ejecutado: {exc}"


def write_full_module_audit(ts: str, proximamente: list[str]) -> None:
    lines = [
        "# Auditoría total de módulos JAIOS",
        "",
        f"- **Generado:** {ts}",
        f"- **Frontend:** {FRONTEND_URL}",
        "",
        "| Módulo | Ruta | Estado | Problemas | Acción requerida | Prioridad |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in MODULES:
        lines.append(f"| {row[0]} | `{row[1]}` | {row[2]} | {row[3]} | {row[4]} | {row[5]} |")

    lines.extend(["", "## Texto «Próximamente» en código frontend", ""])
    if proximamente:
        for p in proximamente:
            lines.append(f"- `{p}`")
    else:
        lines.append("- Ninguno en páginas de plataforma")

    lines.extend([
        "",
        "## Criterio de cierre",
        "- Módulo visible en sidebar debe cargar sin error y sin placeholder.",
        "- Estado honesto: **Listo para revisión** pendiente validación visual Fausto.",
        "",
    ])
    (QA_DIR / "full-module-audit.md").write_text("\n".join(lines), encoding="utf-8")


def write_functional_ui_audit(ts: str) -> None:
    lines = [
        "# Auditoría funcional UI",
        "",
        f"- **Generado:** {ts}",
        "",
        "| Ruta | HTTP | Carga | Próximamente | Notas |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, route, *_ in MODULES:
        status, body = http_get(route)
        loads = status == 200 and "JAIOS" in body
        prox = bool(re.search(r"pr[oó]ximamente", body, re.I))
        note = "OK" if loads and not prox else ("Sin servicio" if status == 0 else "Revisar")
        lines.append(
            f"| `{route}` | {status or '—'} | {'Sí' if loads else 'No'} | {'Sí' if prox else 'No'} | {note} |"
        )
    (QA_DIR / "functional-ui-audit.md").write_text("\n".join(lines), encoding="utf-8")


def write_sidebar_readiness(ts: str) -> None:
    lines = [
        "# Sidebar — readiness por módulo visible",
        "",
        f"- **Generado:** {ts}",
        "",
        "| Grupo / ítem | Ruta | Estado | Evidencia |",
        "| --- | --- | --- | --- |",
    ]
    for row in SIDEBAR_READINESS:
        lines.append(f"| {row[0]} | `{row[1]}` | {row[2]} | {row[3]} |")
    (QA_DIR / "sidebar-module-readiness.md").write_text("\n".join(lines), encoding="utf-8")


def write_dead_buttons(ts: str) -> None:
    lines = [
        "# Reporte botones y acciones",
        "",
        f"- **Generado:** {ts}",
        "",
        "| Módulo | Ruta | Botón | Comportamiento | Veredicto |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in DEAD_BUTTONS:
        lines.append(f"| {row[0]} | `{row[1]}` | {row[2]} | {row[3]} | {row[4]} |")
    lines.extend([
        "",
        "## Regla aplicada",
        "Botones deshabilitados solo con tooltip/mensaje claro. Sin botones decorativos sin acción.",
        "",
    ])
    (QA_DIR / "dead-buttons-report.md").write_text("\n".join(lines), encoding="utf-8")


def write_assistant_report(ts: str, pytest_out: str) -> None:
    lines = [
        "# Assistant — intenciones obligatorias",
        "",
        f"- **Generado:** {ts}",
        "",
        "| Consulta | Intención esperada | Test |",
        "| --- | --- | --- |",
    ]
    for q, intent, test in ASSISTANT_CASES:
        lines.append(f"| {q} | {intent} | `{test}` |")

    lines.extend(["", "## Ejecución pytest (subset)", "", "```", pytest_out.strip()[:3000], "```", ""])
    (QA_DIR / "assistant-intent-report.md").write_text("\n".join(lines), encoding="utf-8")


def write_dashboard_report(ts: str) -> None:
    lines = [
        "# Dashboard ejecutivo — rediseño",
        "",
        f"- **Generado:** {ts}",
        "",
        "## Elementos",
    ]
    for item in DASHBOARD_ITEMS:
        mark = "✅" if "Pendiente" not in item else "⚠️"
        lines.append(f"- {mark} {item}")
    lines.extend([
        "",
        "## Estado",
        "**Validación parcial** — base operativa; KPIs comerciales adicionales pendientes.",
        "",
    ])
    (QA_DIR / "dashboard-redesign-report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prox = scan_proximamente()
    pytest_out = run_pytest_subset()

    write_full_module_audit(ts, prox)
    write_functional_ui_audit(ts)
    write_sidebar_readiness(ts)
    write_dead_buttons(ts)
    write_assistant_report(ts, pytest_out)
    write_dashboard_report(ts)

    print(json.dumps({"generated": ts, "reports": 6, "proximamente_files": prox}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
