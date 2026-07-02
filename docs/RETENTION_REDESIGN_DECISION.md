# Fase 18.13 — Decisión de rediseño de retenciones

## Decisión: continuar con hook nativo Odoo 19 (NO rollback)

El diseño basado en `_prepare_move_withholding_lines` es **correcto** y alineado con `l10n_account_withholding_tax`. No se requiere rollback a Fase 18.8.

## Problema raíz real

| # | Síntoma | Causa |
|---|---------|-------|
| 1 | Total retenido RD$0 en pago | `_hellenia_rebuild_register_withholding_lines()` borraba líneas inyectadas por partner wizard cuando `catalog_ids` vacío |
| 2 | Wizard muestra RD$0 retención | `_compute_withholding_display` leía `withholding_detail_ids` sin recalcular (solo onchange) |
| 3 | 623 sin retención Gobierno | Stamp gov antes de conciliación; filtro `_persistent_gov_lines` solo `affects_623`; UI mostraba total factura |
| 4 | Abono parcial forzaba total | Falta `custom_user_amount` nativo Odoo |
| 5 | Factura → Pagar sin retenciones | Register sin selector de catálogo |

## Arquitectura final

```
Catálogo retención (hellenia.withholding.catalog)
    ↓
account.payment.register (3 caminos)
    ↓ _create_payment_vals_from_wizard
account.payment.create (amount=bruto, hellenia_withholding_line_ids)
    ↓ _prepare_move_withholding_lines (hook nativo)
account.move: D Banco neto + D Retención + C CxC bruto
    ↓ _reconcile_payments
account.partial.reconcile + stamp gov 623
    ↓
hellenia.payment.withholding.line (persistente)
    ↓
606 / 607 / 623 exportadores
```

## Reglas contables

| Operación | Asiento |
|-----------|---------|
| Cobro con retención | D Banco (neto) + D Retención por cobrar = C CxC (bruto) |
| Pago proveedor con retención | D CxP (bruto) = C Banco (neto) + C Retención por pagar |

**`payment.amount` = bruto aplicado.** Nunca reducir al neto.

## Cambios implementados (18.13)

1. Register: `hellenia_withholding_catalog_ids` editable (camino factura).
2. Register: rebuild solo si hay catálogos seleccionados.
3. Partner wizard: cálculo server-side de retenciones en compute.
4. Parcial: `custom_user_amount` + `amount` bruto.
5. `hellenia_withholding_total` / `hellenia_net_transfer` con `store=True`.
6. Stamp gov post-`_reconcile_payments`.
7. 623: filtro unificado + columna monto retención en revisión.

## Módulos

- `hellenia_account` 19.0.1.0.18
- `justech_l10n_do_reports` 19.0.1.12.0
