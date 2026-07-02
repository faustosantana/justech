# Fase 18.6 — Cierre contable retenciones en pagos

## Objetivo

Persistir retenciones en `account.payment`, mostrarlas en recibo PDF y validar efecto contable real con abonos parciales proporcionales.

## Cambios (`hellenia_account` 19.0.1.0.10)

### Modelo persistente

- `hellenia.account.payment.withholding` — líneas por pago con factura, NCF, catálogo, base, %, monto, cuenta y vínculo a línea de asiento.
- Campos en `account.payment`: `hellenia_applied_amount`, `hellenia_withholding_total`, `hellenia_net_transfer`, pestaña **Retenciones aplicadas**.

### Registro contable

Al crear el pago desde `account.payment.register`:

1. `hellenia_applied_amount` = monto bruto aplicado a la factura.
2. `amount` (banco/caja) = neto transferido.
3. `write_off_line_vals` = líneas en cuenta de retención.
4. Líneas persistentes copiadas al pago.
5. Post-creación: vínculo `move_line_id` en cada retención.

### Asiento esperado (venta con retención)

| Cuenta | Débito | Crédito |
|--------|--------|---------|
| Banco/Caja | Neto | |
| Retención por cobrar | Retenido | |
| Cuentas por cobrar | | Bruto aplicado |

### Asiento esperado (compra con retención)

| Cuenta | Débito | Crédito |
|--------|--------|---------|
| Cuentas por pagar | Bruto aplicado | |
| Banco/Caja | | Neto |
| Retención por pagar | | Retenido |

## Reportes fiscales

- **606/607:** `_withholding_breakdown` ahora incluye retenciones de pagos reconciliados (`hellenia_withholding_line_ids`).
- **623:** Existe y cubre **ISR 5% Gobierno** (`RET-GOB-5`). Otros tipos de retención no van al 623.

## Validación

```bash
scripts/run-odoo-shell-env.sh test phase18-6-payment-withholding-test.py PHASE186 evidence/phase18-6-payment-withholding-test.json
```
