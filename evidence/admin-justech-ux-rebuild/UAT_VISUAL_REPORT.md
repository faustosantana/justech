# UAT Visual — Administración Justech UX Rebuild

**Fecha:** 2026-07-12  
**Entorno:** `erp.justech.do` / `justech_dev`  
**Rama local:** `feature/fiscal-standard-consolidation`  
**Módulo:** `justech_admin_center` **19.0.2.11.1**  
**Backup:** `/opt/odoo-dev/backups/admin-justech-ux-rebuild-20260712_213547`  
**Commit:** pendiente de aprobación (sin push/merge)

## Resultado visual (navegador real)

| # | Pantalla | Evidencia | Resultado |
|---|----------|-----------|-----------|
| 1 | Dashboard — Just Office | `screenshots/01_dashboard_just_office.png` | PASS |
| 2 | Dashboard — JUSTECH | `screenshots/02_dashboard_justech.png` | PASS |
| 3 | Justech Fiscal | `screenshots/03_fiscal_just_office.png` | PASS |
| 4 | Justech Garantías | `screenshots/04_garantias_just_office.png` | PASS |
| 5 | Centro de pendientes | dominio severidad warning/error/critical; 0 pendientes reales | PASS |
| 6 | Estado del sistema | `screenshots/06_estado_sistema.png` | PASS |
| 7 | Página de empresa | selector 4/4 + hub nativo | PASS |
| 8 | Modo oscuro | `screenshots/08_dashboard_dark.png` | PASS |
| 9 | Modo claro | `screenshots/01_dashboard_just_office.png` | PASS |

## Checklist de aceptación

| Criterio | Estado |
|----------|--------|
| Sin HTML crudo visible | PASS |
| Sin textos concatenados (`…Global`) | PASS |
| Sin métricas contradictorias (Atención con 0 errores) | PASS |
| Sin pendientes OK / info como accionables | PASS (60 info abiertos **excluidos** del contador) |
| Usuarios UAT fuera de consola principal | PASS (`Más` → Revisar cuentas de prueba, solo `base.group_system`) |
| Breadcrumbs coherentes Admin → Producto | PASS (mejorados; sin Fiscal→Admin→Garantías) |
| Productos/capacidades organizados 1.x | PASS |
| Garantías reconstruida (empty state si inactiva) | PASS |
| Diseño claro/oscuro | PASS |
| Responsive 1920/1440/1280 (viewport browser) | PASS |
| Multiempresa 4/4 | PASS |
| Histórico / GL | PASS (`debit=credit` 86 071 457.49) |
| AccessError / OwlError / RPC_ERROR / 404 / login loop | PASS en flujo validado |

## Notas residuales (no bloquean presentación)

1. Abrir producto desde kanban embebido puede aún renderizar como diálogo técnico en algunos clics; acción corregida a `target=main` + `edit=0`. Revalidar tras hard refresh.
2. Toast nativo de push notifications del browser (ajeno a Justech).
3. Clave maestra **no** rotada; sesión UAT inyectada solo para capturas.

## Auditoría

Ver `UX_AUDIT.md` (Fase 1).
