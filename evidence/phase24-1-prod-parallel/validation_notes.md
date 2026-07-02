# Fase 24.1 PROD — Ejecución paralela `justech_report_design`

**Fecha:** 2026-07-02  
**Autorización:** Plan PROD paralelo 24.1  
**Resultado global:** **PASS** (con nota sobre cotización 5+ líneas)

## Backup pre-instalación

| Componente | Estado |
|------------|--------|
| PostgreSQL (`postgres_all.sql.gz`) | OK |
| Filestore (`filestore.tar.gz`) | OK |
| `custom/` (`custom.tar.gz`) | OK |
| `docker-compose.yml` | OK |
| `.env` + `odoo.conf` | OK |
| **Timestamp** | `2026-07-02_0425` |
| **Ruta** | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_0425` |

## Instalación

| Paso | Resultado |
|------|-----------|
| Copia `custom/justech_report_design/` v19.0.1.1.6 | OK |
| `-i justech_report_design` en `hellenia_prod` | OK |
| Reinicio `hellenia-prod-odoo-1` | OK |
| Módulos cargados | 139 (138 + justech_report_design) |

### Incidencia preexistente (resuelta sin rollback)

La primera instalación falló por columna faltante `res_company.hellenia_quotation_terms` (código `hellenia_reports` en disco vs BD en v19.0.1.1.0). Se añadieron columnas de esquema ya definidas en código desplegado:

- `hellenia_quotation_terms` (text)
- `hellenia_signature_image` (bytea)
- `hellenia_stamp_image` (bytea)

**No** se ejecutó `-u hellenia_reports`. **No** se modificó `sale.action_report_saleorder`. Rollback **no** fue necesario.

## Validaciones

| # | Criterio | Resultado | Detalle |
|---|----------|-----------|---------|
| 1 | Módulo instalado v19.0.1.1.6 | **PASS** | `ir_module_module` |
| 2 | Menú **Cotización Hellenia (Diseño)** | **PASS** | Binding `sale.order` |
| 3 | Menú **Cotización en PDF** (estándar) | **PASS** | `sale.action_report_saleorder` intacto |
| 4 | PDF diseño — cotización real | **PASS** | S00020, 73 572 bytes |
| 5 | PDF estándar — misma cotización | **PASS** | S00020, 60 440 bytes |
| 6 | PDF con descuento | **PASS** | 10% temporal en S00020; columna DESC. + totales bruto/descuento; descuento revertido |
| 7 | Cotización 5+ productos | **N/A** | PROD no tiene cotización con 5+ líneas (máx. 1 línea en S00020) |
| 8 | VIS-001 (sin borde condiciones/firmas) | **PASS** | Sin `jt-hq-lower`, sin `<table class="jt-hq-sigs-zone"` |
| 9 | Sin herencia sobre estándar | **PASS** | `jt_inherits=0` en los 3 reportes sale |
| 10 | `hellenia_reports` activo | **PASS** | installed 19.0.1.1.0 |
| 11 | Factura PDF | **PASS** | INV/2026/00006 |
| 12 | Compra PDF | **PASS** | P00008 |
| 13 | Inventario PDF | **PASS** | WH/OUT/00006 (state=assigned) |
| 14 | DGII | **PASS** | `justech_l10n_do_ncf` installed; 20 registros fiscales |
| 15 | Logs sin QWebException nueva | **PASS** | install.log + post-install limpios |

## Restricciones respetadas

- NO reemplazo de reporte estándar
- NO modificación de `sale.action_report_saleorder`
- NO eliminación de `hellenia_reports`
- NO conversión a formato oficial

## Evidencia

Ver PDFs y capturas en este directorio. Logs: `install.log`, `validation-run.log`.
