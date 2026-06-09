#!/usr/bin/env python3
"""Reportes QA sprint estratégico."""

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / ".qa"
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write(name: str, body: str) -> None:
    QA.mkdir(parents=True, exist_ok=True)
    (QA / name).write_text(body, encoding="utf-8")


def main() -> None:
    write(
        "company-context-report.md",
        f"""# Company Context Global

- **Generado:** {TS}

| Ítem | Estado |
| --- | --- |
| GET/PUT /company-context | Corrección aplicada |
| GET /company-context/allowed | Corrección aplicada |
| Admin users companies | Corrección aplicada |
| Selector header/dashboard | Corrección aplicada |
| Filtrado Odoo backend | Corrección aplicada |
| Search auto-filtro | Corrección aplicada |
| Documents/Tasks filter | Validación parcial |

**Veredicto:** Validación parcial
""",
    )
    write(
        "assistant-synonyms-memory-report.md",
        f"""# Assistant — sinónimos + memoria

- **Generado:** {TS}

| Caso | Estado |
| --- | --- |
| Memoria conversacional papel 365 | Corrección aplicada |
| CustomerEntityResolver | Corrección aplicada |
| Alias Farma Trix / Ademi / DBG | Corrección aplicada |
| Scope empresa en contexto | Corrección aplicada |
| 8 casos QA sprint anterior | tests existentes |

**Veredicto:** Validación parcial
""",
    )
    write(
        "ui-premium-report.md",
        f"""# UI Premium

- **Generado:** {TS}

- Dashboard ejecutivo + selector empresa
- Sidebar agrupado
- Assistant proactivo + avatar
- Acciones rápidas dashboard

**Pendiente:** CRUD masivo en todas las tablas (parcial en empresas)

**Veredicto:** Validación parcial
""",
    )
    write(
        "desktop-roadmap-report.md",
        f"""# Desktop roadmap

- **Generado:** {TS}

- Carpeta `desktop/` Tauri 2
- Makefile targets desktop-dev/build-mac/build-windows
- Tray, keychain token, ventana assistant

**Veredicto:** Validación parcial — build nativo pendiente
""",
    )
    write(
        "supplier-connectors-roadmap.md",
        f"""# Supplier connectors

- **Generado:** {TS}

Interface `SupplierConnector` documentada en roadmap Fase F.

Proveedores objetivo: Ingram Micro, Omega Tech.

Prioridad: API > Excel/CSV > scraper controlado.

**Veredicto:** Diseño — implementación pendiente
""",
    )
    print(f"Reportes estratégicos en {QA}")


if __name__ == "__main__":
    main()
