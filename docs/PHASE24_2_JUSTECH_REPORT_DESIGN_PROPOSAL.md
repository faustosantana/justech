# Fase 24.2 — Localización visual de reportes Justech (`justech_report_design`)

**Estado enfoque:** ✅ **APROBADO** (paquete central, reportes paralelos, diseño/SCSS/paperformat comunes)  
**Estado implementación:** ⛔ **BLOQUEADA** hasta revisión visual final cotización 24.1  
**Entorno:** TEST (`hellenia_test`) exclusivamente  
**PROD:** Bloqueado  
**Fecha:** 2026-07-02

> Ver estado global: `docs/PHASE24_STATUS.md`

### Marco acordado

| Principio | Detalle |
|-----------|---------|
| Naturaleza | Localización visual de reportes impresos Justech |
| Estrategia | Reportes paralelos primero; estándar Odoo intacto |
| Diseño | Base común compartida (header, banda, tablas, footer) |
| SCSS | Un bundle común en `web.report_assets_common` |
| Paperformat | Registro común Justech (+ variante compacta cotización si aplica) |
| Técnica | Templates propios; **sin xpath frágiles** |
| PROD | No tocar |
| Default | No reemplazar reportes estándar hasta aprobación explícita |
| Alcance inmediato | **Solo cotización** — factura, compra, pago e inventario permanecen en planificación |

---

## 1. Cambio de enfoque

| Antes (24.1) | Ahora (24.2 planificado) |
|--------------|--------------------------|
| Un reporte paralelo de cotización | **Paquete central** de reportes impresos Justech |
| Módulo experimental aislado | `custom/justech_report_design` como **localización/reportes** de diseño |
| Validar 1 documento | Cubrir progresivamente los 8 tipos de impresión operativa |
| Coexistir con `hellenia_reports` | Migrar diseño a templates propios; **no más xpath frágiles** en estándar Odoo |

**Principio:** En TEST, el usuario debe poder imprimir con diseño Justech desde el menú **Imprimir**. Primero en **paralelo** (convive con estándar); después de aprobar cada documento, evaluar si pasa a ser el **default**.

---

## 2. Auditoría del estado actual

### 2.1 Dos arquitecturas en conflicto

```
┌─────────────────────────────────────────────────────────────────┐
│  PATRÓN A — hellenia_reports (herencia xpath)                   │
│  web.external_layout → external_layout_hellenia                 │
│  inherit_id en sale/account/purchase/stock estándar             │
│  + paperformat override en ir.actions.report estándar           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PATRÓN B — justech_report_design (24.1, paralelo limpio)       │
│  web.html_container → template propio + SCSS jt-hq-*            │
│  ir.actions.report nuevo con binding_model_id                     │
│  Sin inherit del documento estándar                             │
└─────────────────────────────────────────────────────────────────┘
```

**Problema:** El usuario imprime hoy según qué acción elija, pero el diseño “oficial” Hellenia sigue repartido entre xpath de `hellenia_reports`, layout externo y la cotización paralela 24.1. Eso genera:

- Fragilidad ante upgrades Odoo (xpath en `//strong[text()='Invoice Date']`)
- Duplicación visual (cotización 24.1 ≠ cotización `hellenia_reports`)
- Dificultad para unificar familia gráfica

**Decisión propuesta:** Fase 24.2 consolida todo en **Patrón B**, reutilizando helpers fiscales existentes solo como **lectura de campos**, no como herencia QWeb.

### 2.2 Inventario de reportes estándar Odoo 19 (objetivo)

| # | Documento negocio | Modelo Odoo | `ir.actions.report` (XML ID) | `report_name` (wrapper) | Template documento estándar |
|---|-------------------|-------------|------------------------------|-------------------------|-----------------------------|
| 1 | Cotización / OV borrador | `sale.order` | `sale.action_report_saleorder` | `sale.report_saleorder` | `sale.report_saleorder_raw` → `sale.report_saleorder_document` |
| 1b | Pedido confirmado | `sale.order` | mismo | mismo | mismo (rama `state=sale`) |
| 1c | Pro forma | `sale.order` | `sale.action_report_pro_forma_invoice` | `sale.report_saleorder_pro_forma` | variante pro forma |
| 2 | Factura cliente | `account.move` | `account.account_invoices` | `account.report_invoice_with_payments` | `account.report_invoice_document` |
| 3 | Nota de crédito | `account.move` | `account.account_invoices` | mismo | mismo (`move_type=out_refund`) |
| 3b | Nota de débito | `account.move` | `account.account_invoices` | mismo | mismo (tipo B03 / lógica fiscal) |
| 4 | Recibo de pago | `account.payment` | `account.action_report_payment_receipt` | `account.report_payment_receipt` | `account.report_payment_receipt_document` |
| 5 | Orden de compra | `purchase.order` | `purchase.action_report_purchase_order` | `purchase.report_purchaseorder` | `purchase.report_purchaseorder_document` |
| 6 | RFQ compra | `purchase.order` | `purchase.report_purchase_quotation` | `purchase.report_purchasequotation` | `purchase.report_purchasequotation_document` |
| 7 | Albarán / delivery slip | `stock.picking` | `stock.action_report_delivery` | `stock.report_deliveryslip` | `stock.report_delivery_document` |
| 8 | Picking / operaciones | `stock.picking` | `stock.action_report_picking` | `stock.report_picking` | `stock.report_picking` |

### 2.3 Customizaciones actuales (`hellenia_reports` + satélites)

| Documento | Archivo custom | Mecanismo | Riesgo xpath |
|-----------|----------------|-----------|--------------|
| Cotización | `report/report_sale_quotation.xml` | Reemplaza cuerpo en `sale.report_saleorder_raw` si draft/sent | Medio |
| OV confirmada | `report/report_sale_order.xml` | inherit `sale.report_saleorder_document` | Alto |
| Factura/NC/ND | `report/report_invoice.xml` | inherit + cleanup NCF | Alto |
| NCF campos | `justech_l10n_do_ncf/report/report_invoice.xml` | inherit factura | Medio |
| Recibo pago | `report/report_payment_receipt.xml` + `hellenia_account` | inherit cadena 3 niveles | Alto |
| PO / RFQ | `report/report_purchase.xml` | inherit | Alto |
| Albarán / picking | `report/report_stock.xml` | inherit | Alto |
| Layout global | `report/layout_templates.xml` | `external_layout_hellenia` en compañía | Afecta todo lo que usa external_layout |

**Evidencia diagnóstico TEST:** `evidence/report-templates-diagnostic/report_templates_diagnostic.json`  
**Guías corporativas:** `docs/CORPORATE_DOCUMENT_GUIDELINES.md`, `docs/HELLENIA_DESIGN_SYSTEM.md`

### 2.4 Lo ya implementado en `justech_report_design` (24.1)

| Ítem | Estado |
|------|--------|
| Cotización paralela | ✅ TEST PASS |
| Template | `report_hellenia_quotation_document` + `hellenia_quotation_body` |
| SCSS | `hellenia_quotation.scss` (clases `jt-hq-*`) |
| Paperformat | `Hellenia Quotation Paperformat` |
| Acción menú | `Cotización Hellenia (Diseño)` |
| Dependencias | solo `sale` |

---

## 3. Visión objetivo del módulo

```
custom/justech_report_design/
├── __manifest__.py
├── data/
│   ├── paperformat_data.xml          # paperformat(s) Justech
│   └── report_actions_data.xml       # acciones paralelas (fase 1)
├── models/
│   ├── sale_order.py                 # ✅ existente
│   ├── account_move.py               # lectura fiscal (delegar helpers)
│   ├── account_payment.py            # retenciones / resumen pago
│   ├── purchase_order.py
│   └── stock_picking.py
├── report/
│   ├── common/
│   │   ├── jt_document_shell.xml     # web.html_container + article.jt-page
│   │   ├── jt_header.xml             # logo + empresa
│   │   ├── jt_band.xml               # banda verde título + número
│   │   ├── jt_footer.xml             # contacto + paginación
│   │   └── jt_signatures.xml         # entregado/recibido
│   ├── sale/
│   │   ├── jt_quotation_body.xml     # migrar desde 24.1
│   │   └── jt_sale_order_body.xml    # OV confirmada (si difiere)
│   ├── account/
│   │   ├── jt_invoice_body.xml       # factura + NC + ND (condicionales)
│   │   └── jt_payment_receipt_body.xml
│   ├── purchase/
│   │   ├── jt_purchase_order_body.xml
│   │   └── jt_rfq_body.xml
│   └── stock/
│       ├── jt_delivery_body.xml
│       └── jt_picking_body.xml
└── static/src/scss/
    ├── justech_reports_base.scss     # tokens, header, band, tablas, totales
    └── justech_reports_docs.scss     # modificadores por tipo (.jt-doc-invoice, etc.)
```

**Manifest `assets` (propuesto):**

```python
"assets": {
    "web.report_assets_common": [
        "justech_report_design/static/src/scss/justech_reports_base.scss",
        "justech_report_design/static/src/scss/justech_reports_docs.scss",
    ],
},
```

**Dependencias evolutivas:**

```python
"depends": [
    "sale",              # 24.1 ✅
    "account",           # factura, NC, recibo
    "purchase",          # PO, RFQ
    "stock",             # albarán, picking
    # Lectura fiscal — NO heredar sus QWeb:
    "justech_l10n_do_ncf",  # campos justech_do_ncf, document_type
    # Retenciones en recibo — solo si campos existen:
    "hellenia_account",     # hellenia_withholding_line_ids, etc.
],
```

> **Nota:** `hellenia_reports` **no** debe ser dependencia del paquete de diseño. Convivirán en TEST hasta deprecar visualmente las herencias xpath.

---

## 4. Reportes Justech a crear (propuesta)

Convención de nombres:

- Acción menú: **`Justech — {Documento}`** (prefijo uniforme)
- XML ID acción: `justech_report_design.action_report_jt_{tipo}`
- Template documento: `justech_report_design.report_jt_{tipo}_document`
- Cuerpo parcial: `justech_report_design.jt_{tipo}_body`

### Matriz completa

| # | Menú Imprimir (propuesto) | XML ID acción | Modelo | Template documento | Prioridad impl. |
|---|---------------------------|---------------|--------|-------------------|-----------------|
| 1 | **Justech — Cotización** | `action_report_jt_quotation` | `sale.order` | `report_jt_quotation_document` | ✅ Hecho (renombrar opcional) |
| 1b | **Justech — Pedido de venta** | `action_report_jt_sale_order` | `sale.order` | `report_jt_sale_order_document` | Alta (mismo modelo, distinto título/banda) |
| 2 | **Justech — Factura** | `action_report_jt_invoice` | `account.move` | `report_jt_invoice_document` | Alta |
| 3 | **Justech — Nota de crédito** | `action_report_jt_credit_note` * | `account.move` | `report_jt_credit_note_document` * | Media |
| 4 | **Justech — Recibo de pago** | `action_report_jt_payment_receipt` | `account.payment` | `report_jt_payment_receipt_document` | Media-alta |
| 5 | **Justech — Orden de compra** | `action_report_jt_purchase_order` | `purchase.order` | `report_jt_purchase_order_document` | Media |
| 6 | **Justech — Solicitud de cotización** | `action_report_jt_rfq` | `purchase.order` | `report_jt_rfq_document` | Media |
| 7 | **Justech — Albarán** | `action_report_jt_delivery` | `stock.picking` | `report_jt_delivery_document` | Media |
| 8 | **Justech — Picking** | `action_report_jt_picking` | `stock.picking` | `report_jt_picking_document` | Baja |

\* **Decisión pendiente:** Factura y NC pueden ser **un solo template** con banda condicional (`move_type`, `justech_do_document_type_id`) — como hace Odoo estándar. Menú podría exponer dos acciones con `domain` en el modelo o un solo ítem “Justech — Factura / NC”. Ver §8.

**No incluidos en 24.2 inicial (fuera de alcance salvo decisión):**

- Pro forma (`sale.action_report_pro_forma_invoice`)
- Estado de cuenta / followup
- Export PDF contable (`account_reports`)
- Reportes DGII 606/607/623

---

## 5. Campos obligatorios por documento

Solo campos **existentes** en Odoo/custom — validar con `_fields` antes de usar en QWeb.

### 5.1 Cotización / Pedido venta (`sale.order`)

| Bloque | Campos | Notas |
|--------|--------|-------|
| Empresa | `company_id.logo`, `.name`, `.vat`, `.phone`, `.email`, `.website`, `.street`, `.city` | Header común |
| Documento | `name`, `date_order`, `validity_date`, `state` | Banda: COTIZACIÓN vs PEDIDO |
| Cliente | `partner_id.name`, `.vat`, `.phone`, `.email` | **No** `mobile` |
| Vendedor | `user_id.name` | |
| Pago | `payment_term_id` → helper `get_jt_payment_term_display()` | |
| Líneas | `order_line` vía `_get_order_lines_to_report()` | qty, uom, price, subtotal |
| Totales | `amount_untaxed`, `amount_tax`, `amount_total`, `currency_id` | ITBIS 18% etiqueta fija RD |
| Condiciones | `note` o texto default | Solo cotización |
| Firmas | estáticas | Entregado / Recibido |

### 5.2 Factura (`account.move` — `out_invoice`, `in_invoice`)

| Bloque | Campos | Notas |
|--------|--------|-------|
| Título fiscal | `hellenia_fiscal_document_title()` * | Helper en `hellenia_reports.models.account_move` — reutilizar o mover a mixin |
| NCF | `justech_do_ncf`, `justech_do_document_type_id` | De `justech_l10n_do_ncf` |
| Leyenda DGII | `hellenia_ncf_legal_note()` * | B02 vs crédito fiscal |
| Cliente | `partner_id` (contact widget o campos sueltos) | |
| Fechas | `invoice_date`, `invoice_date_due`, `delivery_date` | |
| Referencia | `payment_reference`, `ref`, `invoice_origin` | |
| Líneas | `invoice_line_ids` | descripción, qty, price, taxes, subtotal |
| Totales | `amount_untaxed`, `amount_tax`, `amount_total`, `currency_id` | |
| Banco | `partner_bank_id` | Si aplica concepto pago |

\* Reutilizar métodos existentes; no duplicar lógica fiscal en QWeb.

### 5.3 Nota de crédito (`account.move` — `out_refund`)

Mismos campos que factura + banda **NOTA DE CRÉDITO** + referencia a factura origen si existe (`reversed_entry_id` / `ref`).

### 5.4 Recibo de pago (`account.payment`)

Según `docs/CORPORATE_DOCUMENT_GUIDELINES.md` §3.3:

| Campo | Origen |
|-------|--------|
| Cliente/proveedor | `partner_id`, `partner_type` |
| Factura afectada | `reconciled_invoice_ids` / `reconciled_bill_ids` |
| NCF factura | `justech_do_ncf` en moves reconciliados |
| Fecha pago | `date` |
| Método | `payment_method_id.name` |
| Banco | `journal_id.bank_account_id` |
| Referencia | `hellenia_payment_reference` o `memo` |
| Monto aplicado | `hellenia_applied_amount` (hellenia_account) |
| Retenciones | `hellenia_withholding_line_ids` (tabla) |
| Total retenido / neto | `hellenia_withholding_total`, `hellenia_net_transfer` |
| Auditoría | `create_uid.name`, `create_date` |
| Monto pago | `amount`, `currency_id` |

> Validar existencia de campos `hellenia_*` con `o._fields.get(...)` en QWeb (patrón ya usado en `hellenia_reports`).

### 5.5 Orden de compra (`purchase.order` — `state=purchase`)

| Bloque | Campos |
|--------|--------|
| Proveedor | `partner_id` |
| Comprador | `user_id` |
| Referencias | `partner_ref`, `name` |
| Fechas | `date_order`, `date_planned` |
| Envío | `dest_address_id`, `picking_type_id.warehouse_id` |
| Líneas | `order_line` — product, qty, price, taxes, subtotal |
| Totales | `amount_untaxed`, `amount_tax`, `amount_total` |
| Notas | `notes` |

### 5.6 RFQ (`purchase.order` — draft/sent/to approve)

Similar a PO pero:

- Banda: **SOLICITUD DE COTIZACIÓN**
- Líneas pueden incluir `date_planned` por línea
- Sin totales fiscales obligatorios si RFQ estándar Odoo no los muestra (validar diseño)

### 5.7 Albarán (`stock.picking` — delivery slip)

| Bloque | Campos |
|--------|--------|
| Tipo doc | `picking_type_id.code` → incoming/outgoing/internal |
| Referencia | `name`, `origin` |
| Partner | `partner_id` |
| Direcciones | según tipo (delivery, warehouse, vendor) |
| Fecha | `scheduled_date` / `date_done` |
| Líneas | `move_ids` / `move_line_ids` — producto, ordered, done qty |
| Pedido origen | `sale_id` / `purchase_id` si existe |
| Firmas | Entregado / Recibido |

### 5.8 Picking operaciones (`stock.picking` — report_picking)

Similar a albarán pero orientado a operación de almacén (ubicaciones origen/destino, barcode si aplica). Evaluar si el diseño Justech unifica con albarán o mantiene layout simplificado.

---

## 6. Diseño común reutilizable (base 24.1)

Extraído del HTML/QWeb aprobado en cotización (`jt-hq-*` → renombrar a `jt-*` global):

| Componente | Clases SCSS | Uso en todos los docs |
|------------|-------------|------------------------|
| Página | `.jt-page` | Contenedor `web.html_container` |
| Header | `.jt-hdr`, `.jt-logo`, `.jt-co` | Logo max 300×95px + datos empresa |
| Banda título | `.jt-band`, `.jt-band-title`, `.jt-band-num` | Verde `#3E4827`, título + número |
| Etiquetas | `.jt-lbl`, `.jt-val`, `.jt-title` | Cards cliente/proveedor/meta |
| Tabla líneas | `.jt-items` | thead verde, filas sin grid Excel |
| Totales | `.jt-totals`, `.grand` | Subtotal, ITBIS, TOTAL |
| Condiciones | `.jt-cond` | Cotización / notas PO |
| Firmas | `.jt-sigs` | Logística y ventas |
| Footer | `.jt-foot`, `.jt-pg` | Contacto + página X de Y |
| Separador | `.jt-line-soft`, `.jt-vdiv` | |

**Tokens** (de `HELLENIA_DESIGN_SYSTEM.md`):

- Primario: `#3E4827`
- Texto muted labels: `#888888`
- Fondo: blanco
- Fuente: `DejaVu Sans`
- Sin `web.external_layout`

### Partials QWeb comunes (propuesta)

```xml
<!-- Ejemplo de uso en cada documento -->
<t t-call="justech_report_design.jt_document_shell">
    <t t-set="jt_doc_title" t-value="'COTIZACIÓN'"/>
    <t t-set="jt_doc_number" t-value="doc.name"/>
    <t t-set="jt_body">
        <t t-call="justech_report_design.jt_quotation_body"/>
    </t>
</t>
```

---

## 7. Qué cambia por documento

| Documento | Banda título | Bloque partner | Tabla | Totales | Específico |
|-----------|--------------|----------------|-------|---------|------------|
| Cotización | COTIZACIÓN | Cliente + Vendedor | 5 cols precio | ITBIS 18% | Condiciones, espaciador dinámico |
| Pedido venta | PEDIDO DE VENTA | igual | igual | igual | Sin validez; puede omitir condiciones default |
| Factura | FACTURA DE CRÉDITO FISCAL / etc. | Cliente | + impuestos col | ITBIS | **Caja NCF** + leyenda DGII |
| Nota crédito | NOTA DE CRÉDITO | Cliente | igual factura | igual | Ref. factura origen |
| Recibo pago | RECIBO DE PAGO | Cliente/Proveedor | tabla facturas + retenciones | aplicado/retenido/neto | Sin tabla productos |
| PO | ORDEN DE COMPRA | Proveedor + Comprador | con descuento | sí | `partner_ref` |
| RFQ | SOLICITUD DE COTIZACIÓN | Proveedor | sin precio o con | opcional | fecha esperada por línea |
| Albarán | GUÍA ENTREGA / RECEPCIÓN | según tipo picking | producto/qty entregada | no | firmas obligatorias |
| Picking | OPERACIÓN DE ALMACÉN | almacén | ubicaciones | no | más técnico |

---

## 8. Menú Imprimir — comportamiento en TEST

### Fase 1 — Paralelo (24.2 implementación)

Cada modelo muestra **acciones adicionales** con prefijo `Justech —`:

**Ejemplo `sale.order`:**

| Acción existente (intacta) | Acción nueva Justech |
|----------------------------|----------------------|
| Cotización en PDF | **Justech — Cotización** |
| Cotización/orden | **Justech — Pedido de venta** (domain: `state in sale,done`) |
| Factura PROFORMA | (sin cambio) |
| — | **Justech — Cotización** (domain: `state in draft,sent`) |

**Ejemplo `account.move`:**

| Estándar | Justech |
|----------|---------|
| Factura | **Justech — Factura** (domain: `move_type=out_invoice`) |
| — | **Justech — Nota de crédito** (domain: `move_type=out_refund`) |

**Ejemplo `account.payment`:**

| Estándar | Justech |
|----------|---------|
| Recibo de pago | **Justech — Recibo de pago** |

**Ejemplo `purchase.order`:**

| Estándar | Justech |
|----------|---------|
| Orden de compra | **Justech — Orden de compra** |
| Solicitud de cotización | **Justech — Solicitud de cotización** |

**Ejemplo `stock.picking`:**

| Estándar | Justech |
|----------|---------|
| Albarán | **Justech — Albarán** |
| Operaciones de picking | **Justech — Picking** |

Implementación técnica: `binding_model_id` + `binding_type=report` en cada `ir.actions.report` nuevo. Opcional: `groups_id` para limitar a usuarios de prueba en TEST.

### Fase 2 — Default (post-aprobación, no ejecutar aún)

Opciones evaluadas:

| Opción | Pros | Contras |
|--------|------|---------|
| A. Desactivar binding estándar | Menú limpio | Rompe hábito usuario / integraciones |
| B. `sequence` menor en acción Justech | Menú las lista primero | Siguen apareciendo ambas |
| C. Redirect en `ir.actions.report._render_qweb_pdf` | Transparente al usuario | Acoplamiento; difícil rollback |
| D. Configuración por compañía `jt_default_reports=True` | Controlado | Más desarrollo |

**Recomendación:** Fase 2 usar **opción D** (flag en `res.company`) tras aprobar los 8 documentos.

---

## 9. Paperformat

| Paperformat | Uso propuesto | Config |
|-------------|---------------|--------|
| `Justech Letter Standard` | Factura, PO, RFQ, recibo, albarán | Letter, márgenes 8mm, dpi 90 |
| `Justech Letter Compact` | Cotización, pedido venta | Letter, márgenes 5/8/8/8, dpi 90 (actual 24.1) |

Unificar en un solo registro si el diseño lo permite; cotización puede mantener márgenes más compactos.

---

## 10. Estrategia de validación por PDF

Por cada documento, replicar patrón 24.1:

```
scripts/phase24-2-{doc}-test.py   → odoo shell en hellenia_test
evidence/phase24-2-{doc}/         → PDFs, PNGs, validation.json
packages/phase24-2-{doc}-review/  → ZIP descargable
```

### Checks automáticos comunes

- [ ] `pass: true` en `validation.json`
- [ ] PDF válido (`%PDF` header)
- [ ] Clases `jt-page`, `jt-band` en HTML renderizado
- [ ] Sin `<style type="text/css">` inline masivo en template
- [ ] Sin `external_layout` hellenia
- [ ] Sin campos inexistentes / sin `partner.mobile`
- [ ] `no_replace_standard: true` (sin inherit en vistas estándar)
- [ ] Reporte estándar sigue generando PDF

### Casos de prueba mínimos por documento

| Documento | Casos PDF |
|-----------|-----------|
| Cotización | 1 / 5 / 25 líneas ✅ hecho |
| Pedido venta | 1 confirmado, multi-línea |
| Factura | B01 crédito fiscal, B02 consumo |
| Nota crédito | 1 NC con ref a factura |
| Recibo pago | sin retención, con retención parcial |
| PO | 1 y 10 líneas |
| RFQ | borrador, 5 líneas |
| Albarán | salida cliente, entrada proveedor |
| Picking | operación interna |

### Validación visual manual

Comparar contra:

- Paquete 24.1 (`packages/phase24-1-hellenia-quotation-review.zip`)
- `docs/CORPORATE_DOCUMENT_GUIDELINES.md`
- HTML aprobado Fausto (cuando se entregue por documento)

---

## 11. Plan de implementación por oleadas (sin ejecutar)

```
BLOQUEANTE: Aprobación visual cotización 24.1
     │
     ▼
Oleada 1 — Fundación (24.2.0)
  • Refactor justech_report_design: common partials + SCSS base unificado
  • Renombrar clases jt-hq-* → jt-* (o alias compatibilidad)
  • Migrar cotización 24.1 al nuevo esqueleto común
  • Menú: "Justech — Cotización" (+ pedido venta si aplica)
     │
     ▼
Oleada 2 — Ventas completas (24.2.1)
  • Pedido de venta confirmado
  • Validación + paquete revisión
     │
     ▼
Oleada 3 — Facturación (24.2.2)  ⚠️ mayor riesgo fiscal
  • Factura + NC (template unificado)
  • Solo lectura campos NCF; sin tocar DGII/contabilidad
  • Validación B01/B02/NC
     │
     ▼
Oleada 4 — Pagos (24.2.3)  ⚠️ retenciones
  • Recibo de pago con tabla retenciones condicional
     │
     ▼
Oleada 5 — Compras (24.2.4)
  • PO + RFQ
     │
     ▼
Oleada 6 — Inventario (24.2.5)
  • Albarán + Picking
     │
     ▼
Oleada 7 — Portal PDF (24.2.6)
  • Evaluar exposición token / rutas portal
     │
     ▼
Oleada 8 — Default reports (24.3)
  • Flag compañía + decisión reemplazo menú
  • Deprecar herencias xpath hellenia_reports (NO borrar fiscal)
```

**Cada oleada:** TEST only → paquete revisión → OK visual → siguiente.

---

## 12. Relación con `hellenia_reports`

| Componente hellenia_reports | Tratamiento propuesto |
|-----------------------------|----------------------|
| `external_layout_hellenia` | Ignorar en Justech (no usar external_layout) |
| xpath reportes venta/compra/stock | **Congelar** — no ampliar |
| xpath factura/pago | Mantener en TEST hasta Oleada 3-4 validada |
| `ir_actions_report.py` paperformat swap | No duplicar; Justech usa su paperformat en su acción |
| Helpers `account_move` fiscales | **Reutilizar** vía dependencia o mixin compartido futuro |
| `hellenia_document_footer_blocks` | Reemplazar por `jt_footer` común |

**No eliminar `hellenia_reports` en 24.2** — convivencia controlada hasta sustitución completa aprobada.

---

## 13. Riesgos y decisiones abiertas

| # | Decisión | Opciones | Recomendación |
|---|----------|----------|---------------|
| D1 | ¿Factura y NC en un template o dos acciones? | Uno / Dos | Un template, dos acciones con domain |
| D2 | ¿Pedido venta separado de cotización? | Uno / Dos | Dos (bandas distintas) |
| D3 | ¿Prefijo menú "Justech —" o "Hellenia (Diseño)"? | Marca | **Justech —** (paquete localización) |
| D4 | ¿Dependencia `hellenia_account` para recibo? | Sí / mixin | Sí, con guards `_fields` |
| D5 | ¿Unificar albarán y picking? | Uno / Dos | Dos templates, SCSS compartido |
| D6 | ¿Cuándo deprecar xpath hellenia_reports? | Por doc / global | Por documento tras OK visual |
| D7 | Portal PDF | Fase 24.2.6 | Diferido |

---

## 14. Criterios de éxito Fase 24.2 (TEST)

- [ ] Los 8 tipos tienen acción **Justech —** en menú Imprimir
- [ ] PDFs conservan diseño común (banda verde, logo, sin Excel)
- [ ] Reportes estándar Odoo siguen funcionando en paralelo
- [ ] Sin errores QWeb ni campos inexistentes
- [ ] Sin cambios en PROD
- [ ] Paquete revisión por documento + validación automática
- [ ] `hellenia_reports` xpath no extendido

---

## 15. Próximo paso inmediato

1. **Usuario:** revisar visualmente PDFs en `packages/phase24-1-hellenia-quotation-review.zip`
2. **Aprobar o listar ajustes** cotización
3. **Entonces:** ejecutar Oleada 1 (fundación SCSS común + refactor cotización)
4. **No iniciar** factura/compra/inventario hasta completar paso 3

---

## Referencias

| Recurso | Ruta |
|---------|------|
| Módulo actual | `custom/justech_report_design/` |
| Paquete revisión 24.1 | `packages/phase24-1-hellenia-quotation-review.zip` |
| Herencias actuales | `custom/hellenia_reports/report/` |
| Diagnóstico TEST | `evidence/report-templates-diagnostic/report_templates_diagnostic.json` |
| Guías visuales | `docs/CORPORATE_DOCUMENT_GUIDELINES.md` |
| Design system | `docs/HELLENIA_DESIGN_SYSTEM.md` |
| Checklist PROD (bloqueado) | `packages/phase24-1-hellenia-quotation-review/PROD_PROMOTION_CHECKLIST.md` |

**Estado:** ✅ Enfoque aprobado — ⛔ implementación bloqueada hasta OK visual ZIP 24.1.
