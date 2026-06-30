# Fase 16 — Informe de validación pagos y bancos

**Rama:** `cursor/phase16-payments-banks-dd85`  
**Fecha informe:** 2026-06-29  
**Responsable:** Justech Cloud Agent

---

## 1. Objetivo

Corregir flujo de pagos/cobros Hellenia: bancos López de Haro, métodos en español, facturas pendientes con NCF, retenciones RD, validación contable.

**Regla:** TEST primero → aprobación → backup PROD → promoción.

---

## 2. Estado de validación

| Ambiente | Resultado | Evidencia | Notas |
|----------|-----------|-----------|-------|
| **TEST** | **PENDIENTE / FAIL esperado hasta despliegue VPS** | `evidence/phase16-payments-test.json` | Requiere ejecutar `run-phase16-payments-test.sh` en `srv.hellenia.cloud` |
| **PROD** | **NO PROMOVIDO** | — | Bloqueado hasta TEST PASS + `APPROVE_PROMOTION=1` |

### Bloqueo previo resuelto en código

- Instalación `hellenia_account` fallaba por `payment_type` en `create()` de líneas de método de pago.
- Corrección en v19.0.1.0.1 + `post_init_hook`.

### Comando validación TEST

```bash
ssh root@srv.hellenia.cloud
cd /opt/odoo-projects/hellenia
git pull origin cursor/phase16-payments-banks-dd85
bash scripts/run-phase16-payments-test.sh
```

---

## 3. Causa raíz — bancos/métodos no visibles

| Problema | Causa |
|----------|-------|
| Cuentas bancarias no aparecen en pagos | `BNK1.bank_account_id` = vacío pese a existir `res.partner.bank` |
| Métodos en inglés / incompletos | Fase 3.5 creó líneas sin renombrar; un diario para dos monedas |
| Instalación módulo corrector fallaba | Campo related `payment_type` en `create()` |

---

## 4. Corrección aplicada

| Entregable | Estado |
|------------|--------|
| Módulo `hellenia_account` v19.0.1.0.1 | ✅ Commit en rama |
| Diarios BNKD, BNKU, CSH1 | ✅ Setup automatizado |
| Métodos Transferencia/Efectivo/Tarjeta/Cheque | ✅ Setup automatizado |
| Wizard NCF + facturas pendientes | ✅ Vista extendida |
| Script validación TEST | ✅ 20+ pruebas |
| Script promoción PROD | ✅ Con guard `APPROVE_PROMOTION` |
| Documentación | ✅ 4 documentos Fase 16 |

---

## 5. Matriz de pruebas (script automatizado)

| ID | Prueba | Criterio PASS |
|----|--------|---------------|
| A1 | `bank_dop_linked` | BNKD.bank_account_id = 4040043811 |
| A2 | `bank_usd_linked` | BNKU.bank_account_id = 4010461048 |
| A3–A6 | `method_*` | Transferencia, Efectivo, Tarjeta, Cheque presentes |
| R1 | `ret_5_gov` | -5% ISR Gov. activo |
| R2 | `ret_30_itbis` | -30% ITBIS Leg. activo |
| R3 | `ret_10_isr` | -10% ISR Fee activo |
| R4 | `ret_75_informal` | -75% ITBIS N08-10 activo |
| T1 | `cobro_transferencia` | Factura cliente pagada + NCF |
| T2 | `cobro_efectivo` | Pago caja |
| T3 | `cobro_tarjeta` | Método Tarjeta BNKD |
| T4 | `pago_proveedor` | Factura proveedor pagada |
| T5 | `pago_cheque` | Cheque salida BNKD |
| T6 | `pago_parcial` | Estado `partial` |
| T7 | `pago_multiple` | Dos facturas mismo cliente |
| T8 | `retencion_5_gobierno` | ISR Gov. en venta gubernamental |
| T9 | `retencion_10_proveedor` | ISR Fee en compra |
| T10 | `retencion_30_itbis` | ITBIS Leg. en compra |
| T11 | `wizard_ncf_visible` | NCF en líneas wizard |
| T12 | `reportes_606_607` | Wizards Justech generan reporte |
| T13 | `conciliacion_bancaria` | BNKD con cuenta + métodos |

---

## 6. Retenciones

### Disponibles (l10n_do)

- 5% Gobierno (`-5% ISR Gov.`)
- 30% ITBIS legal/profesional (`-30% ITBIS Leg./Prof.`)
- 10% ISR Fee (informal)
- 75% ITBIS informal (`-75% ITBIS N08-10`)
- +8 retenciones adicionales documentadas en `DOMINICAN_WITHHOLDINGS_CONFIGURATION.md`

### Pendientes

- Validación contador cuentas retención
- Wizard retención en pago (no requerido MVP)
- Escenarios 609 / pagos exterior

---

## 7. ¿Flujo listo para Hellenia?

| Aspecto | Estado |
|---------|--------|
| Diseño y código | ✅ Listo en rama |
| TEST ejecutado en VPS | ⏳ Pendiente despliegue |
| PROD | ❌ No promovido |
| Operación usuario final | ⏳ Tras TEST PASS + UAT corto |

**Veredicto provisional:** El flujo queda **listo en código** para Hellenia una vez se ejecute la validación TEST en VPS y resulte PASS. No promover a PROD sin evidencia JSON `"ok": true`.

---

## 8. Próximos pasos

1. Desplegar rama en TEST VPS y ejecutar `run-phase16-payments-test.sh`.
2. Si PASS → revisión cliente → `APPROVE_PROMOTION=1 bash scripts/promote-phase16-payments-prod.sh`.
3. Validar manualmente un cobro y un pago en UI TEST antes de PROD.
4. Eliminar datos de prueba (`Cliente Pago Test 16`, etc.) antes de go-live PROD.

---

## 9. Documentación relacionada

- [PAYMENT_METHODS_AND_BANKS_FIX.md](./PAYMENT_METHODS_AND_BANKS_FIX.md)
- [RECEIVABLES_PAYABLES_PAYMENT_FLOW.md](./RECEIVABLES_PAYABLES_PAYMENT_FLOW.md)
- [DOMINICAN_WITHHOLDINGS_CONFIGURATION.md](./DOMINICAN_WITHHOLDINGS_CONFIGURATION.md)
- [ACCOUNTING_CONFIGURATION.md](./ACCOUNTING_CONFIGURATION.md)
