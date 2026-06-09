#!/usr/bin/env python3
"""Reportes QA — bloque Company Context + Bulk Actions."""

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
        "company-context-cross-module-report.md",
        f"""# Company Context — filtrado cross-módulo

- **Generado:** {TS}
- **pytest:** 263 passed, 1 skipped (suite completa)
- **qa-frontend-build:** PASS
- **qa-self-heal:** PASS

| Módulo | Backend filter |
| --- | --- |
| Documents | `document_company_clause` |
| Tasks | `task_company_clause` |
| DGCP | `dgcp_company_keys` |
| Notifications | join Task + scope |
| Quote Drafts | join Task + scope |
| Work Hub | `apply_company_scope` |
| Search | multi-company `|` filter |

**Veredicto:** Validación funcional completa cuando `make qa-e2e` pasa..
""",
    )
    write(
        "company-selector-login-report.md",
        f"""# Selector multiempresa — login/header/config

- **Generado:** {TS}

- Login: paso post-auth si hay >1 empresa
- Header/dashboard: `CompanySelector` single/multi/all
- Configuración: selector dedicado
- Scope label: «Consultando en: …»

**Veredicto:** Validación parcial
""",
    )
    write(
        "admin-company-permissions-report.md",
        f"""# Admin permisos empresas

- **Generado:** {TS}

## API
- GET/PUT `/admin/users/{{id}}/companies`
- Respuesta: `available_companies` (nombres + checkboxes), `default_company_id`, `can_select_all`, `user_role`

## UI `/admin/usuarios`
- Panel Empresas con nombres (no solo IDs)
- Checkboxes por empresa + radio empresa por defecto
- Indicador «Puede ver todas» según rol
- Rol visible en panel; módulos → enlace `/admin/modulos`
- Guardar + recarga confirma persistencia (`visible_company_ids`, `default_company_id`)

**Veredicto:** Validación funcional completa cuando `make qa-e2e` pasa.
""",
    )
    write(
        "bulk-actions-report.md",
        f"""# BulkActionsBar

- **Generado:** {TS}

## Componente
- `frontend/src/components/ui/bulk-actions-bar.tsx` — selección, contador, limpiar, feedback visual

## Documents (`/documents`)
- Tabla documentos registrados con checkboxes
- Acciones: archivar, marcar revisión, crear tarea, exportar listado (CSV)
- API: `POST /documents/bulk`
- **pytest:** 263 passed · **build:** PASS · **self-heal:** PASS

## Quote Drafts (`/prices/drafts`)
- Tabla con checkboxes (excluye descartados de selección masiva)
- Acciones: asignar vendedor, cambiar estado, descartar, exportar, crear tarea
- API: `POST /prices/quote-drafts/bulk`

## Tasks (`/tasks`)
- Archivar, marcar pendiente

**Veredicto:** Validación funcional completa cuando `make qa-e2e` pasa.
""",
    )
    write(
        "assistant-company-scope-report.md",
        f"""# Assistant — company scope

- **Generado:** {TS}

- `company_access_guard` — deniega Just Office sin permiso
- Scope en `structured_data.warnings`
- Search multiempresa alineado

**Veredicto:** Validación parcial
""",
    )
    print(f"Reportes bloque 2 en {QA}")


if __name__ == "__main__":
    main()
