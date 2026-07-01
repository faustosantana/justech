# Fase 20.1 — Rediseño wizard de pagos

**Versión:** `hellenia_account` 19.0.1.0.27  
**Estado:** Implementado en código — **NO PASS** (pendiente certificación Playwright completa + 607/623/PDF)

## Hallazgo post-implementación (v26)

La prueba Playwright del 2026-07-01 13:13 mostró todas las facturas marcadas con montos = residual y creó 3 pagos. Causas identificadas:

1. **Vista en BD desactualizada** — `ir.ui.view` id 1658 carecía de `readonly="not apply"` en `amount_to_pay` (upgrade sin recarga de workers).
2. **`@api.onchange("apply", "amount_residual")`** — dependencia de `amount_residual` innecesaria; corregida en v27 (solo `apply`).
3. **Workers Odoo** — requieren reinicio tras `-u hellenia_account` para cargar Python nuevo.
4. **Datos TEST** — partner 2361 quedó sin facturas pendientes tras la prueba fallida; script `phase20-1-prepare-smoke-test-data.py` recrea escenario.

## Cambios v27

- `@api.onchange("apply")` sin dependencia de `amount_residual`.
- `@api.constrains` en línea: `apply=False` ⇒ `amount_to_pay=0`.
- Vista: `widget="boolean"` + `options="{'autosave': false}"` en checkbox.
- Playwright: selección por `partner_id` / `ref` único, no por nombre.

## Decisión

Reescritura controlada del wizard manteniendo vista, menú, acciones y UX. Cambio únicamente en implementación interna.

## Cambios arquitectónicos

1. **`create()` vacío** — solo `super().create()`; respeta `line_ids` del `web_save`.
2. **`_load_pending_invoices()`** — exclusivamente en onchange de `partner_id` / `partner_type` / `currency_id`.
3. **Carga limpia** — `apply=False`, `amount_to_pay=0`, sin precargar residual.
4. **`action_register_payments()`** — procesa `self.line_ids` con `apply=True` y `amount_to_pay>0`; monto autorizado = `line.amount_to_pay`.
5. **Eliminados** todos los guards SQL/forense de fases 19.x.

## Auditoría partners duplicados — SMOKE P13.4 CF (PROD)

| id | Facturas | Pendientes | Recomendación |
|----|----------|------------|---------------|
| 21 | 1 | 0 | Prueba — archivar o fusionar |
| **22** | 1 | **1** | **Canónico** (tiene INV/2026/00002 pendiente) |
| 23 | 3 | 0 | Prueba — archivar o fusionar |

**Impacto:** autocomplete por nombre selecciona id 23 (sin facturas) → wizard vacío.  
**Acción requerida:** fusionar 21 y 23 en 22, o marcar ref único (`SMOKE-P134-CF-22`). Playwright usa `partner_id` explícito.

## Validación pendiente

| Criterio | Estado |
|----------|--------|
| Playwright UI 3 facturas / parcial RD$5,000 | Pendiente TEST |
| Video flujo | Pendiente |
| Logs servidor | Pendiente |
| Asiento contable | Pendiente |
| Conciliación | Pendiente |
| Retención 5% Gobierno | Pendiente |
| Reporte 607 / 623 / PDF | Pendiente |

## Despliegue

1. Backup TEST/PROD antes de promover.
2. `-u hellenia_account` en TEST primero.
3. Playwright `scripts/phase20-1-payment-wizard-playwright.py` con `partner_id=2361` (TEST).
