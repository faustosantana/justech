# Fase 26C — Conduce de Entrega oficial en PRODUCCIÓN

**Estado:** PASS  
**Módulo:** `justech_report_design` **19.0.5.2.0**  
**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_192648` (8 585 486 bytes)

## Cambio principal

`stock.action_report_delivery` → diseño Justech (`report_justech_delivery_document`).

- Menú **Imprimir → Conduce de Entrega** en entregas salientes (`outgoing`)
- Cotización/OV: **Imprimir → Conduce de Entrega** (`action_report_justech_delivery_sale`)
- Factura: **Imprimir → Conduce de Entrega** (`action_report_justech_delivery_invoice`)
- Recepciones/internos: **Recibo de entrega** (respaldo estándar `stock.report_deliveryslip`)

## Rollback

1. Restaurar backup indicado en `backup_path.txt`
2. Revertir `justech_report_design` a 19.0.5.1.0
3. `odoo -u justech_report_design` en PROD
