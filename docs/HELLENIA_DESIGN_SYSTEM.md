# Hellenia Design System — Documentos PDF

**Fase:** 23 — Identidad visual corporativa  
**Módulo:** `hellenia_reports` v19.0.1.1.0  
**Fecha:** 2026-06-29

---

## 1. Propósito

Sistema de diseño unificado para todos los documentos PDF del ERP Hellenia. Solo afecta presentación (QWeb, SCSS, layouts). No modifica lógica contable, fiscal ni de negocio.

---

## 2. Paleta de color

| Token | HEX | Uso |
|-------|-----|-----|
| `--hellenia-primary` | `#3E4827` | Encabezados, títulos, bordes de acento, cabeceras de tabla |
| `--hellenia-primary-dark` | `#2d361c` | Hover / énfasis fuerte |
| `--hellenia-primary-light` | `#5a6640` | Acentos secundarios |
| `--hellenia-text` | `#2d2d2d` | Texto principal |
| `--hellenia-text-muted` | `#5c5c5c` | Texto secundario |
| `--hellenia-text-light` | `#8a8a8a` | Leyendas, metadatos |
| `--hellenia-border` | `#e5e5e5` | Separadores suaves |
| `--hellenia-row-alt` | `#f8f9f6` | Filas alternas en tablas |
| `--hellenia-surface` | `#ffffff` | Fondo de documento |

### Restricciones de marca

- Fondos siempre blancos (`#ffffff`)
- **Prohibido:** azul corporativo Odoo, dorado, colores fuera de la paleta Hellenia
- El verde `#3E4827` es el único color corporativo de acento

---

## 3. Tipografía

| Elemento | Tamaño | Peso | Notas |
|----------|--------|------|-------|
| Cuerpo documento | 9.5pt | 400 | `DejaVu Sans` |
| Nombre empresa | 13pt | 700 | Color primario |
| Título documento | 14pt | 700 | Mayúsculas, borde inferior |
| Etiquetas meta | 7.5pt | 600 | Mayúsculas, tracking amplio |
| Valores meta | 9.5pt | 500 | — |
| NCF | 13pt | 700 | `DejaVu Sans Mono` |
| Pie de página | 7.5pt | 400 | Gris muted |
| Leyenda fiscal | 7.5pt | 400 italic | Bajo el NCF |

---

## 4. Espaciado y márgenes

### Paperformat `Hellenia Carta`

| Parámetro | Valor |
|-----------|-------|
| Formato | Carta (Letter) |
| Orientación | Vertical |
| Margen superior | 40 mm |
| Margen inferior | 25 mm |
| Margen izquierdo | 10 mm |
| Margen derecho | 10 mm |
| Header spacing | 35 mm |
| DPI | 96 |

### Espaciado interno

- Separación header → contenido: 14px
- Separación entre bloques meta: 18px
- Padding tablas: 7–8px celdas
- Separación términos comerciales: 20px superior

---

## 5. Componentes

### 5.1 `external_layout_hellenia`

Layout global para todos los documentos comerciales. Incluye:

- Logo (max 68px alto)
- Bloque empresa (nombre, dirección, RNC, teléfono, correo, web)
- Línea de acento verde
- Título de documento (`hellenia-doc-title`)
- Pie con aviso legal, redes sociales y paginación `Página X / Y`

### 5.2 `hellenia-ncf-box`

Bloque fiscal para facturas, NC y ND:

- Borde izquierdo 4px verde
- Etiqueta: **Número de Comprobante Fiscal**
- Valor en monospace
- Leyenda DGII discreta debajo

### 5.3 `hellenia-lines-table`

Tabla estándar de líneas (cotización, factura, OC, entrega):

- Cabecera fondo `#3E4827`, texto blanco
- Filas alternas `#f8f9f6`
- Borde inferior suave entre filas

### 5.4 `hellenia-delivery-banner`

Banner logístico para delivery slip:

- Fondo verde corporativo, texto blanco
- Tipo de documento + referencia destacada

### 5.5 `hellenia-commercial-terms`

Bloque de condiciones comerciales en cotizaciones:

- Borde superior 3px verde
- Validez, condiciones de pago, ejecutivo comercial

### 5.6 `hellenia-payment-*`

Componentes del recibo de pago:

- Bloque cliente/proveedor
- Grid de metadatos (fecha, método, banco, referencia, factura, NCF)
- Resumen de aplicación y retenciones
- Auditoría (usuario, fecha/hora)

---

## 6. Archivos fuente

| Archivo | Rol |
|---------|-----|
| `static/src/scss/hellenia_reports.scss` | Variables CSS y estilos globales |
| `report/layout_templates.xml` | Layout corporativo y bloques footer |
| `report/report_*.xml` | Herencias QWeb por tipo de documento |
| `data/paperformat_data.xml` | Formato de página |
| `data/report_actions_data.xml` | Paperformat en acciones de reporte |

---

## 7. Clases por documento

| Clase contenedora | Documento |
|-------------------|-----------|
| `hellenia-sale-doc` | Cotización / pedido |
| `hellenia-invoice-doc` | Factura / NC / ND |
| `hellenia-purchase-doc` | OC / RFQ |
| `hellenia-stock-doc` | Entrega / recepción |
| `hellenia-payment-doc` | Recibo de pago |
| `hellenia-statement-doc` | Estados de cuenta |

---

## 8. Motor PDF

- **wkhtmltopdf** 0.12.6.1 (bundled Odoo)
- Assets: `web.report_assets_common` + `account_reports.assets_pdf_export`
- Layout empresa: `external_layout_hellenia` (configurado en compañía principal)
