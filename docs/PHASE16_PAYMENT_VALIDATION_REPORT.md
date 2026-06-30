# Fase 16 — Informe de validación pagos y bancos

**Rama:** `cursor/phase16-payments-banks-dd85`  
**Commit:** `293148d`  
**Fecha validación TEST:** 2026-06-30T19:09:19Z  
**Responsable:** Justech Cloud Agent

---

## 1. Resultado

| Ambiente | Resultado | Evidencia |
|----------|-----------|-----------|
| **TEST** | **PASS** | `evidence/phase16-payments-test.json` — 23/23 pruebas |
| **PROD** | **NO PROMOVIDO** | Requiere aprobación explícita del cliente |

---

## 2. Qué se instaló realmente en TEST

| Componente | Estado |
|------------|--------|
| `hellenia_account` | **installed** v19.0.1.0.2 |
| `l10n_do_check_printing` | installed (dependencia Cheque) |
| `justech_l10n_do_ncf` | installed (dependencia NCF en wizard) |
| Backup TEST previo | `backups/test/2026-06-30_1907` |

**Comando ejecutado:**
```bash
bash scripts/run-phase16-payments-test.sh
```

---

## 3. Evidencia métodos en español (shell TEST)

```
MODULE: installed 19.0.1.0.2
BNKD Banco López de Haro DOP bank= 4040043811
 IN: ['Transferencia', 'Tarjeta']
 OUT: ['Transferencia', 'Cheque']
BNKU Banco López de Haro USD bank= 4010461048
 IN: ['Transferencia', 'Tarjeta']
 OUT: ['Transferencia', 'Cheque']
CSH1 Caja / Efectivo bank= -
 IN: ['Efectivo']
 OUT: ['Efectivo']
```

**NO aparecen en diarios activos:** Manual Payment, Checks, BNK1 (legacy desactivado).

---

## 4. Matriz de pruebas — todas PASS

| Prueba | Resultado | Detalle |
|--------|-----------|---------|
| bank_dop_linked | PASS | 4040043811 |
| bank_usd_linked | PASS | 4010461048 |
| method_transferencia | PASS | |
| method_efectivo | PASS | |
| method_tarjeta | PASS | |
| method_cheque | PASS | |
| ret_5_gov | PASS | -5% ISR Gov. |
| ret_30_itbis | PASS | -5.4% |
| ret_10_isr | PASS | -10% |
| ret_75_informal | PASS | -13.5% |
| cobro_transferencia | PASS | NCF + PBNKD/2026/00001 |
| cobro_efectivo | PASS | paid |
| cobro_tarjeta | PASS | paid |
| pago_proveedor | PASS | paid |
| pago_cheque | PASS | paid |
| pago_parcial | PASS | residual=1180.00 |
| pago_multiple | PASS | 2 facturas |
| retencion_5_gobierno | PASS | ISR Gov. en factura |
| retencion_10_proveedor | PASS | ISR Fee |
| retencion_30_itbis | PASS | ITBIS Leg. |
| wizard_ncf_visible | PASS | NCF en líneas |
| reportes_606_607 | PASS | generados |
| conciliacion_bancaria | PASS | account_accountant installed |

---

## 5. Correcciones aplicadas en Fase 16.1

| Iteración | Problema | Fix |
|-----------|----------|-----|
| 1 | Instalación fallaba (`payment_type` en create) | v19.0.1.0.1 — eliminar campo related |
| 2 | Manual Payment / Checks visibles | v19.0.1.0.2 — unlink líneas genéricas duplicadas |
| 2 | BNK1 legacy activo | Desactivar BNK1 al existir BNKD/BNKU |
| 2 | Facturas proveedor sin fecha | `invoice_date` en tests y validación RD |
| 2 | Retención gobierno | Impuesto `-5% ISR Gov.` en línea factura |

---

## 6. Wizard de pago

Al registrar pago desde factura, el wizard muestra:

- Número de factura
- NCF (`justech_do_ncf`)
- Fecha, vencimiento, moneda
- Total y residual
- Importe editable (pago parcial/total)

Extensión: `hellenia_account/views/account_payment_register_views.xml`

---

## 7. Retenciones disponibles

| Retención | Impuesto `l10n_do` | Estado |
|-----------|-------------------|--------|
| 5% Gobierno | `-5% ISR Gov.` | Activo |
| 30% ITBIS retenido | `-30% ITBIS Leg. (N02-05)` | Activo |
| 10% proveedor informal (ISR) | `-10% ISR Fee` | Activo |
| 75% ITBIS informal | `-75% ITBIS (N08-10)` | Activo |

---

## 8. Autorización promoción PROD

| Criterio | Estado |
|----------|--------|
| TEST PASS | ✅ |
| Backup TEST | ✅ `2026-06-30_1907` |
| Sin datos críticos rotos | ✅ |
| Aprobación cliente | ⏳ **Pendiente — NO promover sin aprobación explícita** |

**Comando promoción (solo tras aprobación):**
```bash
APPROVE_PROMOTION=1 bash scripts/promote-phase16-payments-prod.sh
```

---

## 9. Documentación relacionada

- [PAYMENT_METHODS_AND_BANKS_FIX.md](./PAYMENT_METHODS_AND_BANKS_FIX.md)
- [RECEIVABLES_PAYABLES_PAYMENT_FLOW.md](./RECEIVABLES_PAYABLES_PAYMENT_FLOW.md)
- [DOMINICAN_WITHHOLDINGS_CONFIGURATION.md](./DOMINICAN_WITHHOLDINGS_CONFIGURATION.md)
