#!/usr/bin/env python3
"""Genera reportes UX, desktop y assistant del sprint premium."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / ".qa"
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)

    write(
        QA / "dashboard-ux-report.md",
        f"""# Dashboard UX — reporte

- **Generado:** {TS}

## Elementos implementados

| Elemento | Estado |
| --- | --- |
| Saludo personalizado + empresa activa | Corrección aplicada |
| Assistant proactivo grande (AssistantPromptCard XL avatar) | Corrección aplicada |
| KPIs enlazados (ventas/cxc/vencidas/tareas/DGCP/docs/precios/borradores/notif.) | Corrección aplicada |
| Alertas críticas | Listo para revisión |
| Acciones rápidas | Listo para revisión |
| Actividad reciente | Listo para revisión |

## Veredicto

**Validación parcial** — pendiente revisión visual Fausto.
""",
    )

    write(
        QA / "ui-redesign-report.md",
        f"""# UI Redesign Premium — reporte

- **Generado:** {TS}

## Cambios estructurales

- Sidebar agrupado (Inicio, Operaciones, Comercial, Licitaciones, Documentos, Plataforma, Administración)
- AssistantAvatar con estados y animación ligera
- Banner proactivo por módulo (`ProactiveAssistantBanner`)
- PWA manifest + iconos SVG
- Tokens Justech en globals.css (primary navy, success, warning, destructive)

## Pendiente

- Header dedicado con breadcrumbs (parcial — header en AppShell)
- Dark mode CSS completo

## Veredicto

**Validación parcial**
""",
    )

    write(
        QA / "desktop-app-report.md",
        f"""# Desktop App — reporte

- **Generado:** {TS}

## Estructura

- `desktop/` — Tauri 2 shell
- Tray/menu: Abrir JAIOS, Preguntar, Ver tareas, Salir
- Token seguro: keyring (Mac Keychain / Windows Credential Manager)
- Comandos: `make desktop-dev`, `make desktop-build-mac`, `make desktop-build-windows`

## Validación

| Ítem | Estado |
| --- | --- |
| Carpeta desktop/ | ✅ |
| Tray/menu bar config | ✅ (código Rust) |
| Atajo Cmd/Ctrl+Shift+J | ⚠️ Pendiente registrar global shortcut |
| Build Mac generado | ⚠️ Requiere Rust+Tauri en máquina dev |
| Build Windows | ⚠️ Documentado — requiere entorno Windows |

## Veredicto

**Validación parcial** — estructura real; builds nativos pendientes de entorno.
""",
    )

    write(
        QA / "assistant-intent-report.md",
        f"""# Assistant — intención + memoria conversacional

- **Generado:** {TS}

## Memoria conversacional

- `conversation_id` por sesión (localStorage frontend)
- Backend: `ConversationContextStore` + `resolve_follow_up`
- Entidades: producto, cliente, licitación, documento, etc.
- Panel debug: `?assistant_debug=1` o `localStorage jaios-assistant-debug=1`

## Casos obligatorios

| Caso | Mecanismo |
| --- | --- |
| Papel 365 → ¿A quiénes? | Follow-up + BUYERS intent |
| ¿Y a qué precio? | Follow-up → LAST_PRICE |
| ¿Quién compró más? | TOP_BUYER intent |
| ¿Y este año? | year_filter + follow-up |
| 8 casos sprint anterior | tests/test_assistant.py, test_sales_semantic.py |

## Tests

- `tests/test_conversation_memory.py`

## Veredicto

**Corrección aplicada** — revalidar con Odoo conectado y Fausto en UI.
""",
    )

    print(f"Reportes UX generados en {QA}")


if __name__ == "__main__":
    main()
