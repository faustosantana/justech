# Guía de Branding — Documentos Hellenia

**Fase:** 13.5 — Bloque 6  
**Cliente:** Hellenia, S.R.L.  
**Módulo destino:** `hellenia_reports` + `res.company`  
**Fecha:** 2026-06-30

---

## 1. Objetivo

Definir todos los elementos de marca configurables por empresa para documentos PDF comerciales, sin hardcodear valores en plantillas QWeb.

---

## 2. Elementos de branding

| Elemento | Configurable | Fuente propuesta |
|----------|--------------|------------------|
| **Logo** | Sí | `res.company.logo` (estándar Odoo) |
| **Marca de agua** | Sí | Campo nuevo `hellenia_watermark` en `res.company` |
| **Paleta de colores** | Sí | Campos color + SCSS variables |
| **Tipografías** | Parcial | SCSS (DejaVu/Roboto en contenedor) |
| **Firmas** | Sí | Campo binario `hellenia_signature_image` |
| **Sellos** | Sí | Campo binario `hellenia_stamp_image` |
| **QR** | Sí | Generado dinámico (NCF/URL verificación) |
| **Redes sociales** | Sí | Campos URL por red |
| **Información legal** | Sí | `res.company.report_footer` |
| **RNC** | Sí | `res.company.vat` |
| **NCF** | Sí | `account.move.justech_do_ncf` (fiscal) |

---

## 3. Configuración estándar Odoo (sin desarrollo)

Estos campos ya existen en `res.company` y deben configurarse en PROD antes del desarrollo visual:

| Campo UI | Campo técnico | Uso en PDF |
|----------|---------------|------------|
| Logo | `logo` | Encabezado |
| Nombre empresa | `name` | Título |
| RNC | `vat` | Encabezado fiscal |
| Dirección | `partner_id` address | Encabezado |
| Teléfono | `phone` | Contacto |
| Email | `email` | Contacto |
| Sitio web | `website` | Pie |
| Encabezado documento | `report_header` | HTML libre bajo logo |
| Pie documento | `report_footer` | HTML libre al final |
| Layout documento | `external_report_layout_id` | Selección layout |

**Acción inmediata Hellenia:** cargar logo PNG (mín. 300×100 px, fondo transparente) y completar RNC en Configuración → Empresas.

---

## 4. Campos propuestos `hellenia_reports`

Extensión de `res.company` (implementación futura):

```python
class ResCompany(models.Model):
    _inherit = "res.company"

    hellenia_primary_color = fields.Char(
        string="Color primario",
        default="#1a365d",
        help="Color corporativo principal (hex).",
    )
    hellenia_secondary_color = fields.Char(
        string="Color secundario",
        default="#c9a227",
    )
    hellenia_watermark = fields.Binary(string="Marca de agua")
    hellenia_signature_image = fields.Binary(string="Firma autorizada")
    hellenia_stamp_image = fields.Binary(string="Sello empresa")
    hellenia_social_facebook = fields.Char(string="Facebook")
    hellenia_social_instagram = fields.Char(string="Instagram")
    hellenia_social_whatsapp = fields.Char(string="WhatsApp")
    hellenia_legal_notice = fields.Html(
        string="Aviso legal documentos",
        help="Texto legal obligatorio en pie de facturas.",
    )
    hellenia_show_qr_on_invoice = fields.Boolean(
        string="Mostrar QR en factura",
        default=False,
    )
```

---

## 5. Paleta de colores propuesta

> Valores provisionales — confirmar con identidad visual Hellenia.

| Rol | Color | Hex | Uso |
|-----|-------|-----|-----|
| Primario | Azul marino | `#1a365d` | Encabezados, bordes tabla |
| Secundario | Dorado | `#c9a227` | Acentos, líneas |
| Texto | Gris oscuro | `#2d3748` | Cuerpo |
| Fondo tabla header | Primario | `#1a365d` | thead |
| Fondo zebra | Gris claro | `#f7fafc` | Filas alternas |

### Aplicación en SCSS

```scss
:root {
    --hellenia-primary: #{var(--company-primary, #1a365d)};
    --hellenia-secondary: #{var(--company-secondary, #c9a227)};
}
```

Inyectar colores vía inline style en layout desde campos `res.company`.

---

## 6. Tipografías

| Fuente | Disponibilidad PDF | Uso recomendado |
|--------|-------------------|-----------------|
| **DejaVu Sans** | ✅ Contenedor | Cuerpo, tablas |
| **DejaVu Serif** | ✅ Contenedor | Títulos formales |
| **Roboto** | ✅ Contenedor | Alternativa moderna |
| Fuentes custom | ⚠️ Requiere instalar TTF en Docker | Solo si Hellenia provee archivos |

**Recomendación:** DejaVu Sans para compatibilidad UTF-8/español sin dependencias extra.

---

## 7. Logo

| Especificación | Valor |
|----------------|-------|
| Formato | PNG (preferido) o SVG |
| Fondo | Transparente |
| Tamaño máximo render | 80px alto en encabezado |
| Resolución fuente | Mín. 300 DPI para impresión |
| Ubicación config | Configuración → Empresas → Logo |

### SVG en wkhtmltopdf

SVG soportado vía `<img src="data:image/svg+xml;base64,...">`. Odoo convierte logo binario automáticamente con `image_data_uri()`.

---

## 8. Marca de agua

```scss
.page.hellenia-watermark::before {
    content: '';
    position: fixed;
    top: 30%;
    left: 15%;
    width: 70%;
    height: 40%;
    background-image: url(/* watermark base64 */);
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.08;
    z-index: -1;
}
```

Activar solo en cotizaciones (opcional) o desactivar en facturas fiscales.

---

## 9. Firmas y sellos

```xml
<div class="hellenia-signature-block row mt-4">
    <div class="col-6 text-center">
        <img t-if="company.hellenia_signature_image"
             t-att-src="image_data_uri(company.hellenia_signature_image)"
             style="max-height: 60px;"/>
        <div class="border-top pt-1">Firma autorizada</div>
    </div>
    <div class="col-6 text-center">
        <img t-if="company.hellenia_stamp_image"
             t-att-src="image_data_uri(company.hellenia_stamp_image)"
             style="max-height: 80px;"/>
    </div>
</div>
```

---

## 10. QR y códigos de barras

| Documento | Contenido QR | Contenido barcode |
|-----------|--------------|-------------------|
| Factura | URL verificación / NCF (futuro eNCF) | NCF Code128 |
| Cotización | URL pública cotización (portal) | Número cotización |
| OC | Referencia interna | Número OC |

Configuración: `hellenia_show_qr_on_invoice` por empresa.

---

## 11. Redes sociales

Bloque pie de página:

```xml
<div class="hellenia-social text-center" t-if="company.hellenia_social_instagram">
    <span>Instagram: </span><span t-field="company.hellenia_social_instagram"/>
    <span t-if="company.hellenia_social_whatsapp"> | WhatsApp: </span>
    <span t-field="company.hellenia_social_whatsapp"/>
</div>
```

---

## 12. Información legal RD

### Factura — pie obligatorio (plantilla)

Contenido sugerido para `hellenia_legal_notice` o `report_footer`:

- Hellenia, S.R.L. — RNC [vat]
- Dirección fiscal completa
- "Esta factura es válida como comprobante fiscal según normas DGII"
- Condiciones de pago y política de devoluciones
- Cuentas bancarias para transferencias

### NCF en encabezado

Siempre visible cuando `o.justech_do_ncf` está presente (ya implementado en `justech_l10n_do_ncf`).

---

## 13. Configuración por empresa

Hellenia es mono-empresa hoy, pero la arquitectura soporta multi-compañía:

| Elemento | Scope |
|----------|-------|
| Logo, colores, firmas | `res.company` |
| Layout | `external_report_layout_id` per company |
| Paperformat | `ir.actions.report` (puede variar por company con record rules) |
| NCF / fiscal | `justech.do.ncf.range` per company |

---

## 14. Checklist branding pre-desarrollo

| # | Tarea | Responsable | Estado |
|---|-------|-------------|--------|
| 1 | Proveer logo PNG alta resolución | Hellenia | Pendiente |
| 2 | Confirmar paleta colores oficial | Hellenia | Pendiente |
| 3 | Texto legal pie de factura | Hellenia / Contador | Pendiente |
| 4 | Imagen firma autorizada | Hellenia | Pendiente |
| 5 | Imagen sello (si aplica) | Hellenia | Pendiente |
| 6 | URLs redes sociales | Hellenia | Pendiente |
| 7 | Cargar RNC en `res.company` | Admin PROD | Verificar |
| 8 | Cuentas bancarias en empresa | Admin PROD | Verificar |

---

## 15. Referencias

- [COMMERCIAL_DOCUMENTS_SPEC.md](COMMERCIAL_DOCUMENTS_SPEC.md)
- [QWEB_CUSTOMIZATION_GUIDE.md](QWEB_CUSTOMIZATION_GUIDE.md)
- [REPORT_ENGINE_ARCHITECTURE.md](REPORT_ENGINE_ARCHITECTURE.md)
- [NCF_CONFIGURATION.md](NCF_CONFIGURATION.md)
