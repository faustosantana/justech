# Fase 26D — Botón y contador Conduce en cotización y factura

**Estado:** PASS  
**Módulo:** `justech_report_design` **19.0.5.3.0**  
**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_193903` (8 609 483 bytes)

## UI

- Header: botón **Conduce de Entrega** (cotización/OV y factura cliente)
- Smart button: contador **Conduce / Conduces** con entregas salientes relacionadas
- Chatter: registro al imprimir (usuario, fecha, documento, entregas)

## Evidencia

- `validation.json` — validación funcional PROD
- `01_from_sale_button.pdf` / `.png` — PDF desde botón OV
- `02_from_invoice_button.pdf` / `.png` — PDF desde botón factura
- `view_arch_snippet.txt` — presencia de botones en vistas
