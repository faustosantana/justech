# Análisis de causa raíz — Ciclo de retenciones

## Síntomas reportados

- Pago muestra **Total retenido = RD$0.00** tras registrar con retenciones
- Recibo no conserva retención aplicada
- Reporte **623 sin movimientos** pese a pagos con Gobierno 5%
- Retención no persiste en BD

## Flujo auditado (14 puntos)

| # | Etapa | Hallazgo |
|---|-------|----------|
| 1 | Selección wizard | OK — catálogo y cálculo correctos |
| 2 | Cálculo por factura | OK — proporcional en abonos parciales |
| 3 | Registro pago | OK vía `hellenia.payment.partner.wizard` |
| 4 | `account.payment` | **FALLO** — líneas no persistían si create vals fallaba |
| 5 | `account.move` pago | OK — write-offs generados |
| 6 | Líneas contables | OK — cuenta retención + banco neto |
| 7 | Write-off | OK |
| 8 | Conciliación CxC/CxP | OK por monto bruto aplicado |
| 9 | Persistencia BD | **FALLO** — modelo transitorio y persistente con mismo nombre |
| 10 | Visualización pago | **FALLO** — `store=True` en compute + líneas ausentes |
| 11 | Visualización factura | **AUSENTE** — sin sección en factura |
| 12 | Reporte 606 | Parcial — solo tax lines, no pagos |
| 13 | Reporte 607 | Parcial — idem |
| 14 | Reporte 623 | **FALLO** — no leía líneas persistentes |

## Causas exactas

### 1. Total retenido RD$0.00

- Modelo transitorio `hellenia.payment.withholding.line` y persistente `hellenia.account.payment.withholding` convivían con nombres confusos.
- Líneas persistentes dependían solo de `create()` vals sin **fallback post-create**.
- Pagos históricos o vía registro estándar sin wizard: `hellenia_applied_amount=0`, sin líneas.
- Campo `hellenia_withholding_total` almacenado (`store=True`) podía quedar en 0 si el compute corría antes de las líneas.

### 2. Reporte 623 sin movimientos

- Exportador 623 buscaba solo `justech_do_gov_withholding_amount` en factura o líneas de impuesto.
- No consultaba `hellenia.payment.withholding.line` persistentes.
- `classify_moves` filtraba por tax line `-5% ISR Gov.` en factura, inexistente en retención al momento del pago.

## Corrección (Fase 18.8)

- Modelo persistente único: **`hellenia.payment.withholding.line`**
- Transitorio renombrado: **`hellenia.payment.withholding.wizard.line`**
- `_hellenia_finalize_persistent_lines()` post-create en register
- 623/606/607 leen líneas persistentes
- Vista retenciones en factura
- Compute de totales sin `store=True`
