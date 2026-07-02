# Fase 24.2A — Diagnóstico y corrección TEST vs PROD

## 1. Por qué el encabezado se veía diferente en PROD

**Causa:** El bundle PDF `web.report_assets_common` incluye **hellenia_reports** y **justech_report_design**. Reglas de borde de `hellenia_reports.scss` (p. ej. `.hellenia-partner-block`, bloques con `border-left`) pueden aplicarse en el mismo contexto wkhtmltopdf. En PROD, la compilación/caché de assets y el orden de carga hacían visible una línea/borde entre columnas del encabezado que en TEST no se percibía igual.

**Corrección:**
- `border="0"` explícito en tabla `jt-hq-hdr`
- Reglas SCSS reforzadas: sin bordes en celdas del encabezado
- Aislamiento `.jt-hq-page` contra clases `hellenia-*`
- Upgrade módulo v`19.0.2.0.1` para regenerar assets

## 2. Por qué las condiciones no aparecían

| Problema | Causa |
|----------|--------|
| PDF sin CONDICIONES | `sale.order.note` vacío en cotizaciones existentes (p. ej. S00020 creada antes de 24.2) |
| Formulario vacío | `default_get` solo precargaba `note` si `"note" in fields_list` — Odoo a menudo llama `default_get` sin ese campo |
| Empresa sin datos (24.1) | `hellenia_quotation_terms` vacío en PROD (corregido en despliegue 24.2) |

**Corrección:**
- `default_get` siempre precarga `note` desde `company.hellenia_quotation_terms`
- Vista con sección visible **Términos y Condiciones**
- `jt_backfill_empty_quotation_notes()` para borradores/enviadas sin `note`
- PDF imprime solo `doc.note` (sin texto en XML)

## 3. Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `models/sale_order.py` | Fix `default_get`, backfill borradores |
| `views/sale_order_views.xml` | Sección Términos y Condiciones visible + config empresa |
| `report/quotation/hellenia_quotation_template.xml` | `border="0"` en encabezado |
| `static/src/scss/hellenia_quotation.scss` | Aislamiento bordes encabezado / hellenia |
| `__manifest__.py` | v19.0.2.0.1 |

## 4. Rollback

Ver `docs/PHASE24_2_OFFICIAL_QUOTATION_ROLLBACK.md` — revierte acción de reporte en < 2 min sin tocar `note`.

Para revertir solo este patch: checkout módulo v`19.0.2.0.0` y `-u justech_report_design`.
