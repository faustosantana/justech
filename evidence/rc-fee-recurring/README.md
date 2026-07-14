# Evidencia — Fee recurrente Justech (maestro)

**Entorno:** DEV `erp.justech.do` / BD `justech_dev`  
**Fecha:** 2026-07-14  
**Módulo:** `justech_recurring_fee` **19.0.1.0.1**  
**Backup previo RC6.2:** `/opt/odoo-dev/backups/rc62-pre-20260713_222240/` (sin tocar Producción)

## Decisión de arquitectura

| Elemento | Decisión |
|---|---|
| Registro maestro | `justech.recurring.fee` (Fee recurrente) |
| Suscripciones Odoo | Reuso opcional de `sale.subscription.plan` para periodicidad |
| Flujo UI | **No** obligar Cotización → Suscripción |
| Generación default | Cotización en borrador |
| Fiscal | NCF solo al publicar factura vía Motor Fiscal Justech |

## Flujo operativo

Fee → próxima fecha → cron → cotización/factura → revisión → confirmación → factura → Motor Fiscal / NCF → pago → próxima recurrencia.

## Validación ORM (DEV)

Scripts: `/tmp/rc_fee_validate_v2.py`, `/tmp/rc_fee_idem.py`  
Transacciones de prueba: **rollback** (sin contaminar datos).

| Caso | Resultado |
|---|---|
| 1 Fee mensual sin cotización previa → cotización vinculada | **PASS** |
| 2 Idempotencia mismo fee+período+tipo | **PASS** (`cycles=1`, `sos=1` en reintento) |
| 2b Segundo ciclo distinto | **PASS** |
| 3 Factura borrador + post → NCF `B01…` | **PASS** |
| 4 Cambio de precio solo futuro | **PASS** |
| 5 Pausa (no genera) + reactiva wizard | **PASS** |
| 6 Multiempresa 4/4 + aislamiento company | **PASS** |
| 7 Factura borrador sin NCF hasta publicar | **PASS** |
| Menú Ventas → Fees recurrentes | **PASS** |
| `invoice_auto` (admin) → posted + NCF | **PASS** |

## Fix crítico 19.0.1.0.1

Impuestos multiempresa en líneas del fee rompían la creación del SO; la excepción se capturaba **sin savepoint**, dejando cotizaciones huérfanas y **sin ciclo** (idempotencia rota).

- Filtrar `tax_ids` por `company_id` del fee.
- Savepoint alrededor de documento + ciclo.
- Advisory lock en cron.

## Rollback

1. `-u` revert no aplica; desinstalar módulo o restaurar backup RC6.2.
2. Código: volver a commit anterior del módulo (cuando exista) o eliminar `custom/justech_recurring_fee`.
3. Datos de prueba de validación **no persistidos** (rollback).

## Criterio PASS pedido

- Fee como registro maestro: **PASS**
- Creación sin cotización previa: **PASS**
- Generación automática cotización: **PASS**
- Factura borrador opcional: **PASS**
- Idempotencia por ciclo: **PASS**
- Cambios solo períodos futuros: **PASS**
- Pausa / reactivación: **PASS**
- Documentos vinculados: **PASS**
- Motor Fiscal Justech al publicar: **PASS**
- Multiempresa 4/4: **PASS**

**Commit pendiente:** no ejecutado (requiere aprobación explícita).
