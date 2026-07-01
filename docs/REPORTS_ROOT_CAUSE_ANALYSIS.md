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

## Hallazgo 3 — 623 con 0 líneas exportables (datos, no código)

### Síntoma
Reporte 623 genera revisión pero **Total documentos: 0** tras **Cargar período**.

### Causa (validación DGII, no bug de exportador)
Factura `INV/2026/00003` con retención persistente:

| Validación 623 | Estado |
|----------------|--------|
| `partner.vat` (RNC) | **Vacío** en `SMOKE P13.4 CF` (partner id **23**) |
| `justech_do_dgii_fiscal_state` | `incomplete` |
| Referencia pago | vacía en `PBNKD/2026/00002` (fallback `payment.name` sí disponible) |
| Catálogo retención | **RET-ITBIS-30** (`affects_623=false`) — no es retención Estado |
| Monto retención contable | **540.00** (`hellenia_payment_withholding_line` id 18 = `account_move_line` id 354) |
| Monto campo gobierno factura | **500.00** (`justech_do_gov_withholding_amount`) — **discrepancia 40** |

**Archivo validación:** `dgii_623_exporter.py` → `_dgii_validate_single_move` líneas 217–251.

**Validación odoo shell jul-2026:** `valid=0`, `incomplete=2`. Error explícito: *"INV/2026/00003: la entidad SMOKE P13.4 CF no tiene RNC."*

### Cadena verificada (SQL PROD)

```
Pago PBNKD/2026/00002
  → Retención línea 18: 540.00 RET-ITBIS-30
  → Asiento línea 354: débito 540.00 ✓ (cuadra)
  → Factura INV/2026/00003: gov_withholding 500.00 ✗ (no cuadra con 540)
  → Reporte 623: 0 exportables (RNC + datos inconsistentes)
```

### Acción requerida (datos maestros / operación)
- Asignar RNC al partner canónico de prueba (id 22, no duplicado 23).
- Registrar transacción con catálogo **RET-GOB-5** (5% Gobierno), no ITBIS 30%.
- Alinear `justech_do_gov_withholding_amount` con línea persistente antes de certificar.

**No se modificó** lógica de retenciones en esta fase (sin causa demostrada en código).

---

## Componentes NO modificados (por diseño Fase 21)

- `hellenia_account` / wizard de pagos
- `payment_partner_wizard.py`
- Motor de retenciones (`hellenia.withholding.catalog`)
- Conciliación (`account.partial.reconcile`)
