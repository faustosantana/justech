# Fase 23.3C — Rediseño template cotización Hellenia

**Fecha:** 2026-07-01  
**Entorno:** `hellenia_test` — `test.hellenia.cloud`  
**Módulo:** `hellenia_reports` **19.0.1.3.2**  
**Resultado:** **TEST PASS**

---

## Causa exacta del FAIL visual

| Síntoma | Causa raíz |
|---------|------------|
| `CotizaciÃ³n`, `RepÃºblica` | El template usaba `div.page` **sin** clase `article` → Odoo no envolvía el body en `web.minimal_layout` → wkhtmltopdf recibía HTML fragmentado **sin** `<meta charset="utf-8">` |
| `$Â 1,000.00` | NBSP (`\xa0`) del widget monetario mal interpretado por el mismo fallo de charset |
| Logo gigante / layout roto (23.3) | CSS no soportado: flex, `var()`, `object-fit`, Bootstrap grid |
| Emojis rotos | Caracteres/iconos no soportados en wkhtmltopdf 0.12.6 |

El HTML QWeb era UTF-8 correcto; el fallo ocurría al convertir a PDF.

---

## Solución aplicada (v19.0.1.3.2)

1. **Reescritura total** `report_sale_quotation.xml` — layout 100% tablas, color `#3E4827`, logo `max-height: 90px` inline, sin emojis/SVG/flex
2. **Wrapper `article`** con `data-oe-model/id/lang` para que Odoo use `minimal_layout` (charset + assets PDF)
3. **`models/ir_actions_report.py`** — añade `--encoding utf-8` a wkhtmltopdf
4. Validación ampliada: texto extraído del PDF con `pdftotext` + portal HTTP 200

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `custom/hellenia_reports/report/report_sale_quotation.xml` | Template table-based + wrapper article |
| `custom/hellenia_reports/models/ir_actions_report.py` | Fuerza UTF-8 en wkhtmltopdf |
| `custom/hellenia_reports/models/__init__.py` | Import |
| `custom/hellenia_reports/__manifest__.py` | v19.0.1.3.2 |
| `scripts/phase23-3c-quotation-redesign-test.py` | Validación PDF texto + screenshot |
| `scripts/run-phase23-3c-test.sh` | exec + poppler-utils |

---

## Validación real (TEST)

| Prueba | Resultado |
|--------|-----------|
| Portal PDF orden 135 | **HTTP 200** |
| PDF sin mojibake (`COTIZACIÓN`, `República`) | **PASS** |
| PDF sin `$Â` | **PASS** |
| Logo max 90px, color #3E4827 | **PASS** |
| PDF 1 / 5 / 15 productos | **PASS** |
| Screenshot visual | `evidence/phase23-3c-quotation-redesign/screenshot_portal_page1.png` |

---

## Promoción PROD

**No** — pendiente aprobación explícita.
