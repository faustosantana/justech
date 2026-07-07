# PURCHASE-UX-1 — Solicitud de Cotización / Orden de Compra

**Módulo:** `justech_report_design` 19.0.7.4.0  
**Entorno validado:** hellenia_test  
**Resultado:** PASS

## Cambios

- Plantilla compras alineada a cotización/factura (`jt-hq-band`, `jt-hq-dates`, `jt-hq-cards`)
- Título dinámico: `SOLICITUD DE COTIZACIÓN` (draft/sent) / `ORDEN DE COMPRA` (purchase/done)
- RFQ (`purchase.report_purchase_quotation`) usa el mismo reporte corporativo Justech
- Eliminada banda antigua tipo Excel con metadatos duplicados
- Observaciones solo si hay contenido
- Paperformat Carta + A4 para validación responsive

## PDFs generados (TEST)

- draft — Letter + A4
- sent — Letter + A4
- purchase — Letter + A4

## Nota Odoo 19

El estado `done` ya no existe en `purchase.order`; órdenes confirmadas usan `purchase` (título ORDEN DE COMPRA).
