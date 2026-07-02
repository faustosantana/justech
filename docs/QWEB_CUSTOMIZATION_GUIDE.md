# Guía de Personalización QWeb — Reportes Hellenia

**Fase:** 13.5 — Bloque 4  
**Plataforma:** Odoo 19  
**Módulo destino:** `hellenia_reports`  
**Fecha:** 2026-06-30

---

## 1. Objetivo

Documentar la estrategia técnica para construir formatos corporativos Justech **sin modificar core ni Enterprise**, de forma **upgrade-safe**.

---

## 2. Stack tecnológico

| Capa | Tecnología | Rol |
|------|------------|-----|
| Motor plantillas | **QWeb** (XML) | HTML de reportes |
| Layout global | **`external_layout`** | Encabezado, pie, logo |
| Formato página | **`report.paperformat`** | Tamaño, márgenes, DPI |
| Estilos | **Bootstrap 5** + **SCSS/CSS** | Clases en PDF |
| PDF | **wkhtmltopdf 0.12.6.1** | HTML → PDF |
| Assets | `web.report_assets_common` | CSS en PDF |
| Datos | Modelos Odoo estándar | `sale.order`, `account.move`, etc. |
| Fiscal RD | `justech_l10n_do_ncf` | NCF, tipo documento |

---

## 3. Anatomía de un reporte Odoo 19

```xml
<!-- 1. Acción de reporte -->
<record id="action_report_saleorder_hellenia" model="ir.actions.report">
    <field name="name">Cotización Hellenia</field>
    <field name="model">sale.order</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">hellenia_reports.report_saleorder_hellenia</field>
    <field name="paperformat_id" ref="hellenia_reports.paperformat_hellenia_letter"/>
</record>

<!-- 2. Wrapper del reporte -->
<template id="report_saleorder_hellenia">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="o">
            <t t-call="hellenia_reports.report_saleorder_document_hellenia"/>
        </t>
    </t>
</template>

<!-- 3. Documento con layout -->
<template id="report_saleorder_document_hellenia"
          inherit_id="sale.report_saleorder_document">
    <xpath expr="//div[hasclass('page')]" position="attributes">
        <attribute name="class">page hellenia-sale-order</attribute>
    </xpath>
</template>
```

---

## 4. `external_layout` — Layout corporativo

### 4.1 Layouts estándar Odoo 19

| Template key | Uso |
|--------------|-----|
| `web.external_layout_standard` | Layout por defecto |
| `web.external_layout_boxed` | Variante con caja |
| `web.external_layout_bold` | Variante bold |
| `web.external_layout_striped` | Variante striped |

### 4.2 Estrategia Hellenia

Crear `external_layout_hellenia` que herede `web.external_layout_standard`:

```xml
<template id="external_layout_hellenia" inherit_id="web.external_layout_standard">
    <!-- Reemplazar bloque header -->
    <xpath expr="//div[contains(@t-attf-class, 'header')]" position="replace">
        <div class="header hellenia-header">
            <div class="row">
                <div class="col-4">
                    <img t-if="company.logo"
                         t-att-src="image_data_uri(company.logo)"
                         class="hellenia-logo"/>
                </div>
                <div class="col-8 text-end">
                    <h2 t-field="company.name"/>
                    <div>RNC: <span t-field="company.vat"/></div>
                </div>
            </div>
        </div>
    </xpath>
</template>
```

### 4.3 Asignar layout por empresa

En `res.company`, campo `external_report_layout_id` apunta al layout activo. Configurar vía data XML o UI Configuración → Empresas.

---

## 5. `report.paperformat`

### 5.1 Definición Hellenia (propuesta)

```xml
<record id="paperformat_hellenia_letter" model="report.paperformat">
    <field name="name">Hellenia Letter</field>
    <field name="format">Letter</field>
    <field name="orientation">Portrait</field>
    <field name="margin_top">45</field>
    <field name="margin_bottom">30</field>
    <field name="margin_left">10</field>
    <field name="margin_right">10</field>
    <field name="header_spacing">40</field>
    <field name="dpi">90</field>
</record>
```

### 5.2 Asignar a reportes

```xml
<record id="sale.action_report_saleorder" model="ir.actions.report">
    <field name="paperformat_id" ref="hellenia_reports.paperformat_hellenia_letter"/>
</record>
```

> Usar `inherit_id` en el record existente o xpath en data — no duplicar acciones.

---

## 6. Assets, CSS y SCSS

### 6.1 Registrar assets PDF

```python
# __manifest__.py
'assets': {
    'web.report_assets_common': [
        'hellenia_reports/static/src/scss/hellenia_reports.scss',
    ],
},
```

### 6.2 SCSS ejemplo

```scss
.hellenia-header {
    border-bottom: 2px solid #1a365d;
    padding-bottom: 8px;
    margin-bottom: 16px;
}

.hellenia-logo {
    max-height: 60px;
}

.hellenia-invoice .table thead {
    background-color: #1a365d;
    color: #fff;
}

.page {
    font-family: 'DejaVu Sans', sans-serif;
}
```

### 6.3 Bootstrap en PDF

Odoo 19 incluye Bootstrap en reportes. Usar clases estándar:

- `row`, `col-*` — grid
- `table`, `table-sm`, `table-bordered` — tablas
- `text-end`, `fw-bold` — alineación y peso

**Limitación wkhtmltopdf:** no soporta CSS moderno (flex avanzado, grid CSS). Preferir tablas y floats para layouts complejos.

---

## 7. Imágenes

| Tipo | Método QWeb |
|------|-------------|
| Logo empresa | `image_data_uri(company.logo)` |
| Imagen producto | `image_data_uri(line.product_id.image_128)` |
| Imagen estática módulo | `/hellenia_reports/static/img/sello.png` |
| Firma | Campo binario en `res.company` (futuro) |
| Marca de agua | CSS background o `<img>` absoluto opacity |

```xml
<img t-if="company.logo"
     t-att-src="image_data_uri(company.logo)"
     style="max-height: 80px;"/>
```

---

## 8. Encabezados y pies de página

wkhtmltopdf (patched qt) soporta `--header-html` y `--footer-html`. Odoo los genera automáticamente desde `external_layout`.

### Variables disponibles en header/footer

| Variable | Descripción |
|----------|-------------|
| `company` | `res.company` activa |
| `o` | Documento actual |
| Página | `[page]` / `[topage]` en span especiales Odoo |

```xml
<div class="footer hellenia-footer">
    <div class="text-center">
        <span t-field="company.report_footer"/>
        — Página <span class="page"/> de <span class="topage"/>
    </div>
</div>
```

---

## 9. Códigos QR y códigos de barras

### 9.1 Código de barras (estándar Odoo)

```xml
<div t-field="o.justech_do_ncf"
     t-options="{'widget': 'barcode', 'barcode_type': 'Code128', 'width': 300, 'height': 50}"/>
```

Requiere módulo `barcodes` (instalado en Hellenia).

### 9.2 QR (custom)

Opción A — widget Python en `hellenia_reports`:

```python
def _get_qr_code_base64(self, value):
    import qrcode
    import base64
    from io import BytesIO
    qr = qrcode.make(value)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()
```

Opción B — URL externa (no recomendado para producción).

---

## 10. Herencia vs reemplazo

| Estrategia | Cuándo usar | Upgrade-safe |
|------------|-------------|--------------|
| **Herencia xpath** | Añadir/modificar bloques | ✅ Preferido |
| **Nueva plantilla + nueva acción** | Documento totalmente distinto | ✅ Sí |
| **Reemplazar acción estándar** | Cambiar paperformat/layout global | ✅ Con cuidado |
| **Copiar XML completo del core** | Nunca | ❌ Rompe en upgrades |
| **Studio** | Prototipo rápido | ❌ No versionable en Git |

### Reemplazar formato estándar (permitido)

```xml
<!-- Cambiar solo el report_name de la acción existente -->
<record id="account.account_invoices" model="ir.actions.report">
    <field name="report_name">hellenia_reports.report_invoice_hellenia</field>
    <field name="paperformat_id" ref="hellenia_reports.paperformat_hellenia_letter"/>
</record>
```

La plantilla hija debe seguir heredando la estándar para recibir actualizaciones de campos nuevos.

---

## 11. Patrón fiscal existente (referencia)

El módulo `justech_l10n_do_ncf` ya demuestra el patrón correcto:

```xml
<template id="report_invoice_document_justech_ncf"
          inherit_id="account.report_invoice_document">
    <xpath expr="//div[@name='reference']" position="after">
        <div class="col" t-if="o.justech_do_ncf" name="justech_ncf">
            <strong>NCF</strong>
            <div t-field="o.justech_do_ncf"/>
        </div>
    </xpath>
</template>
```

`hellenia_reports` heredará esta plantilla para estilizar, no duplicar campos fiscales.

---

## 12. Checklist desarrollo

| # | Tarea |
|---|-------|
| 1 | Crear `external_layout_hellenia` |
| 2 | Crear `paperformat_hellenia_letter` |
| 3 | Registrar SCSS en `web.report_assets_common` |
| 4 | Heredar cada `report_*_document` |
| 5 | Asignar paperformat a `ir.actions.report` |
| 6 | Probar PDF en TEST todos los documentos |
| 7 | Validar NCF, ITBIS, saltos de página |
| 8 | UAT visual con Hellenia |

---

## 13. Respuestas rápidas

| Pregunta | Respuesta |
|----------|-----------|
| ¿Formatos personalizados sin Enterprise? | **Sí** — QWeb en `custom/` |
| ¿Upgrade-safe? | **Sí** — con herencia, no copias |
| ¿Reemplazar estándar? | **Sí** — reasignar `ir.actions.report` |
| ¿Mejor herramienta? | QWeb + external_layout + SCSS |

---

## 14. Referencias

- [REPORT_ENGINE_ARCHITECTURE.md](REPORT_ENGINE_ARCHITECTURE.md)
- [BRANDING_GUIDE.md](BRANDING_GUIDE.md)
- [PDF_ENGINE_CERTIFICATION.md](PDF_ENGINE_CERTIFICATION.md)
- [Odoo QWeb Reports](https://www.odoo.com/documentation/19.0/developer/reference/backend/reports.html)
