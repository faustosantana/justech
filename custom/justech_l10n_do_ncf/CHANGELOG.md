# Changelog — Estándar Fiscal Justech (cierre)

## [19.0.2.4.1] — 2026-07-13

### Fixed
- RPC_ERROR del Centro Fiscal: placeholders `_()` mixtos nombrados/`%.1f` en diagnóstico de rangos NCF.
- Defensas ante `name`/`remaining_count`/`pct_used` nulos en mensajes de stock bajo.

## [19.0.2.4.0] — 2026-07-13

### Added
- Migración controlada legacy Adel → Motor Fiscal Justech (`justech.do.ncf.migration.*`) con previsualización obligatoria.
- Reconciliación post-sync de numeración (`justech.do.ncf.reconcile.*`) — solo avanza, nunca retrocede.
- Auditoría de migración (`justech.do.ncf.migration.log`).
- Menú Motor Fiscal NCF: migración, reconciliación y auditoría.

### Changed
- Asignación en ventas auto-asignables: ya no publica en silencio sin NCF (exige diario `justech_do_use_ncf` o NCF manual / rango activo).
- Dual-write LatAm solo refleja NCF generado por Justech.

### Notes
- Secuencias Adel permanecen como histórico; `get_fiscal_number` bloqueado si Justech fiscal está activo.
- Tras sync de transacciones desde Prod: ejecutar reconciliación; no copiar rangos/`ir.sequence` de Prod.

## [19.0.2.3.1] — 2026-07-10

### Changed
- Campo `justech_do_document_type_id` oculto en formulario de cotización/pedido (`invisible="1"`).
- La herencia interna hacia la factura (`_prepare_invoice`) se mantiene intacta.
- El tipo de comprobante fiscal sigue visible en facturas (cliente/proveedor, NC/ND).

## [19.0.2.2.4] — 2026-07-10

### Fixed
- Lectura fiscal en formularios vía campos display seguros (`fiscal_*_display`) y Fiscal Data Provider.
- Estado histórico Adel: **Histórico compatible** (nunca «Incompleto» cuando hay NCF válido).
- NCF histórico visible en facturas de venta/compra sin backfill ni escritura.

### Added
- Regla permanente Cursor: auditoría de herencia XML antes de tocar vistas/menús.
- UAT de cierre (shell + visual) en `justech_dev`.

## [19.0.2.0.0] — 2026-07-10

### Added
- `justech_l10n_do_payments_withholding`: motor pagos con retenciones (wizard único).
- `justech_fiscal_admin`: Centro de Administración Fiscal + feature flags runtime.
- Menú **Auditoría Fiscal** consolidado (606–623, NCF, retenciones, centro fiscal).

### Fixed
- RPC `action_justech_open_fiscal_admin_center` en Ajustes → Fiscal Justech.
- Dependencia circular `justech_fiscal_admin` ↔ `justech_l10n_do_reports`.
- Pantalla facturas restaurada (pestaña compacta Comprobante Fiscal).
- Feature flags conectados: `ncf_motor`, `ncf_dual_write`, `duplicate_blocking`, `payments_withholding`.

### Scripts
- `fiscal-closure-run.sh`, `fiscal-standard-cleanup.py`, `fiscal-clean-install-lab.sh`.
