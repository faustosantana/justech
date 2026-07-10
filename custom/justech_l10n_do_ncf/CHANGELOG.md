# Changelog — Estándar Fiscal Justech (cierre)

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
