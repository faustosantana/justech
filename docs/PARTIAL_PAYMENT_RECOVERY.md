# Recuperación — Abono parcial

## Problema

El wizard permitía editar "Monto a aplicar" pero tras el commit `70df199` los pagos **sin retención** no persistían `hellenia_applied_amount`, ocultando el resumen y dando la impresión de que el abono parcial no funcionaba.

En algunos casos Odoo 19 recalculaba `account.payment.register.amount` al residual completo ignorando el monto parcial pasado en `create()`.

## Causa

| Componente | Commit | Detalle |
|------------|--------|---------|
| `hellenia_applied_amount` | `70df199` | Solo se seteaba si `wh_total > 0` |
| `register.amount` | — | Compute de Odoo podía sobrescribir monto parcial |

## Fix (18.12)

**`payment_register_withholding.py`**
```python
applied = self.amount or payment_vals.get("amount") or 0.0
if applied:
    payment_vals["hellenia_applied_amount"] = applied
# ... retenciones solo si wh_total > 0
```

**`payment_partner_wizard.py`**
```python
if abs((register.amount or 0.0) - line.amount_to_pay) > 0.01:
    register.amount = line.amount_to_pay
```

## Caso obligatorio validado

| Campo | Valor |
|-------|-------|
| Factura total | RD$11,800 |
| Monto a aplicar | RD$5,000 |
| Retención 5% Gobierno (proporcional) | RD$211.86 |
| Estado factura | `partial` |
| Residual | RD$6,800 |
| `payment.amount` | RD$5,000 |
| `hellenia_applied_amount` | RD$5,000 |

## Evidencia TEST

- `01_partial_no_wh_*` — PASS  
- `02_partial_gov_*` — PASS  
- `04_two_payments` — pago múltiple parcial + total — PASS  
- `07_residual` / `08_partial_reconcile` — PASS  

Ver `evidence/phase18-12-regression-recovery-test.json`
