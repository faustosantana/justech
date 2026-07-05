# Estado reporte fiscal 623 — retenciones

## ¿Existe el 623?

**Sí.** Implementado en `justech_l10n_do_reports` (`justech.do.dgii.623.exporter`).

## Alcance funcional

| Incluido | Excluido |
|----------|----------|
| ISR 5% Gobierno (`RET-GOB-5` / `wh_isr_gov`) | ITBIS 30%, 75%, 100% |
| Ventas a entidades del Estado | ISR informal, honorarios |
| NCF, cliente, monto retenido, fecha, referencia pago | Retenciones solo en compras (606) |

## Fuentes de datos

1. `account.payment.justech_do_gov_withholding_amount` (pago con retención Gobierno).
2. `account.move.justech_do_gov_withholding_amount` (copiado desde pago).
3. Líneas persistentes `hellenia.account.payment.withholding` con catálogo `RET-GOB-5`.
4. Fallback: línea de impuesto `-5% ISR Gov.` en factura.

## Pendiente fiscal formal

- ITBIS retenido en pagos → reportes **606/607** (columnas de retención), no 623.
- Auxiliar/mayor de retenciones → consulta por cuenta contable del catálogo.
- Validación normativa completa 623 con DGII → certificación fiscal separada.

## Conclusión

El 623 **está funcional para Gobierno 5%** en el flujo de pagos con retención. No afirmar cobertura de otros tipos de retención en formato 623.
