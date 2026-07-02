# Certificación Motor PDF — Hellenia PROD

**Fase:** 13.5 — Motor de reportes, PDF y formatos comerciales  
**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_prod` — https://odoo.hellenia.cloud  
**VPS:** `srv.hellenia.cloud` (`2.25.69.179`)  
**Fecha certificación:** 2026-06-30  
**Estado:** **PASS** — infraestructura lista para documentos corporativos

---

## 1. Resumen ejecutivo

Se certificó el motor de generación PDF en producción sin modificar core, Enterprise ni `odoo-pecv`. El contenedor Odoo 19 incluye **wkhtmltopdf 0.12.6.1 (with patched qt)**, versión recomendada oficialmente para Odoo 19. Todos los documentos comerciales estándar probados generan PDF válido (> 59 KB).

| Pregunta | Respuesta |
|----------|-----------|
| ¿VPS listo para PDFs? | **Sí** |
| ¿wkhtmltopdf correctamente instalado? | **Sí** |
| ¿Versión recomendada Odoo? | **Sí** — 0.12.6.1 patched qt |
| ¿Formatos personalizados sin Enterprise? | **Sí** — vía módulos custom QWeb |
| ¿Plataforma certificada nivel empresarial? | **PASS** — motor OK; diseños corporativos pendientes |

**Evidencia:** `evidence/phase13-5-pdf-certification-prod.json`  
**Script:** `scripts/phase13-5-certify-pdf-engine.py` / `scripts/run-phase13-5-pdf-certification.sh`

---

## 2. Bloque 1 — Motor PDF

### 2.1 Componente wkhtmltopdf

| Parámetro | Valor certificado |
|-----------|-------------------|
| **Versión** | `wkhtmltopdf 0.12.6.1 (with patched qt)` |
| **Ubicación** | `/usr/local/bin/wkhtmltopdf` |
| **wkhtmltoimage** | `/usr/local/bin/wkhtmltoimage` |
| **Contenedor** | `hellenia-prod-odoo-1` (imagen `odoo:19.0-20260619`) |
| **Recomendación Odoo 19** | ✅ Coincide — Odoo documenta 0.12.6.1-3 patched Qt para 16–19 |

> **Nota:** wkhtmltopdf vive **dentro del contenedor Docker**, no en el host VPS. Esto es correcto: Odoo invoca el binario del mismo entorno donde corre el servicio.

### 2.2 Dependencias y soporte

| Capacidad | Estado | Detalle |
|-----------|--------|---------|
| UTF-8 | ✅ PASS | CLI test → PDF 8 870 bytes con acentos (`ñ á é í ó ú`) |
| Español (es_DO) | ✅ PASS | Locale UI y contenido QWeb en español |
| Fuentes | ✅ Instaladas | DejaVu Sans/Serif/Mono, Roboto, URW Base35, Noto CJK |
| Imágenes PNG | ✅ PASS | Embebidas en HTML → PDF |
| Logos SVG/PNG | ✅ Soportado | vía `<img>` en QWeb; logo empresa en `res.company.logo` |
| Códigos QR | ✅ PASS | Paquete Python `qrcode` disponible en contenedor |
| Códigos de barras | ✅ PASS | Módulo Odoo `barcodes` instalado; widget estándar QWeb |
| Encabezados / pies | ✅ Soportado | Requiere patched qt (presente) + `external_layout` Odoo |
| `python-barcode` | ⚠️ No instalado | No requerido — Odoo usa `barcodes` + reportlab internamente |

### 2.3 Parámetros Odoo relevantes

| Parámetro | Valor PROD |
|-----------|------------|
| `web.base.url` | `https://odoo.hellenia.cloud` |
| `report.url` | `https://odoo.hellenia.cloud` |

`report.url` debe coincidir con `web.base.url` para que wkhtmltopdf resuelva assets CSS/imágenes al renderizar. Configurado y verificado en esta fase.

### 2.4 Parámetros wkhtmltopdf (uso Odoo)

Odoo invoca wkhtmltopdf internamente con opciones como:

| Parámetro | Uso |
|-----------|-----|
| `--quiet` | Suprime salida verbose |
| `--encoding UTF-8` | Caracteres españoles |
| `--page-size` | Desde `report.paperformat` (A4 / Letter) |
| `--margin-top/bottom/left/right` | Desde `report.paperformat` |
| `--dpi` | 90 (estándar Odoo) |
| `--header-html` / `--footer-html` | Encabezado/pie corporativo |
| `--disable-local-file-access` | Seguridad (Odoo 19 default) |

### 2.5 Smoke test documentos comerciales

Ejecutado vía `ir.actions.report._render_qweb_pdf` en `hellenia_prod`:

| Documento | XML ID | Bytes | Estado |
|-----------|--------|-------|--------|
| Cotización | `sale.report_saleorder` | 62 949 | ✅ PASS |
| Pedido de venta | `sale.report_saleorder` | 63 103 | ✅ PASS |
| Factura cliente | `account.account_invoices` | 60 699 | ✅ PASS |
| Nota de crédito | `account.account_invoices` | 59 993 | ✅ PASS |
| RFQ compra | `purchase.report_purchasequotation` | 61 489 | ✅ PASS |
| Orden de compra | `purchase.report_purchaseorder` | 64 779 | ✅ PASS |

**NCF generado en prueba:** `B0200009903` (rango certificación PDF).

### 2.6 Observaciones conocidas

| Observación | Impacto | Mitigación |
|-------------|---------|------------|
| `ContentNotFoundError` ocasional en logs al cargar assets externos | Bajo — PDF se genera | `report.url` configurado; usar URLs absolutas en QWeb custom |
| Diseños actuales = plantillas estándar Odoo | Estético | Fase siguiente: `hellenia_reports` |
| Logo empresa no configurado en `res.company` | Branding pendiente | Configurar antes de desarrollo corporativo |

---

## 3. Bloque 2 — Impresión

### 3.1 Canales de salida

| Canal | Estado | Notas |
|-------|--------|-------|
| Impresión navegador | ✅ | Botón Imprimir → vista HTML QWeb |
| Descarga PDF | ✅ | Botón Imprimir → PDF vía wkhtmltopdf |
| Envío por email | ✅ | Adjunto PDF estándar Odoo |

### 3.2 Formatos de papel (`report.paperformat`)

| Formato | Página | Márgenes (mm) | DPI | Uso Hellenia |
|---------|--------|---------------|-----|--------------|
| **A4** | A4 | top 52, bottom 32 | 90 | Documentos internacionales / proveedores |
| **US Letter** | Letter | top 52, bottom 32 | 90 | **Recomendado RD** — carta dominicana |
| Dominican Republic Check Letter | Letter | 0 | 90 | Cheques |
| A4 - statement | A4 | top 52, bottom 32 | 90 | Estados de cuenta |

**Decisión Hellenia:** usar **US Letter** como formato principal para documentos comerciales RD (carta 8.5" × 11").

### 3.3 Elementos de layout verificados

| Elemento | Estado estándar Odoo |
|----------|---------------------|
| Márgenes configurables | ✅ `report.paperformat` |
| Saltos de página | ✅ CSS `page-break-before/after` |
| Fuentes | ✅ Bootstrap + DejaVu en PDF |
| Tablas largas | ✅ Paginación automática wkhtmltopdf |
| Imágenes producto | ✅ Soportado en líneas |
| Logotipo empresa | ✅ `res.company.logo` en `external_layout` |

---

## 4. Bloque 7 — Certificación final

### 4.1 Checklist

| # | Ítem | Resultado |
|---|------|-----------|
| 1 | wkhtmltopdf instalado en contenedor PROD | ✅ |
| 2 | Versión patched qt compatible Odoo 19 | ✅ |
| 3 | UTF-8 y español | ✅ |
| 4 | Fuentes suficientes | ✅ |
| 5 | QR y códigos de barras | ✅ |
| 6 | PDF cotización / pedido / factura / NC / OC | ✅ |
| 7 | `report.url` configurado | ✅ |
| 8 | Sin modificar core / Enterprise / odoo-pecv | ✅ |

### 4.2 Respuestas oficiales (8 preguntas)

1. **¿El VPS está listo para generar PDFs?** — **Sí.**
2. **¿wkhtmltopdf está correctamente instalado?** — **Sí**, en el contenedor Odoo PROD.
3. **¿Qué versión tiene?** — **0.12.6.1 (with patched qt)**.
4. **¿Es la recomendada por Odoo?** — **Sí** (0.12.6.1-3 patched Qt para Odoo 16–19).
5. **¿Podemos construir formatos completamente personalizados?** — **Sí**, en `custom/hellenia_reports` con QWeb inherit.
6. **¿Podemos reemplazar completamente los formatos estándar?** — **Sí**, reasignando `ir.actions.report` o heredando plantillas; sin tocar Enterprise.
7. **¿Estrategia upgrade-safe?** — Módulo `hellenia_reports` con herencia QWeb (`inherit_id`), nunca copiar XML de core/EE. Ver `REPORT_ENGINE_ARCHITECTURE.md`.
8. **¿Plataforma certificada para documentos corporativos?** — **Sí (infraestructura)**. Diseños Justech pendientes de implementación en fase siguiente.

### 4.3 Próximos pasos (fuera de alcance 13.5)

- Instalar y activar `hellenia_reports` en TEST
- Diseñar `external_layout_hellenia` corporativo
- Configurar logo, RNC y datos legales en `res.company`
- Desarrollar plantillas por documento según `COMMERCIAL_DOCUMENTS_SPEC.md`

---

## 5. Referencias

| Documento | Contenido |
|-----------|-----------|
| [REPORT_ENGINE_ARCHITECTURE.md](REPORT_ENGINE_ARCHITECTURE.md) | Arquitectura reportes Justech |
| [COMMERCIAL_DOCUMENTS_SPEC.md](COMMERCIAL_DOCUMENTS_SPEC.md) | Especificación por documento |
| [QWEB_CUSTOMIZATION_GUIDE.md](QWEB_CUSTOMIZATION_GUIDE.md) | Guía técnica QWeb |
| [BRANDING_GUIDE.md](BRANDING_GUIDE.md) | Branding configurable |
