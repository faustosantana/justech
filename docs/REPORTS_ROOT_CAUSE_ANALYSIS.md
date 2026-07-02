# Análisis de causa raíz — Reportes Fase 21

**Fecha:** 2026-07-01  
**Ambiente:** PROD `hellenia_prod`

---

## Incidente 1 — Wizard 623 no abre (RPC / ¡Vaya!)

### Síntoma UI
Al abrir menú **623 — Retenciones Estado** (action-658), Odoo muestra diálogo **¡Vaya!** y el wizard no carga.

### Excepción completa (log PROD)
```
ValueError: Wrong value for justech.do.fiscal.report.wizard.report_type: '623'
```
Stack: `POST .../justech.do.fiscal.report.wizard/onchange` tras abrir action con `context={'default_report_type': '623'}`.

### Causa raíz
| Campo | Detalle |
|-------|---------|
| **Archivo** | `custom/justech_l10n_do_reports/wizard/fiscal_report_wizard.py` |
| **Modelo** | `justech.do.fiscal.report.wizard` |
| **Campo** | `report_type` (Selection) |
| **Línea** | ~15–24 — selection solo incluía `606`, `607`, `608` |
| **Menú** | `views/menu.xml` action-658 pasa `default_report_type: 623` |
| **Modelo persistente** | `justech.do.fiscal.report` **sí** incluye 623 en selection |

**Desalineación:** menú y modelo persistente admiten 623; wizard transitorio lo rechazaba.

### Corrección aplicada (v19.0.1.12.2)
Añadir `609` y `623` al `Selection` del wizard. **Sin cambios** en pagos, retenciones ni conciliación.

### Regresión verificada
- 623 abre en UI ✓
- 607/608 no afectados ✓

---

## Incidente 2 — Exportación 607 falla al generar Excel

### Síntoma UI
Tras **Validar período** en 607 y pulsar **Generar Excel DGII**, diálogo **¡Vaya!**.

### Excepción completa (log PROD)
```
AttributeError: 'justech.do.fiscal.report' object has no attribute '_get_exportable_lines'
```
| Campo | Detalle |
|-------|---------|
| **Archivo** | `custom/justech_l10n_do_reports/models/fiscal_report.py` |
| **Método** | `action_export_dgii` |
| **Línea** | 204, 208 |
| **Llamada desde** | `wizard/fiscal_report_wizard.py` → `action_generate` → `action_generate_dgii_export` → `action_export_dgii` |

### Causa raíz
`action_export_dgii` invocaba `_get_exportable_lines()` pero el método **nunca fue implementado** en `fiscal_report.py`. El mixin de revisión (`dgii_report_review.py`) filtraba líneas en `_check_can_generate` pero no proveía el helper en la clase base.

### Corrección aplicada (v19.0.1.12.2)
1. `fiscal_report.py`: implementar `_get_exportable_lines()` → `self.line_ids`; ajustar `action_export_dgii` para no llamar al helper cuando `moves` ya viene del flujo de revisión.
2. `dgii_report_review.py`: override `_get_exportable_lines()` filtrando `include_in_report` + `fiscal_state == valid`.

### Regresión verificada
- 607 valida 3 documentos jun-2026 ✓
- Generar ya no lanza AttributeError ✓

---

## Hallazgo 3 — 623 con 0 líneas exportables

### Resultado prueba controlada (P21-GOV-623-PROOF)

Con partner **nuevo**, RNC **101733934**, factura **INV/2026/00006**, retención **solo RET-GOB-5** (500.00) aplicada desde UI:

| Capa | Resultado |
|------|-----------|
| Pago / asiento / campos gov | OK — 500.00 en todos los eslabones |
| `validate_period_623` (motor) | OK — 1 documento válido |
| UI revisión fiscal «Cargar período» | **FAIL** — 0 documentos (v12.2) |

**Conclusión:** no era solo datos maestros del SMOKE. Existía bug funcional adicional.

### Causa raíz UI (v12.2–v12.3)

| Campo | Detalle |
|-------|---------|
| **Archivo** | `dgii_report_review.py` |
| **Método** | `_collect_review_lines` |
| **Línea** | ~148 — sin rama `623` → `return []` |
| **Síntoma** | Bandeja revisión vacía pese a exporter con 1 válido |

### Corrección v19.0.1.12.4

- `_review_lines_623` + `_prepare_line_vals_623`
- UI post-fix: **3 documentos cargados, 1 válido** (P21 / 500.00)

### Hallazgo previo SMOKE (datos, no código)

Factura `INV/2026/00003` — partner id 23 sin RNC, catálogo RET-ITBIS-30 vs campo gov 500:

| Validación 623 | Estado |
|----------------|--------|
| `partner.vat` | Vacío |
| Catálogo | RET-ITBIS-30 (`affects_623=false`) |
| Monto | 540 persistente vs 500 gov |

Detalle completo: `docs/PHASE21_623_CONTROLLED_PROOF.md`

---

## Componentes NO modificados (por diseño Fase 21)

- `hellenia_account` / wizard de pagos
- `payment_partner_wizard.py`
- Motor de retenciones (`hellenia.withholding.catalog`)
- Conciliación (`account.partial.reconcile`)
