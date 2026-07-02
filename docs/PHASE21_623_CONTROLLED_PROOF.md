# Prueba controlada 623 — P21 GOV PROOF (PROD)

**Fecha:** 2026-07-01  
**Objetivo:** Demostrar si el 623 vacío es datos maestros o bug funcional.

---

## Escenario creado (datos limpios)

| Elemento | Valor |
|----------|-------|
| Partner | `P21 GOV PROOF UNIQUE` (id **36**) |
| Ref | `P21-GOV-623-PROOF` |
| RNC | `101733934` |
| Factura | `INV/2026/00006` / ref `P21-GOV-INV-PROOF` |
| NCF | `B0200009905` |
| Pago UI | `PBNKD/2026/00003` / ref `P21-GOV-PAY-PROOF` |
| Retención | **solo RET-GOB-5** = **500.00** |

---

## Cadena verificada (post-pago UI)

| Eslabón | Valor | Estado |
|---------|-------|--------|
| Wizard UI retención preview | RD$ 500.00 | OK |
| `hellenia.payment.withholding.line` id 19 | RET-GOB-5 / 500.00 | OK |
| Asiento contable línea 366 | débito 500.00 | OK |
| `payment.justech_do_gov_withholding_amount` | 500.00 | OK |
| `invoice.justech_do_gov_withholding_amount` | 500.00 | OK |
| `invoice.justech_do_dgii_fiscal_state` | **valid** | OK |
| `validate_period_623` (exporter) | **1 válido** | OK |

---

## Resultado ANTES del fix (v12.2)

| Verificación | Resultado |
|--------------|-----------|
| UI → 623 → Generar → Cargar período | **0 documentos** |
| Conclusión datos limpios | **NO es solo datos maestros** |

### Causa funcional demostrada

| Campo | Detalle |
|-------|---------|
| **Archivo** | `dgii_report_review.py` |
| **Método** | `_collect_review_lines` |
| **Línea** | ~148 — `return []` para tipos distintos de 606/607/608 |
| **Efecto** | `action_load_review_lines` no cargaba líneas 623 aunque el exportador encontraba documentos válidos |

---

## Corrección aplicada (v19.0.1.12.4)

1. Rama `_collect_review_lines` para `623`
2. `_review_lines_623` + `_prepare_line_vals_623` (montos gobierno, fecha retención)

**No se modificó:** wizard pagos, motor retenciones, conciliación.

---

## Resultado DESPUÉS del fix (UI PROD)

| Métrica | Valor |
|---------|-------|
| Total documentos en revisión | 3 |
| Válidos para exportar | **1** (P21 GOV PROOF / 500.00) |
| RNC visible en UI | 101733934 |

Evidencia: `evidence/phase21-gov-623-proof/screenshots/12-623-post-fix.png`

---

## Conclusión dual

| Hallazgo | Tipo |
|----------|------|
| SMOKE P13.4 CF (partner 23 sin RNC, RET-ITBIS-30 vs gov 500) | **Inconsistencia datos maestros** |
| 623 vacío con partner limpio + RET-GOB-5 | **Bug funcional** en bandeja de revisión |

**El código de retenciones y stamp fiscal funciona.** El fallo estaba en la carga de líneas del reporte 623 en UI.

---

## Scripts y evidencia

- `scripts/phase21-gov-623-proof-setup.py`
- `scripts/phase21-gov-623-proof-playwright.py`
- `scripts/phase21-gov-623-proof-verify.py`
- `scripts/phase21-gov-623-post-fix-ui.py`
- `evidence/phase21-gov-623-proof/`
