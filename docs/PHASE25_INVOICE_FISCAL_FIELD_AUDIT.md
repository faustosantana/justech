# Fase 25 — Auditoría de campos factura fiscal Hellenia

**Fecha:** 2026-07-02  
**Base de datos objetivo:** `hellenia_test` (solo TEST)  
**Módulos auditados:** `account`, `justech_l10n_do_base`, `justech_l10n_do_ncf`, `hellenia_reports`, `hellenia_ux`, `hellenia_account`, `justech_report_design`

---

## 1. Resumen ejecutivo

| Requisito diseño | Campo real | Modelo | Módulo | Estado |
|------------------|------------|--------|--------|--------|
| No. factura | `name` | `account.move` | Odoo `account` | ✅ Existe |
| NCF | `justech_do_ncf` | `account.move` | `justech_l10n_do_ncf` | ✅ Existe |
| Tipo comprobante | `justech_do_document_type_id.name` | `account.move` → `justech.do.fiscal.document.type` | `justech_l10n_do_ncf` / `justech_l10n_do_base` | ✅ Existe |
| Secuencia fiscal | Asignación automática vía `justech_do_ncf_range_id` | `account.move` | `justech_l10n_do_ncf` | ✅ Existe (al publicar) |
| Fecha emisión | `invoice_date` | `account.move` | Odoo `account` | ✅ Existe |
| Fecha vencimiento | `invoice_date_due` | `account.move` | Odoo `account` | ✅ Existe |
| Cliente | `partner_id` | `account.move` | Odoo `account` | ✅ Existe |
| RNC cliente | `partner_id.vat` | `res.partner` | Odoo `base` | ✅ Existe |
| RNC empresa | `company_id.vat` | `res.company` | Odoo `base` | ✅ Existe |
| Dirección cliente | `partner_id` (street, city, …) | `res.partner` | Odoo `base` | ✅ Existe |
| Condiciones de pago | `invoice_payment_term_id` | `account.move` | Odoo `account` | ✅ Existe |
| Vendedor | `invoice_user_id` | `account.move` | Odoo `account` | ✅ Existe |
| Moneda | `currency_id` | `account.move` | Odoo `account` | ✅ Existe |
| Tasa de cambio | `invoice_currency_rate` | `account.move` | Odoo 19 `account` | ✅ Existe (no requerido en PDF aprobado) |
| Líneas | `invoice_line_ids` | `account.move` | Odoo `account` | ✅ Existe |
| Cantidad | `quantity` | `account.move.line` | Odoo `account` | ✅ Existe |
| Precio unitario | `price_unit` | `account.move.line` | Odoo `account` | ✅ Existe |
| Descuento línea | `discount` (%) | `account.move.line` | Odoo `account` | ✅ Existe |
| Subtotal línea | `price_subtotal` | `account.move.line` | Odoo `account` | ✅ Existe |
| ITBIS documento | Líneas impuesto positivas / `amount_tax` neto | `account.move` / `account.move.line` | Odoo + impuestos RD | ✅ Existe |
| ITBIS por línea | Cálculo desde `tax_ids` en línea | `account.move.line` | Odoo `account` | ✅ Calculable |
| Subtotal | `amount_untaxed` | `account.move` | Odoo `account` | ✅ Existe |
| Total | `amount_total` | `account.move` | Odoo `account` | ✅ Existe |
| Retenciones | Líneas impuesto negativo (`tax_line_id.amount < 0`) | `account.move.line` | `hellenia_ux` + impuestos | ✅ Existe si aplican |
| Retenciones pago | `hellenia_withholding_line_ids` | `account.move` | `hellenia_account` | ✅ Existe (flujo pago; no en PDF factura estándar) |
| Observaciones / términos | `narration` | `account.move` | Odoo `account` | ✅ Existe (campo editable en factura) |
| Términos empresa (fallback) | `hellenia_terms_conditions` | `res.company` | `hellenia_reports` | ✅ Existe (solo si `narration` vacío) |

---

## 2. Detalle por modelo

### 2.1 `account.move` — campos fiscales y comerciales

| Campo | Tipo | Uso en PDF Justech |
|-------|------|-------------------|
| `name` | Char | No. FACTURA en banda verde |
| `invoice_date` | Date | Fecha de emisión |
| `invoice_date_due` | Date | Fecha de vencimiento |
| `partner_id` | Many2one | Bloque cliente |
| `invoice_user_id` | Many2one | Vendedor |
| `invoice_payment_term_id` | Many2one | Condiciones de pago |
| `currency_id` | Many2one | Formato moneda DOP/USD |
| `invoice_currency_rate` | Float | Solo validación multi-moneda (no en diseño aprobado) |
| `amount_untaxed` | Monetary | Subtotal totales |
| `amount_tax` | Monetary | Neto impuestos (ITBIS − retenciones en documento) |
| `amount_total` | Monetary | Total |
| `narration` | Html/Text | Observaciones / términos editables |
| `justech_do_ncf` | Char | NCF en banda verde |
| `justech_do_document_type_id` | Many2one | Tipo de comprobante |
| `justech_do_ncf_range_id` | Many2one | Rango NCF (asignación al publicar) |
| `move_type` | Selection | Filtro `out_invoice` / `out_refund` |
| `state` | Selection | Borrador / publicado |

**Campos adicionales (no en bloque principal del diseño):**

| Campo | Uso |
|-------|-----|
| `ref` | Referencia interna |
| `invoice_origin` | Origen pedido |
| `justech_do_origin_ncf` | NCF origen (NC/ND) |
| `justech_do_ncf_modified` | NCF modificado DGII |
| `hellenia_ret_isr_gov` | Toggle retención gobierno 5% (`hellenia_ux`) |

### 2.2 `account.move.line`

| Campo | Uso en tabla PDF |
|-------|-----------------|
| `name` | Descripción |
| `quantity` | Cant. |
| `price_unit` | P. Unit. |
| `discount` | % → monto descuento calculado |
| `price_subtotal` | Subtotal línea |
| `tax_ids` | Cálculo ITBIS por línea |
| `display_type` | Filtrar solo `product` |

### 2.3 `res.partner`

| Campo | Uso |
|-------|-----|
| `name` | Nombre cliente |
| `vat` | RNC / cédula |
| `street`, `city`, `phone`, `email` | Datos contacto |
| `justech_do_partner_id_type` | Tipo ID DGII (`justech_l10n_do_base`) |

### 2.4 `res.company`

| Campo | Uso |
|-------|-----|
| `name`, `vat`, `street`, `phone`, `email`, `website` | Encabezado derecho |
| `logo` | Logo izquierda |
| `hellenia_terms_conditions` | Fallback observaciones (`hellenia_reports`) |

### 2.5 `justech.do.fiscal.document.type` (catálogo)

| Prefix | Nombre instalado | move_type |
|--------|------------------|-----------|
| B01 | Factura de Crédito Fiscal | out_invoice |
| B02 | Factura de Consumo | out_invoice |
| B03 | Nota de Débito | out_invoice |
| B04 | Nota de Crédito | out_refund |

---

## 3. Cálculo ITBIS y retenciones

### ITBIS (positivo)

- **Publicado:** suma de `account.move.line` con `tax_line_id` positivo cuyo nombre contiene `ITBIS` o tasa 18/16/9/8% (misma lógica que `justech.do.fiscal.report._move_itbis_amount`).
- **Borrador:** cálculo desde `invoice_line_ids` + `tax_ids`.

### Retenciones (solo si existen)

- **Publicado:** líneas con `tax_line_id.amount < 0` (retenciones ISR/ITBIS aplicadas en factura vía `hellenia_ux`).
- Etiqueta PDF: nombre del impuesto (`tax_line_id.name`), ej. `ISR 1%`.
- **No se inventan montos:** si no hay líneas de retención, el bloque no aparece.

### Descuentos

- **Columna:** monto = `quantity × price_unit × discount / 100` (solo si alguna línea tiene `discount > 0`).
- **Totales:** subtotal bruto, descuento total, subtotal neto (`amount_untaxed`).

---

## 4. Observaciones / términos — decisión

| Prioridad | Fuente | Editable en factura |
|-----------|--------|---------------------|
| 1 | `account.move.narration` | Sí (campo estándar Odoo «Términos y condiciones») |
| 2 | `res.company.hellenia_terms_conditions` | Empresa (`hellenia_reports`) — solo si narration vacío |

**No se crean campos nuevos.** El PDF imprime `narration` si tiene contenido; si no, `hellenia_terms_conditions` de la empresa.

---

## 5. Reportes existentes — NO reemplazar

| XML ID | report_name | Estado |
|--------|-------------|--------|
| `account.account_invoices` | `account.report_invoice_with_payments` | Producción — intacto |
| `account.report_invoice_document` | Herencia `hellenia_reports` + `justech_l10n_do_ncf` | Producción — intacto |

### Nuevo reporte paralelo (Fase 25)

| XML ID | report_name | Binding |
|--------|-------------|---------|
| `justech_report_design.action_report_justech_invoice` | `justech_report_design.report_justech_invoice_document` | `account.move` (menú Imprimir) |

---

## 6. Dependencias del módulo

| Módulo | Obligatorio para Fase 25 |
|--------|--------------------------|
| `account` | Sí |
| `sale` | Sí (cotización existente) |
| `justech_l10n_do_ncf` | Sí en Hellenia (campos NCF) |
| `hellenia_reports` | Opcional (fallback términos empresa) |

Los helpers usan `getattr` / `hasattr` para campos fiscales cuando el módulo NCF no está instalado (portabilidad).

---

## 7. Matriz de validación TEST

| # | Escenario | Campos clave |
|---|-----------|--------------|
| 1 | 1 línea | `invoice_line_ids` × 1 |
| 2 | Varias líneas | múltiples productos |
| 3 | Con descuento | `discount > 0` |
| 4 | Sin descuento | `discount = 0` |
| 5 | NCF fiscal B01 | `justech_do_ncf`, partner con `vat` |
| 6 | Consumo B02 | sin RNC obligatorio |
| 7 | Gubernamental | `hellenia_ret_isr_gov` si existe partner gobierno |
| 8 | Cliente con RNC | `partner_id.vat` |
| 9 | Cliente sin RNC | B02 |
| 10 | DOP | `currency_id` = DOP |
| 11 | USD | moneda extranjera |
| 12 | Envío correo | acción email estándar intacta |
| 13 | PDF backend | `_render_qweb_pdf` |
| 14 | Factura estándar Odoo | `account.account_invoices` sin cambios |
| 15 | DGII | sin modificar módulos DGII |
| 16 | Contabilidad | solo lectura de campos |
| 17 | Cotización | `sale.action_report_saleorder` sin cambios |

---

## 8. Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| `narration` vacío en facturas existentes | Fallback `hellenia_terms_conditions`; documentar en guía |
| Retenciones solo en impuestos negativos | Mostrar solo si `get_jt_invoice_retention_lines()` no vacío |
| NCF solo al publicar | Validaciones con facturas `posted` |
| Diseño 5 columnas en wkhtmltopdf | Layout con `div`, no `table` (misma lección Fase 24.2B) |

---

## 9. Referencias

- `docs/COMMERCIAL_DOCUMENTS_SPEC.md` §4
- `custom/hellenia_reports/models/account_move.py`
- `custom/justech_l10n_do_ncf/models/account_move.py`
- `custom/justech_report_design/report/quotation/hellenia_quotation_template.xml`
