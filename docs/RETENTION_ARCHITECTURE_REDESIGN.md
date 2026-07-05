# Rediseño arquitectura retenciones — Fase 18.10

## Principio

La retención **no es un cálculo del wizard**. Es parte del asiento contable del pago, persistida en BD y trazable en factura, conciliación y reportes DGII.

## Capas

```
┌─────────────────────────────────────────────────────────────┐
│  hellenia.payment.partner.wizard  (UX cobro/pago)             │
│  - Selección facturas, montos, catálogo retenciones         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  account.payment.register  (wizard Odoo)                      │
│  _create_payment_vals_from_wizard / _from_batch             │
│  _init_payments / _reconcile_payments                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  account.payment  (persistente)                               │
│  - hellenia_applied_amount (bruto)                          │
│  - hellenia_withholding_line_ids → hellenia.payment...line    │
│  - _prepare_move_withholding_lines() → account.move.line      │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   account.move      account.partial.    DGII 606/607/623
   (asiento pago)    reconcile           (líneas persistentes)
```

## Modelo persistente: `hellenia.payment.withholding.line`

| Campo | Uso |
|-------|-----|
| `payment_id` | Pago origen |
| `move_id` / `invoice_move_id` | Factura afectada |
| `partner_id`, `ncf` | Trazabilidad fiscal |
| `catalog_id`, `withholding_code`, `withholding_type` | Tipo retención |
| `base_amount`, `rate`, `amount` | Montos |
| `account_id`, `move_line_id` | Cuenta y línea GL |
| `payment_move_id` | Asiento del pago |
| `partial_reconcile_id` | Conciliación CxC/CxP |
| `affects_606/607/623` | Reportes DGII |
| `state` | draft / posted |

## Flujo cobro con 5% Gobierno (RD$11,800)

1. Wizard: aplicado RD$11,800, retención RD$500, neto RD$11,300
2. Register crea pago: `amount=11300`, `hellenia_applied_amount=11800`
3. Línea persistente: base RD$10,000, 5%, RD$500, cuenta 11080302
4. `_prepare_move_withholding_lines`: débito retención RD$500
5. Asiento: Banco RD$11,300 | Retención RD$500 | CxC crédito RD$11,800
6. Conciliación: CxC factura ↔ contrapartida pago
7. Factura: pestaña Retenciones aplicadas
8. 623: lee línea persistente `affects_623=True`

## Cambios vs Fase 18.8

| Antes | Después 18.10 |
|-------|---------------|
| `write_off_line_vals` para retención | `_prepare_move_withholding_lines` nativo |
| Solo `_from_wizard` | También `_from_batch` |
| Finalize en `_create_payments` | `_init_payments` + `_reconcile_payments` |
| N pagos para N facturas | 1 pago agrupado si múltiples facturas |
| Sin `partial_reconcile_id` | Enlazado post-conciliación |

## Criterio PASS

Wizard → Pago (`hellenia_withholding_total` > 0) → Asiento (línea retención) → Conciliación → Factura → Recibo PDF → 606/607/623.
