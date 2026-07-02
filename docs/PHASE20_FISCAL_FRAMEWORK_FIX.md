# Fase 20 — Correcciones funcionales del Framework Fiscal DGII

## Alcance

Correcciones obligatorias detectadas en validación manual TEST antes de continuar con formatos 607/608/609.

**Restricciones respetadas:** solo TEST, sin cambios en odoo-pecv ni producción.

## Errores encontrados y causa raíz

| # | Problema | Causa raíz |
|---|----------|------------|
| 1 | Bitácora/chatter incompleta | Cambios de estado vía `write()` directo sin evento unificado |
| 2 | Estados decorativos | `state` editable en vistas; múltiples puntos de escritura |
| 3 | Bandeja pendientes vacía | Dominio `[('approval_ids.state','=','pending')]` poco fiable en Odoo |
| 4 | Excel sin orientación | `UserError` genérico en lugar de asistente con diagnóstico |
| 5 | Contadores inconsistentes | Mezcla contadores del exportador vs líneas cargadas en revisión |
| 6 | Período 30/06–30/06 | `date_from`/`date_to` por defecto = hoy; `period_code` no sincronizaba fechas |
| 7 | Revisión fiscal incompleta | Faltaban filtros, acciones por línea y fechas legibles |
| 8 | UX de error pobre | Mensajes sin acciones de navegación |

## Correcciones aplicadas

### Workflow unificado (`dgii_fiscal_workflow.py`)
- `_transition_state()` — único punto de cambio de estado + chatter + bitácora
- `_post_workflow_event()` — registra quién, cuándo y comentario
- Guardia `write()` — bloquea cambio manual de `state`
- `has_pending_approval` — campo almacenado/indexado para bandeja
- `_refresh_summary_counts()` — unifica `count_*` con `line_ids`
- `_get_export_diagnostics()` + asistente de bloqueo Excel
- Fechas legibles `date_from_display` / `date_to_display` (DD/MM/YYYY)
- `action_generate()` sin cambiar estado del flujo

### Vistas
- Revisión fiscal: estado readonly, filtros completos, acciones por línea (factura, proveedor, pago, PDF, aprobar/rechazar/corregir)
- Bandeja pendientes: dominio `has_pending_approval = True` + mensaje vacío
- Asistente bloqueo Excel con botones de navegación

### Post-init (`hooks.py`)
- Backfill `period_code` y sincronización de fechas en reportes existentes

## Validación

```bash
bash scripts/run-phase20-test.sh
```

Evidencia: `evidence/phase20-fiscal-framework-test.json`

## Flujo esperado E2E

```
Borrador → Validado → Requiere aprobación → Aprobado → Generado
```

Cada transición solo mediante botones de acción, registrada en bitácora y chatter.
