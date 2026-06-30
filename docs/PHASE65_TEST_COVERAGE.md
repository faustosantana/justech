# Fase 6.5 — Cobertura de Pruebas

**Fecha:** 2026-06-30  
**Metodología:** Análisis estático + inventario tests Odoo + script E2E DEV

---

## 1. Resumen

| Métrica | Valor |
|---------|-------|
| LOC producción (Python) | ~965 |
| LOC tests (Python) | ~396 |
| Tests unitarios Odoo | 13 |
| Casos E2E (`validate-phase6-mvp.py`) | 14 |
| **Cobertura estimada (líneas)** | **~48%** |
| **Cobertura estimada (métodos)** | **~52%** |
| **Cobertura estimada (ramas)** | **~40%** |

> Nota: sin `coverage.py` en CI — estimación basada en inventario manual de métodos y paths.

---

## 2. Tests existentes

### `justech_l10n_do_base` — 3 tests

| Test | Cubre |
|------|-------|
| `test_document_types_loaded` | Data XML tipos |
| `test_ncf_format` | `format_ncf()` |
| `test_rnc_validation` | RNC con guiones |

### `justech_l10n_do_ncf` — 8 tests

| Test | Cubre |
|------|-------|
| `test_b02_consumer_invoice` | B02 auto |
| `test_b01_requires_rnc` | B01 auto |
| `test_credit_note_b04` | B04 NC |
| `test_duplicate_ncf_blocked` | Duplicado |
| `test_depleted_range_blocked` | Agotado |
| `test_expired_range_blocked` | Vencido |
| `test_b11_purchase` | B11 compra |
| `test_void_ncf` | Anulación |

### `justech_l10n_do_reports` — 2 tests

| Test | Cubre |
|------|-------|
| `test_report_607` | Generación 607 |
| `test_report_608_voided` | Generación 608 |

### E2E DEV — 14 casos adicionales

Incluye B13, 606, PDF, balanced entry, receivable — no en suite CI unitaria.

---

## 3. Métodos sin cobertura directa

| Módulo | Método | Riesgo |
|--------|--------|--------|
| account_move | `_justech_fiscal_enabled` | Bajo |
| account_move | `_justech_should_auto_assign_ncf` | Medio |
| account_move | `_justech_validate_manual_ncf` | Alto |
| account_move | B03 via `debit_origin_id` | Alto |
| ncf_range | `action_cancel` / `action_set_draft` | Bajo |
| ncf_range | `_validate_ncf_format` edge cases | Medio |
| fiscal_report | `_lines_606` | Medio |
| fiscal_report | `action_export_csv` | Medio |
| fiscal_report | `action_export_xlsx` | Medio |
| wizard | `action_generate` | Bajo |
| fiscal_document_type | `parse_ncf` invalid input | Medio |
| res_partner | constraint país no-DO | Bajo |

---

## 4. Ramas sin probar

| Rama | Condición |
|------|-----------|
| Fiscal deshabilitado | `justech_do_fiscal_enabled=False` |
| País no DO | `country_id != DO` |
| Journal sin NCF | `justech_do_use_ncf=False` |
| NCF requerido sin rango | UserError path |
| B01 sin RNC | UserError path |
| `in_refund` | Sin lógica |
| Compra NCF manual proveedor | Sin test |
| Multi-company isolation | Sin test |
| Concurrencia 2 posts | Sin test |
| `xlsxwriter` ImportError fallback | Sin test |

---

## 5. Casos extremos no cubiertos

1. **Post simultáneo** de 2 facturas — último NCF del rango
2. **Factura borrador** con NCF manual duplicado de otra borrador
3. **Reporte 606** con miles de moves — performance
4. **Void NCF** sin permiso manager (seguridad)
5. **Compañía sin rangos** configurados
6. **Secuencia NCF** fuera de rango autorizado DGII
7. **Nota crédito** sin factura origen (`reversed_entry_id` vacío)
8. **Export** caracteres especiales en nombre partner (CSV encoding)

---

## 6. Pruebas adicionales propuestas

### P0 — Sprint hardening

```python
# test_ncf_concurrent_posts — 2 threads, assert unique NCF
# test_void_ncf_requires_manager_group
# test_record_rules_company_isolation
# test_manual_ncf_validation_invalid_format
```

### P1 — Cobertura funcional

```python
# test_b03_debit_note
# test_b13_purchase
# test_report_606_lines
# test_export_csv_607
# test_fiscal_disabled_skips_ncf
```

### P2 — Regresión contable

```python
# test_payment_after_ncf_invoice — CxC unchanged
# test_stock_invoice_with_ncf — valuation unchanged
# test_in_refund_no_ncf_crash
```

---

## 7. CI recomendado

```bash
# Por módulo en DEV/CI
odoo -d test_db -i justech_l10n_do_base --test-enable --stop-after-init
odoo -d test_db -i justech_l10n_do_ncf --test-enable --stop-after-init
odoo -d test_db -i justech_l10n_do_reports --test-enable --stop-after-init

# E2E post-install
odoo shell -d test_db < scripts/validate-phase6-mvp.py
```

Añadir `coverage run` cuando disponible en imagen Docker.

---

## 8. Mapa cobertura visual

```
justech_l10n_do_base     [████████░░] ~60%
justech_l10n_do_ncf      [███████░░░] ~55%
justech_l10n_do_reports  [████░░░░░░] ~35%
─────────────────────────────────────
TOTAL ESTIMADO           [█████░░░░░] ~48%
```

---

## 9. Conclusión

Cobertura **insuficiente para producto comercial** (objetivo típico ≥75%). **Adecuada para MVP validado** en DEV con E2E manual. Priorizar tests P0 de concurrencia, seguridad y multi-empresa.

**Cobertura reportada:** **48%**
