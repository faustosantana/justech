# Certificación pagos parciales con retención — Fase 18.10

## Escenario

Factura RD$11,800 (base RD$10,000 + ITBIS RD$1,800)  
Abono RD$5,000 con retención Gobierno 5%

## Comportamiento esperado

| Concepto | Valor |
|----------|-------|
| Monto aplicado | RD$5,000 |
| Base proporcional | RD$5,000 × (10,000/11,800) ≈ RD$4,237.29 |
| Retención 5% | ≈ RD$211.86 (sobre base proporcional) |
| Neto banco | RD$5,000 − retención |
| Residual factura | RD$6,800 |
| Estado factura | `partial` |

## Implementación

- `hellenia.withholding.catalog.compute_withholding_amount(move, applied_amount=...)`
- Wizard partner: `amount_to_pay` dispara recálculo proporcional
- Pago: `hellenia_applied_amount` = bruto aplicado; `amount` = neto banco
- Conciliación parcial vía flujo nativo Odoo (`payment_difference_handling=open` implícito)

## Validación script

Caso `06_partial_gov` en `phase18-10-retention-end-to-end-test.py`.

## Criterio FAIL

- Factura marcada `paid` con residual > 0
- Retención calculada sobre total factura en lugar de monto aplicado
- Pago muestra Total retenido = RD$0.00
