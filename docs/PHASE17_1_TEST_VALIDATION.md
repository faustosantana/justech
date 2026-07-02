# Fase 17.1 — Validación TEST

## Entorno

- Base: `hellenia_test`
- Rama: `cursor/phase17-1-payments-pdf-dd85`
- Módulos: `hellenia_account` 19.0.1.0.3, `hellenia_reports` 19.0.1.0.1, `hellenia_ux`

## Ejecución

```bash
bash scripts/run-phase17-1-test.sh
```

## Casos (20 + regresión)

| # | Caso | Test ID |
|---|------|---------|
| 1 | Cliente 3 facturas pendientes en wizard | `01_customer_3_pending` |
| 2 | Proveedor 3 facturas pendientes | `02_vendor_3_pending` |
| 3 | Pago parcial | `03_partial_payment` |
| 4 | Pago total | `04_full_payment` |
| 5 | Pago múltiple | `05_multi_payment` |
| 6 | Transferencia | `06_transfer` |
| 7 | Efectivo | `07_cash` |
| 8 | Tarjeta | `08_card` |
| 9 | Cheque | `09_check` |
| 10 | Retención 5% | `10_wh_5_gov` |
| 11 | Retención ITBIS 30% | `11_wh_30_itbis` |
| 12 | Retención informal 10% | `12_wh_10_informal` |
| 13 | Dos retenciones | `13_dual_withholding` |
| 14 | Asiento balanceado | `14_balanced_entry` |
| 15 | Conciliación | `15_reconciliation_ready` |
| 16 | Reporte 607 | `16_report_607` |
| 17 | Reporte 606 | `17_report_606` |
| 18 | PDF factura | `18_pdf_invoice` |
| 19 | PDF nota de crédito | `19_pdf_credit_note` |
| 20 | PDF B02 consumo | `20_pdf_b02_consumption` |

Regresión Fase 16: `evidence/phase17-1-payments-regression.json`

## Evidencia

Resultado principal: `evidence/phase17-1-full-validation.json`

## Estado

**TEST: PASS 25/25** (2026-06-30) — regresión Fase 16: PASS 23/23

Evidencia: `evidence/phase17-1-full-validation.json`

**PROD: NO promovido** — pendiente aprobación explícita.
