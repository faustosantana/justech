# Certificación end-to-end retenciones — Fase 18.10 / 18.10B

**Estado:** TEST PASS  
**Fecha:** 2026-07-01  
**Base de datos:** `hellenia_test`  
**Módulo:** `hellenia_account` **19.0.1.0.14**  
**Commit desplegado:** `fd93ca4`  
**Backup previo:** `/opt/odoo-projects/hellenia/backups/test/2026-07-01_0154`

## Criterio PASS

Cadena completa verificada:

`Wizard → Pago → Asiento → Conciliación → Factura → Recibo PDF → 606/607/623`

## Certificación automática

```bash
bash scripts/run-odoo-shell-env.sh test phase18-10-retention-end-to-end-test.py PHASE1810 evidence/phase18-10-retention-end-to-end-test.json
```

**Resultado:** 23/23 PASS

## Certificación UI (shell)

```bash
bash scripts/run-odoo-shell-env.sh test phase18-10b-ui-validation-test.py PHASE1810B evidence/phase18-10b-ui-validation-test.json
```

**Resultado:** 28/28 PASS

## Evidencia clave — Cobro 5% Gobierno

| Punto | Valor |
|-------|-------|
| Pago | PBNKD/2026/00010 |
| Factura | INV/2026/00186 |
| NCF | B0100020036 |
| Monto aplicado | RD$11,800.00 |
| Total retenido | RD$500.00 |
| Neto transferido | RD$11,300.00 |
| Cuenta retención | 11080302 |
| Estado factura | paid |
| Asiento | D banco 11,300 + D retención 500 = C CxC 11,800 |
| 607 | 1 línea, ISR 500 |
| 623 | 1 línea, Gobierno 500 |
| PDF | Total retenido visible |

## Corrección crítica aplicada en deploy

Con el hook nativo `_prepare_move_withholding_lines`, **`payment.amount` debe ser el bruto aplicado**. Odoo resta automáticamente la retención de la línea de banco. Reducir `amount` al neto causaba CxC incompleta y factura `partial`.

## Pendiente P1

- Pago único agrupado multi-factura con retenciones distintas (limitación Odoo `group_payment`) — actualmente un pago por factura.

## Promoción

**NO lista para aprobación de promoción** sin validación manual en UI web por usuario funcional.
