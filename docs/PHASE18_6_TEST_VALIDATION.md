# Fase 18.6 — Validación TEST

**Ambiente:** `hellenia_test` @ `test.hellenia.cloud`  
**Módulo:** `hellenia_account` **19.0.1.0.10**  
**Fecha:** 2026-07-01 UTC  
**Resultado:** **TEST PASS — 23/23**

## Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| Retenciones visibles en el pago | **Sí** — pestaña «Retenciones aplicadas» persistente |
| Recibo de pago muestra retenciones | **Sí** — PDF con factura, NCF, base, %, monto |
| Asientos contables reales | **Sí** — write-offs balanceados, vínculo GL |
| Cuentas usadas | ITBIS 100%: `21030201`, Gobierno 5%: `11080302` |
| Estado 623 | **Funcional** para ISR 5% Gobierno únicamente |
| Abonos parciales | **Validados** — retención proporcional al monto aplicado |
| Regresión 18.5 | **PASS** tras actualizar test 18.3 proporcional |
| Listo para pedir aprobación promoción | **Sí** (requiere aprobación explícita) |

## Pruebas ejecutadas

| # | Caso | Resultado |
|---|------|-----------|
| 1 | Pago completo sin retención | PASS |
| 2 | Pago completo ITBIS 100% | PASS |
| 3 | Pago completo Gobierno 5% | PASS |
| 4 | Doble retención ITBIS + ISR | PASS |
| 5 | Abono parcial sin retención | PASS |
| 6 | Abono parcial con retención proporcional | PASS |
| 7 | Multi-factura completa + parcial | PASS |
| 8 | Pago proveedor ITBIS 30% | PASS |
| 9 | Recibo PDF con retenciones y NCF | PASS |
| 10 | Pago reabierto conserva retenciones | PASS |
| 11 | Mayor cuenta retención vinculado | PASS |
| 12 | Reporte 606 | PASS |
| 13 | Reporte 607 | PASS |
| 14 | Reporte 623 (Gobierno 5%) | PASS |

## Comando revalidación

```bash
bash scripts/run-odoo-shell-env.sh test phase18-6-payment-withholding-test.py PHASE186 evidence/phase18-6-payment-withholding-test.json
```

## Documentación relacionada

- `docs/PAYMENT_WITHHOLDING_ACCOUNTING_CLOSURE.md`
- `docs/PARTIAL_PAYMENT_WITHHOLDING_FLOW.md`
- `docs/PAYMENT_RECEIPT_WITHHOLDING_REPORT.md`
- `docs/FISCAL_623_WITHHOLDING_STATUS.md`

## Evidencia

`evidence/phase18-6-payment-withholding-test.json`
