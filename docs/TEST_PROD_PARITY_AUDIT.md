# Fase 19 — Auditoría de paridad TEST vs PRODUCCIÓN

**Fecha:** 2026-07-01  
**Entorno TEST:** `hellenia_test` @ test.hellenia.cloud  
**Entorno PROD:** `hellenia_prod` @ odoo.hellenia.cloud  
**Commit certificado base:** `bbaf113` (Fase 18.13 — 89/89 PASS)  
**Commit promovido:** `acf21ca` (bbaf113 + fixes install/upgrade PROD)

---

## 1. Resumen ejecutivo

| Métrica | Valor |
|---------|-------|
| Diferencias módulos objetivo | 2 (pre-promoción) → 0 (post-promoción) |
| Diferencias menús DGII | 0 |
| Diferencias campos críticos | 0 (post-promoción) |
| Paridad alcanzada | **SÍ** |
| Evidencia TEST | `evidence/phase18-13-final-payment-retention-test.json` (89/89 PASS) |

---

## 2. Módulos auditados

| Módulo | TEST (objetivo) | PROD (pre) | PROD (post) |
|--------|-----------------|------------|-------------|
| `hellenia_account` | 19.0.1.0.19 installed | 19.0.1.0.18 installed | **19.0.1.0.19 installed** |
| `hellenia_ui` | 19.0.1.0.4 installed | 19.0.1.0.4 installed | 19.0.1.0.4 installed |
| `hellenia_reports` | 19.0.1.0.1 installed | 19.0.1.0.1 installed | 19.0.1.0.1 installed |
| `justech_l10n_do_base` | 19.0.1.3.0 installed | 19.0.1.3.0 installed | 19.0.1.3.0 installed |
| `justech_l10n_do_ncf` | 19.0.1.4.0 installed | 19.0.1.4.0 installed | 19.0.1.4.0 installed |
| `justech_l10n_do_reports` | 19.0.1.12.1 installed | **19.0.1.2.0 installed** | **19.0.1.12.1 installed** |

---

## 3. Menús DGII

| Reporte | TEST | PROD (post) |
|---------|------|-------------|
| 606 | ✓ activo | ✓ activo |
| 607 | ✓ activo | ✓ activo |
| 608 | ✓ activo | ✓ activo |
| 623 | ✓ activo | ✓ activo |

XMLID: `justech_l10n_do_reports.menu_justech_do_report_{606,607,608,623}`

---

## 4. Campos y modelos críticos (pagos / retenciones)

| Elemento | TEST | PROD (post) |
|----------|------|-------------|
| `account.payment.hellenia_applied_amount` | ✓ | ✓ |
| `account.payment.hellenia_withholding_total` | ✓ | ✓ |
| `account.payment.hellenia_withholding_line_ids` | ✓ | ✓ |
| `account.payment.hellenia_net_transfer` | ✓ | ✓ |
| `hellenia.payment.withholding.line` | ✓ | ✓ |
| `hellenia.payment.application.line` | ✓ | ✓ |

---

## 5. Bancos y diarios

| Código | TEST | PROD (post) |
|--------|------|-------------|
| BNKD | Banco López de Haro DOP | Banco López de Haro DOP |
| BNKU | Banco López de Haro USD | Banco López de Haro USD |
| CSH1 | Caja / Efectivo | Caja / Efectivo |

Métodos de pago: Transferencia, Efectivo, Tarjeta, Cheque (configurados vía `post_init_hook`).

---

## 6. Acciones y reportes

| Acción | TEST | PROD (post) |
|--------|------|-------------|
| `action_justech_do_report_606` | ✓ | ✓ |
| `action_justech_do_report_607` | ✓ | ✓ |
| `action_justech_do_report_608` | ✓ | ✓ |
| `action_justech_do_report_623` | ✓ | ✓ |
| Exportador `justech.do.dgii.623.exporter` | ✓ | ✓ |
| Catálogo `RET-GOB-5` | ✓ | ✓ |

---

## 7. Bloqueadores identificados en primer intento

### 7.1 `hellenia_account` — install en PROD

```
ParseError: payment_setup.xml — model hellenia.account.payment.setup no disponible durante carga XML en install
```

**Causa:** `<function>` en data XML ejecuta antes de que el modelo abstracto esté registrado en install fresco.  
**Fix (acf21ca):** `payment_setup.xml` vacío; configuración idempotente solo vía `post_init_hook`.

### 7.2 `justech_l10n_do_reports` — upgrade en PROD

```
AttributeError: 'justech.do.fiscal.report' object has no attribute '_compute_validation_state'
```

**Causa:** Campo `validation_state` declarado como `compute` sin método implementado. TEST no falló porque el campo ya existía en BD sin compute (migración incremental).  
**Fix (acf21ca):** Implementación de `_compute_validation_state` en `fiscal_report.py`.

---

## 8. Commit seleccionado para promoción

| Campo | Valor |
|-------|-------|
| Commit base certificado | `bbaf113` — Fase 18.13, 89/89 PASS |
| Commit promovido | `acf21ca` — bbaf113 + fixes PROD-safe |
| Rama | `cursor/phase19-test-prod-sync-dd85` |
| Evidencia TEST requerida | `evidence/phase18-13-final-payment-retention-test.json` |

> **Nota:** `bbaf113` no se promovió directamente porque fallaba el upgrade de `justech_l10n_do_reports` en PROD. `acf21ca` incluye el mismo código funcional certificado más los dos fixes mínimos, re-certificado 89/89 en TEST.

---

## 9. Evidencia

- Auditoría JSON: `evidence/phase19-parity-audit.json`
- Script: `scripts/phase19-test-prod-parity-audit.py`

---

## 10. Conclusión

**Paridad TEST ↔ PROD alcanzada** en módulos, menús, campos, modelos, bancos y reportes DGII tras promoción de `acf21ca`.
