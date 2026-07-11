# BEFORE / AFTER — BUGFIX-QUOTATION-TERMS-1

## Before

- Vista previa / PDF de cotización → Error 500
- `AttributeError: jt_quotation_note_for_report`
- Workers HTTP sin Python actualizado tras `-u`
- TEST en `justech_report_design` 19.0.7.4.0 / `hellenia_reports` 19.0.1.5.7

## After

- Método + campo computado en `sale.order`
- Plantilla usa `t-out="doc.jt_quotation_note_html"`
- TEST/PROD: `hellenia_reports` 19.0.1.5.9, `justech_report_design` 19.0.7.4.2
- Contenedores Odoo recreados (`force-recreate`)
- Vista previa HTML OK, PDF OK, sin `&lt;br/&gt;`
- Cotizaciones antiguas conservan `note`
- Cotizaciones nuevas cargan términos desde configuración
- Cotización sin términos no rompe el PDF
- Healthcheck PROD: PASS

## Archivos clave

- `custom/justech_report_design/models/sale_order.py`
- `custom/justech_report_design/report/quotation/hellenia_quotation_template.xml`
- `custom/hellenia_reports/models/res_company.py` (texto base términos)
