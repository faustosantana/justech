# Fase 18.10B — Certificación UI TEST

**Estado:** TEST PASS  
**Fecha:** 2026-07-01  
**URL:** https://test.hellenia.cloud  
**BD:** `hellenia_test`  
**Commit:** `fd93ca4`  
**Módulo:** `hellenia_account` 19.0.1.0.14

## Deploy ejecutado

1. `git checkout cursor/phase18-10-retention-accounting-dd85`
2. Backup: `/opt/odoo-projects/hellenia/backups/test/2026-07-01_0154`
3. `rsync` custom + scripts
4. Restart Odoo TEST
5. Upgrade automático vía script certificación

## Registry validado

| Modelo | Estado |
|--------|--------|
| `hellenia.payment.withholding.line` | OK |
| `hellenia.payment.withholding.wizard.line` | OK |
| `hellenia.withholding.catalog` | OK |
| `hellenia.payment.partner.wizard` | OK |

## Escenario 1 — Factura RD$11,800 + 5% Gobierno

| # | Validación | Resultado |
|---|------------|-----------|
| 1 | Wizard calcula retención RD$500 | PASS |
| 2 | Pago: Total retenido ≠ RD$0 | PASS (500) |
| 3 | Factura afectada + NCF | PASS |
| 4 | Base RD$10,000 / 5% / RD$500 | PASS |
| 5 | Neto RD$11,300 | PASS |
| 6 | Factura muestra retención | PASS |
| 7 | Asiento línea retención 11080302 | PASS |
| 8 | Asiento balanceado D=C=11,800 | PASS |
| 9 | Conciliación paid | PASS |
| 10 | Reporte 607 | PASS (ISR 500) |
| 11 | Reporte 623 | PASS (Gobierno 500) |
| 12 | Recibo PDF con retención | PASS |

## Escenario 2 — Abono parcial RD$5,000 + 5% Gobierno

| Validación | Resultado |
|------------|-----------|
| Retención proporcional RD$211.86 | PASS |
| Factura partial | PASS |
| Residual RD$6,800 | PASS |
| Asiento balanceado | PASS |

## Escenario 3 — Pago múltiple (2 facturas proveedor)

| Validación | Resultado |
|------------|-----------|
| 2 pagos (uno por factura) | PASS |
| Solo factura 2 con ITBIS 100% | PASS |
| NCF visible | PASS |
| Reporte 606 | PASS |

## Evidencia

`evidence/phase18-10b-ui-validation-test.json`

## Nota

Validación ejecutada vía Odoo shell replicando campos UI. Se recomienda confirmación visual en navegador antes de promoción.
