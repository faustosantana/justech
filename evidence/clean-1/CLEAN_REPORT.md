# CLEAN-1 — Limpieza definitiva PRE GO-LIVE

**Fecha:** 2026-07-07T14:32:45Z  
**Base de datos:** hellenia_prod  
**Instancia:** https://odoo.hellenia.cloud  
**Resultado global:** **PASS**

## Resumen eliminación (estado inicial → final)

| Área | Antes | Después |
|------|-------|---------|
| Asientos publicados | 39 | 0 |
| Asientos totales | 39 | 0 |
| Pagos | 6 | 0 |
| Pedidos venta | 10 | 0 |
| Órdenes compra | 6 | 0 |
| Extractos banco | 3 | 0 |
| Reportes fiscales DGII | 37 | 0 |
| Consumos NCF | 33 | 0 |
| Pickings inventario | 10 | 0 |
| Conduces | 8 | 0 |
| Logs auditoría prueba | 18 | 0 |
| Mensajes chatter operativos | ~140 | 0 |

## Registros eliminados por categoría

- **fiscal_reports:** 37
- **delivery_notes:** 8
- **account_payments:** 6
- **bank_statements:** 3
- **account_moves:** 39 (facturas venta/compra, NC, pagos contables, extractos)
- **sale_orders:** 10
- **purchase_orders:** 6
- **stock_pickings:** 10 (purge SQL — transferencias done)
- **ncf_consumptions:** 33
- **audit_logs_test:** 18 (vía `justech_retention_purge`)
- **mail_messages_test:** 32
- **account.partial.reconcile / full.reconcile:** conciliaciones residuales

## Conservado (sin cambios)

- **partners:** 27 (clientes, proveedores, contactos — incl. maestros certificación)
- **products:** 8
- **accounts (COA Justech):** 292
- **journals:** 10
- **taxes:** 37
- **ncf_ranges:** 11 (configuración intacta)
- **ncf_types:** 11 (B01–B17)
- **users_active:** 2
- **audit_rules:** 3 (config auditoría)
- **governance_roles:** 9
- **governance_permissions:** 17
- **modules_justech:** 7 instalados
- Empresa, licencias, Centro Justech, plantillas PDF, secuencias config

## Reinicio secuencias NCF

Todos los rangos activos reiniciados a `sequence_start` (consumos eliminados):

| Rango | Prefijo | next → reset |
|-------|---------|--------------|
| COA3 B01 | B01 | 9708 → 9701 |
| SMOKE P13.4 B02 | B02 | 9910 → 9900 |
| FISCALRD B03 | B03 | 8921 → 8920 |
| COA3 B04 | B04 | 9708 → 9704 |
| FISCALRD B11 | B11 | 9302 → 9300 |
| FISCALRD B12 | B12 | 8981 → 8980 |
| FISCALRD B13 | B13 | 9401 → 9400 |
| COA3 B14 | B14 | 9713 → 9709 |
| FISCALRD B15 | B15 | 9101 → 9100 |
| FISCALRD B16 | B16 | 9161 → 9160 |
| FISCALRD B17 | B17 | 9501 → 9500 |

Secuencias documentales (`sale.order`, `purchase.order`, `account.payment`, etc.) verificadas en `number_next = 1`.

## Validación post-limpieza

| Check | Resultado |
|-------|-----------|
| Healthcheck PROD | PASS |
| NCF B01–B17 | PASS (11 tipos, 11 rangos activos) |
| DGII 606/607/608/609/623 | PASS (periodo vacío) |
| Balance General | Vacío (0 líneas posted) |
| Estado de Resultados | Vacío |
| Mayor | Vacío |
| Sin asientos | PASS |
| Sin facturas/compras/pagos | PASS |

## Backup

Ver `backup.md` — `/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-1-2026-07-07_103112`

## ¿Listo para operación real?

**Sí** — datos operativos de prueba eliminados, configuración fiscal/contable/maestros intacta, validaciones PASS.
