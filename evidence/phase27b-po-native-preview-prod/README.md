# Fase 27B — Evidencia vista previa nativa OC

## TEST — PASS

- Módulo: `justech_report_design` 19.0.7.3.1
- PO: P00054 (id 56)
- Validación automática: `validation.json` → PASS
- Capturas UI: `01_form_with_preview_button.png`, `02_portal_preview_page.png`
- Sin `/report/html/` directo; preview portal con iframe Hellenia

## PROD — PASS

- Backup: `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_212348`
- Módulo: `justech_report_design` 19.0.7.3.1
- PO: P00008 (id 9)
- Validación automática: `validation.json` → PASS
- Capturas UI: `01_form_with_preview_button.png`, `02_portal_preview_page.png`
- Sin QWebError / RPCError / OWLError

## Flujo validado

1. Botón **Vista previa** visible en header `purchase.order`
2. Abre `/my/purchase/{id}/preview` (misma pestaña)
3. Sidebar: Descargar + Imprimir
4. Banner: volver a edición
5. Iframe: diseño Hellenia (`jt-po-band`)
6. Menú Imprimir → Orden de Compra sigue OK
