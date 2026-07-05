# Fase 24.2B — Ajuste final diseño (sin rediseño)

## Por qué aparecían los bordes en el encabezado

wkhtmltopdf dibuja bordes implícitos en celdas `<table>/<td>` aunque CSS declare `border: none`. El encabezado usaba una tabla de dos columnas (logo | empresa); eso generaba líneas finas entre columnas y en el perímetro del bloque, visibles en PROD al compilar el bundle PDF con `hellenia_reports` + `justech_report_design`.

## Cambios realizados (únicamente lo solicitado)

| # | Ajuste | Archivo |
|---|--------|---------|
| 1 | Encabezado: `<table>` → `<div>` con `display: table` / `table-cell` | `hellenia_quotation_template.xml`, `hellenia_quotation.scss` |
| 2 | Títulos «Información del Cliente/Vendedor»: clase `jt-hq-card-title` 7.5pt (antes 6.5pt vía `jt-hq-title`) | mismos archivos |

**No modificado:** condiciones, totales, firmas, tabla productos, colores, footer, lógica, espaciados generales.

Versión módulo: **19.0.2.0.2**
