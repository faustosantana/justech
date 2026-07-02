# Fase 26B — Conduce de Entrega en PRODUCCIÓN

**Estado:** PASS  
**Módulo:** `justech_report_design` **19.0.5.1.0**  
**Base de datos:** `hellenia_prod`  
**URL:** https://odoo.hellenia.cloud  

## Backup previo (obligatorio)

```
/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_191647/
```

Contenido: `postgres_all.sql.gz`, `filestore.tar.gz`, `custom.tar.gz`, `docker-compose.yml`, `.env`, `odoo.conf`, `MANIFEST.txt`

## Evidencia

| Archivo | Origen |
|---------|--------|
| `01_from_picking.pdf` / `.png` | `stock.picking` WH/OUT/00008 |
| `02_from_sale_order.pdf` / `.png` | `sale.order` S00010 |
| `03_from_invoice.pdf` / `.png` | `account.move` INV/2026/00006 |
| `validation.json` | Validación automatizada + host pdftotext |

## Criterios 26B verificados

- Banda verde dos columnas (No. Conduce / OV / Factura | Estado / Fecha / Almacén)
- Responsable y Vendedor separados (sin `— / OdooBot`)
- Almacén: código `WH` (no nombre de empresa)
- OBSERVACIONES siempre visible
- Leyenda legal discreta
- Sin precios, ITBIS ni totales
- Cant. Ent. en negrita (plantilla)

## Rollback

Ver `evidence/phase26-delivery-slip/Rollback.md` — restaurar backup anterior y `odoo -u justech_report_design` con versión previa.
