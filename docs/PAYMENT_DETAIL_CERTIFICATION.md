# Certificación — Detalle del pago (Fase 18.13)

## Secciones validadas

| Sección | Campos | Persistencia |
|---------|--------|--------------|
| Resumen aplicación | Facturas, monto aplicado, total retenido, neto | `store=True` en totales |
| Detalle por factura | Factura, NCF, fecha, aplicado, retenciones, neto, conciliación | `hellenia.payment.application.line` |
| Retenciones aplicadas | Factura, NCF, retención, base, %, monto, cuenta, asiento, reporte | `hellenia.payment.withholding.line` + `move_line_id` |

## Tests PASS

- `02_full_no_wh_detail` — sin retención muestra aplicado y NCF
- `04_full_gov_*` — total retenido RD$500, GL vinculado
- `12_reopen_wh` — persiste al reabrir pago
- `09_from_invoice` — camino factura → pagar

## Evidencia

JSON: `evidence/phase18-13-final-payment-retention-test.json`

Ejemplo pago con retención:
- `hellenia_withholding_total`: 500.0 (almacenado)
- `hellenia_applied_amount`: 11800.0
- `hellenia_net_transfer`: 11300.0
- Línea GL retención vinculada (`move_line_id` set)
