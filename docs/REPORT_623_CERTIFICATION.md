# Certificación — Reporte 623 (Fase 18.13)

## Menú

**Contabilidad → Reportes → Reportes DGII → 623 — Retenciones Estado**

Test `19_623_menu`: PASS

## Fuente de datos

1. `hellenia.payment.withholding.line` con `affects_623=True` OR código `RET-GOB-5` / `wh_isr_gov`
2. Stamp en `account.move` post-conciliación (`justech_do_gov_withholding_amount`)
3. Exportador `justech.do.dgii.623.exporter`

## Campos validados para Retención 5% Gobierno

| Campo | Fuente |
|-------|--------|
| Fecha | `payment.date` / `justech_do_gov_retention_date` |
| Cliente/RNC | `partner_id.vat` |
| Factura / NCF | `move_id` / `justech_do_ncf` |
| Pago | `payment.name` como referencia fallback |
| Base | Línea persistente `base_amount` |
| % | `rate` del catálogo |
| Monto retenido | `amount` línea persistente |
| Cuenta contable | `account_id` |
| Asiento origen | `payment_move_id` / `move_line_id` |

## Test PASS

- `19_623_lines` — líneas generadas, `gov_amt >= 500`
- `19_623_amount_col` — columna revisión muestra monto retención (no total factura)

## Evidencia

`evidence/phase18-13-final-payment-retention-test.json` → `evidence.623`
