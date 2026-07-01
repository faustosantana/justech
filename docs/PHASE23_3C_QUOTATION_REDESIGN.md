# Fase 23.3C — Rediseño cotización wkhtmltopdf-safe — TEST

**Fecha:** 2026-07-01  
**Entorno:** `hellenia_test` — `test.hellenia.cloud`  
**Módulo:** `hellenia_reports` **19.0.1.3.1**  
**Resultado:** ver `evidence/phase23-3c-quotation-redesign/validation.json`

---

## Causa exacta del FAIL visual

| Síntoma | Causa raíz |
|---------|------------|
| `CotizaciÃ³n`, `RepÃºblica` | wkhtmltopdf 0.12.6 **sin** `--encoding utf-8`; interpreta bytes UTF-8 como Latin-1 |
| `$Â 1,000.00` | NBSP (`\xa0`) del widget monetario mal decodificado |
| Logo gigante / layout roto (fase anterior) | CSS no soportado: flex, `var()`, `object-fit`, Bootstrap grid |

El HTML renderizado por QWeb era **correcto UTF-8**; el fallo ocurría solo en la conversión PDF.

---

## Solución 23.3C (v19.0.1.3.1)

1. **`models/ir_actions_report.py`** — añade `--encoding utf-8` a wkhtmltopdf
2. **`report/report_sale_quotation.xml`** — layout 100% tablas, color `#3E4827`, logo `max-height: 90px` inline, acentos UTF-8 normales, sin emojis/SVG/flex
3. Validación ampliada: **texto extraído del PDF** (no solo HTML)

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `custom/hellenia_reports/models/ir_actions_report.py` | Nuevo — fuerza UTF-8 en wkhtmltopdf |
| `custom/hellenia_reports/models/__init__.py` | Import |
| `custom/hellenia_reports/report/report_sale_quotation.xml` | Template table-based + UTF-8 |
| `custom/hellenia_reports/__manifest__.py` | v19.0.1.3.1 |
| `scripts/phase23-3c-quotation-redesign-test.py` | Validación PDF texto + screenshot |

---

## Promoción PROD

**No** — pendiente aprobación explícita.
