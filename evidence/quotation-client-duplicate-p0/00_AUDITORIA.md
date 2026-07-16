# P0 Cotización — Auditoría (ANTES de corregir)

**Estado:** Fases 0–2 completadas. **Ningún reporte modificado aún.**

## Fase 0 — Backup

| Ítem | Ubicación |
|---|---|
| Backup Prod | `/opt/odoo-backups/quotation-client-duplicate-p0-20260716_102807/` |
| Vistas Studio / QWeb dump | `views_db/studio/` |
| Dump `ir_ui_view` | `views_db/ir_ui_view.dump.fc` |
| PDFs ANTES | `before_pdfs/` (+ copia local en `evidence/.../before/`) |

## Hallazgos de Producción

| Hecho | Valor |
|---|---|
| Reporte activo | `sale.action_report_saleorder` → **`sale.report_saleorder`** |
| Layout 4 empresas | `web.external_layout_bubble` (id 211) |
| `justech_report_design` | **uninstalled** en Prod (no aplica el diseño Hellenia del repo) |
| `hellenia_reports` | No instalado |
| Personalización | Odoo Studio activo sobre `sale.report_saleorder_document` y bubble |

## Origen exacto del bloque duplicado

### BLOQUE 1 (incorrecto — bajo logo/datos empresa)

En `sale.report_saleorder_document` (arch DB / Studio):

```xml
<t t-set="address">
  <div t-field="doc.partner_id" ... contact address+name .../>
  <p t-if="doc.partner_id.vat">... RNC ...</p>
</t>
```

Ese `address` se imprime vía:

`web.external_layout_bubble` → `<t t-call="web.address_layout"/>`

Resultado: cliente aparece **debajo** de los datos de la empresa.

### BLOQUE 2 (correcto — bajo título Cotización)

Mismo documento, div `#informations` / `name="customer_info"`:

```xml
<div class="fw-bold mb-1">Cliente</div>
<div t-field="doc.partner_id" .../>
```

Este es el cuadro que debe **permanecer**.

## Evidencia ANTES (4 empresas)

| Empresa | SO | PDF/PNG |
|---|---|---|
| JUSTECH S.R.L. | C-0003881 | `before/1_JUSTECH_SRL_C-0003881.*` |
| PlugSafe SRL | CPS-0000093 | `before/2_PlugSafe_SRL_CPS-0000093.*` |
| Just Office SRL | CJO-0000612 | `before/3_Just_Office_SRL_CJO-0000612.*` |
| Omni Solutions SRL | CJT-0003590 | `before/4_Omni_Solutions_SRL_CJT-0003590.*` |

Duplicidad confirmada visualmente en Justech y Just Office (mismo patrón en las 4: layout bubble compartido).

## Corrección propuesta (NO aplicada)

Herencia QWeb mínima sobre `sale.report_saleorder_document`:

- **XPath:** `//t[@t-set='address']`
- **Acción:** `replace` → `<t t-set="address" t-value="False"/>` (o vacío)
- **No tocar:** `#informations` / `customer_info`, logo, empresa, tablas, totales, firmas

Afecta a las 4 empresas (mismo layout/reporte).

## Pendiente

Aprobación explícita para Fase 3 (corregir Prod) + Fases 4–5 (DESPUÉS + regresión).
