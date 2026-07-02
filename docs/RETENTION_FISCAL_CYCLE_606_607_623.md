# Ciclo fiscal 606 / 607 / 623

## Fuente de datos

Todas las retenciones se leen desde **`hellenia.payment.withholding.line`** persistentes, reconciliadas con la factura.

## 606 — Compras

- Retenciones ITBIS/ISR con `affects_606=True`
- `_withholding_breakdown()` suma líneas persistentes de pagos reconciliados

## 607 — Ventas

- Retenciones con `affects_607=True` (ej. Gobierno 5%, ITBIS)
- Validado: ISR 500.0 desde pago con `RET-GOB-5`

## 623 — Gobierno 5%

**Alcance funcional:** ISR 5% Gobierno (`RET-GOB-5`) únicamente.

Alimentado desde:
1. Líneas persistentes con `affects_623=True`
2. `justech_do_gov_withholding_amount` en pago/factura
3. Fallback: línea impuesto en factura

Campos exportados: período, fecha retención, RNC, factura, NCF, monto, referencia pago.

**Evidencia TEST:** reporte 623 con `lines=1` tras pago Gobierno 5%.
