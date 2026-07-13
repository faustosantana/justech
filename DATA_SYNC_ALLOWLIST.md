# DATA SYNC ALLOWLIST — modelos operativos autorizados

Procedimiento seguro para refrescar **solo datos operativos** desde Producción
hacia `justech_dev` (o cualquier clon DEV).

## Regla de oro

1. Backup completo + restore-test de DESTINO **antes** de cualquier sync.
2. Origen (Producción): **solo lectura** (`pg_dump` / SELECT). Nunca escribir.
3. Sincronizar **únicamente** modelos de esta allowlist (o tablas equivalentes).
4. **Prohibido** tocar modelos de `DATA_SYNC_DENYLIST.md`.
5. Tras el sync: **no** reemplazar `ir_module_module` ni XML IDs; si faltan
   módulos Justech, **instalar/actualizar desde código** (`-i` / `-u`), luego
   reaplicar activaciones por empresa y feature flags desde backup DEV.
6. Neutralizar correo y `database.is_neutralized=true` en DESTINO.

## Modelos operativos autorizados

### Master data
- `res.partner` (+ bancos `res.partner.bank`)
- `res.company` (**solo campos maestros / fiscales de negocio**; no secretos SMTP)
- `product.template` / `product.product` / `product.category`
- `uom.uom` / `uom.category` (si el origen los trae como datos)
- `res.currency` / `res.currency.rate`
- `res.country` / `res.country.state` / `res.bank` (catálogos)

### Comercial
- `sale.order` / `sale.order.line`
- `purchase.order` / `purchase.order.line`
- `crm.lead` / `crm.stage` (si aplica)

### Contabilidad / tesorería
- `account.move` / `account.move.line`
- `account.payment` / `account.payment.method` / `account.payment.method.line`
- `account.partial.reconcile` / `account.full.reconcile`
- `account.bank.statement` / `account.bank.statement.line`
- `account.journal` / `account.account` / `account.tax` / `account.fiscal.position`
- `account.reconcile.model` (si se usa como dato operativo)

### Fiscal RD (datos / rangos / históricos)
- `account.fiscal.sequence` (+ `ir.sequence` **solo** las ligadas a NCF)
- `l10n_latam.document.type` (catálogo)
- Campos NCF en `account.move` (`l10n_latam_document_number`, etc.)
- Tablas de consumo/rangos Justech **de datos**: `justech.do.ncf.range`,
  `justech.do.ncf.consumption` (si existen y son datos, no flags de producto)
- Padrón: `justech.do.rnc.padron*` (datos)

### Inventario
- `stock.quant` / `stock.move` / `stock.move.line`
- `stock.picking` / `stock.picking.type`
- `stock.lot` / `stock.quant.package`
- `stock.location` / `stock.warehouse`

### Productividad / soporte
- `project.task` / `project.project` (tickets/tareas operativas)
- `mail.activity` / `mail.message` / `mail.followers`
- `ir.attachment` (**filestore asociado**)
- `discuss.channel` (si hay historial operativo relevante)

### Garantías (solo transacciones; no rehacer históricas en sync)
- `justech.warranty` / `justech.warranty.claim` (si se sincronizan como datos)
- Campos warranty en líneas de venta/factura: se reponen con el **módulo**, no
  con overwrite de `ir_*`

## Método recomendado (futuro)

Preferir **ETL por modelo** (export/import o `pg_dump --table` de tablas
operativas) sobre restore completo de BD.

Si se hace restore completo de dump Prod como atajo de emergencia:

1. Backup DEV previo (obligatorio).
2. Restore dump → DESTINO.
3. Reinstalar stack Justech desde addons (`-i` lista canónica).
4. Reaplicar desde backup DEV: activaciones `justech.admin.module.company`,
   `justech.ecf.company.config`, flags de compañía, grupos Justech por login.
5. Validar integridad operativa (conteos GL/NCF/pagos) vs snapshot pre-restore
   de **origen**, no vs DEV antiguo.

## Validación mínima post-sync

- Conteo facturas / pagos / conciliaciones / AML / partners / quants / NCF
- GL debit = credit
- `number_next` de secuencias fiscales activas
- Módulos `justech_*` = installed
- Mail external = 0; `database.is_neutralized=true`
- Producción sin escrituras
- Ejecutar **Reconciliar numeración fiscal** (wizard Justech) si se importaron
  NCF publicados: solo avanza `next_sequence` Justech si quedó detrás; nunca
  retrocede; nunca copia rangos/secuencias desde Prod.

## Lista canónica de módulos a reinstalar (DEV)

```
justech_core,justech_modules,justech_global_audit_log,
justech_l10n_do_base,justech_l10n_do_ncf,justech_l10n_do_adel_freeze,
justech_l10n_do_reports,justech_l10n_do_payments_withholding,justech_l10n_do_treasury,
justech_fiscal_admin,justech_admin_center,
justech_ecf_core,justech_ecf_xml,justech_ecf_signature,justech_ecf_queue,
justech_ecf_dgii,justech_ecf_admin,justech_warranty
```
