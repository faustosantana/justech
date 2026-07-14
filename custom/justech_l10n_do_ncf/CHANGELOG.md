# Changelog — Estándar Fiscal Justech (cierre)

## [19.0.2.7.0] — 2026-07-14 — Hotfix moneda DOP + vigencia NCF

### Fixed
- Oculta `account.document_tax_totals_company_currency_template` (“Impuestos DOP”)
  en facturas multicurrency; el PDF solo muestra totales en moneda del documento.
- “Válida hasta:” usa `justech_do_ncf_range_id.date_to` si `l10n_do_ncf_expiration_date`
  está vacío; oculta la etiqueta cuando no hay fecha.

### Docs
- `docs/REPORT_HOTFIX_CURRENCY_NCF_VALIDITY.md`

## [19.0.2.6.2] — 2026-07-14 — Hotfix reportes (gate DO por compañía)

### Fixed
- `is_l10n_do_invoice` usa compañía DO (`l10n_do_country_code`), no el flag latam del diario.
  Cubre borradores sin NCF; no aplica a empresas no dominicanas.

## [19.0.2.6.1] — 2026-07-14 — Hotfix reportes (Studio fingerprint)

### Fixed
- Fingerprint Studio alineado al arch real (`information_block`, `name='address'`).

## [19.0.2.6.0] — 2026-07-14 — Hotfix reportes (Studio address + gate DO)

### Fixed
- Desactiva de forma idempotente la vista Studio destructiva
  `web_studio.report_editor_customization_diff.view._web.address_layout`
  (fingerprint + inherit `web.address_layout`) para restaurar address/information_block.
- Restaura `is_l10n_do_invoice` vía herencia QWeb Justech cuando el documento DO
  tiene evidencia fiscal (`l10n_latam_*` o Motor Justech), sin forzar latam en diarios.

### Docs
- `docs/REPORT_HOTFIX_IS_L10N_DO_INVOICE.md`

## [19.0.2.5.0] — 2026-07-14 — Resolución fiscal histórica

### Changed
- Orden de resolución en factura: default persistido → histórico por empresa →
  padrón/sugerencia → regla inequívoca (sin RNC→B01 ciego).
- Onchange de partner recalcula el tipo (no hereda del cliente anterior).
- Post bloquea clientes nuevos / revisión sin comprobante con mensaje claro.

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
