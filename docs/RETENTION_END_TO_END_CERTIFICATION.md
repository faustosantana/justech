# Certificación end-to-end retenciones — Fase 18.10

## Criterio PASS estricto

Solo PASS si la cadena completa está conectada:

**Wizard → Pago → Asiento → Conciliación → Factura → Recibo PDF → 606/607/623**

## Script

```bash
bash scripts/run-odoo-shell-env.sh test phase18-10-retention-end-to-end-test.py PHASE1810 evidence/phase18-10-retention-end-to-end-test.json
```

## Casos cubiertos

| # | Caso | Validación |
|---|------|------------|
| 01 | Cobro sin retención | wh=0, sin líneas BD |
| 03 | Cobro 5% Gobierno | wh=500, GL, factura, gov field |
| 04 | ITBIS 100% compra | wh=1800, move_line_id |
| 05 | Dual ITBIS+ISR | wh=2000 |
| 06 | Abono parcial + Gobierno | proporcional, partial |
| 07 | Multi-factura agrupada | 1 pago, 2 facturas, wh en una |
| 08 | Proveedor ITBIS 30% | wh=540 |
| 09 | Reopen pago | totales persisten |
| 10-12 | 606, 607, 623 | líneas reporte + montos |
| 13 | Conciliación | partial_reconcile o paid |
| 14 | Recibo PDF | "Total retenido" + monto |
| 15 | Vistas OWL | sin error registry |

## Evidencia requerida por caso con retención

- `payment.hellenia_withholding_total` > 0
- `hellenia.payment.withholding.line` en BD
- Línea GL en cuenta retención en `payment.move_id`
- Factura: `hellenia_withholding_line_ids`
- 623: `_gov_amount` >= 500 para Gobierno

## Estado

Ejecutar en TEST tras deploy de `hellenia_account` 19.0.1.0.13.

**NO promover a producción** hasta aprobación explícita tras PASS manual en UI.
