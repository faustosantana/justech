# Changelog — Estándar Fiscal Justech (cierre)

## [19.0.2.12.1] — 2026-07-14 — Hotfix void NCF sin Hellenia

### Fixed
- Wizard 100% en `justech_l10n_do_ncf` (catálogo 608 del move + «Otro» UX).
- Aviso claro si la factura tiene pagos/parcial; no toca pagos ni conciliaciones.
- `button_cancel` oculto también con NCF anulado; herencia Justech solo.
- `button_draft` no reactiva ni reutiliza NCF anulado ni borra traza 608.
- Sin dependencia de `hellenia_ux` para el flujo.

### Unchanged
- Producción; secuencias; asientos históricos; 606/607/609/623 lógica.

## [19.0.2.12.0] — 2026-07-14 — Wizard anulación NCF + Cancelar asiento

### Added
- Wizard modal `justech.do.ncf.void.wizard`: motivo 608, observación (obligatoria si Otro), ayuda 608.
- Botón «Anular NCF» abre el wizard (`action_open_void_ncf_wizard`).

### Fixed
- Motivo inaccesible: ya no exige campo oculto en el form.
- `button_cancel` (Cancelar asiento): invisible fuera de `draft` (corrige fórmula rota de `l10n_do_accounting`).
- Anulación idempotente con mensaje claro; chatter legible; no cancela el asiento contable.

### Unchanged
- Secuencias/rangos; no auto nota de crédito; 606/607/609/623 sin cambios de lógica.

## [19.0.2.11.1] — 2026-07-14 — Hotfix Cotización de referencia (PO)

### Fixed
- Cotización de referencia: enlace inequívoco vía `sale_line_id` o `origin→sale.order` (bi_convert).
- Smart button si hay múltiples cotizaciones origen.
- `partner_ref` ya no recibe el nombre de cotización desde bi_convert.
- Migración: limpia `partner_ref` solo si `partner_ref == origin == sale.order.name` (misma empresa).

### Unchanged
- Fiscal, NCF, secuencias, facturas, pagos, GL.

## [19.0.2.11.0] — 2026-07-14 — RC-FISCAL-UX-FINAL (Centro + columnas)

### Changed
- Filtro superior Tipo de Flujo (dropdown Todos / Ventas / Compras Emitidos / Compras Recibidos).
- Tarjetas KPI unificadas: Tipos / Activos / Pendientes / Sin rango.
- Columnas por flujo según UX operativa; `last_used` en Ventas y Compras Emitidos (lectura).
- Menú raíz: Fiscal República Dominicana (sin menús nuevos).

### Unchanged
- Sin inventar rangos; sin consumo NCF; DGII/histórico intactos.

## [19.0.2.10.0] — 2026-07-14 — Centro único Rangos (filtros de flujo)

### Added
- `justech.do.fiscal.range.center` + líneas unificadas:
  Todos / Ventas / Compras Emitidos / Compras Recibidos.
- KPIs superiores; ficha de detalle; columna Consume secuencia / Origen / Flujo.

### Changed
- Menú **Rangos** = Centro de Administración Fiscal (Localización Dominicana).
- Menús satélite de documentos Compras desactivados (sin duplicar).

### Unchanged
- Sin rangos ficticios; sin consumo de NCF; histórico intacto.

## [19.0.2.9.0] — 2026-07-14 — UX admin Compras + costos/gastos editables

### Added
- `justech_do_expense_type_id` editable en borrador (factura proveedor).
- Sugerencia histórica no bloqueante (`justech_do_expense_type_manual`).
- Administración: documentos recibidos LATAM; emisión B11/B13/B17; rangos Compras.
- Menú Localización Dominicana → Compras.
- Post-migrate: enlace `l10n_do_expense_type` → catálogo Justech.

### Changed
- Emisión compras: botón «Administrar rango»; nombres/ayudas operativas.

### Fixed
- El “Tipo de costos y gastos” deja de ser solo un display readonly.

## [19.0.2.8.0] — 2026-07-14 — Compras: recibidos LATAM vs emisión B11/B13/B17

### Added
- Campo `justech_do_purchase_registration_mode` en facturas de proveedor
  (`received` | `issued`).
- Modelo `justech.do.purchase.emission.config`: configuración por empresa de
  B11/B13/B17 sin inventar rangos; `emission_enabled` solo con rango activo.
- UX Compras: selector de tipo de registro; LATAM dominio recepción B+E;
  emisión Justech limitada a `is_purchase_document`.
- Post-migrate idempotente: 12 configs (4 empresas × 3 tipos) + modo `received`
  en históricos nulos.
- Tests `test_purchase_registration_mode`.

### Changed
- Assignment: documentos recibidos no consumen rangos/secuencias Justech;
  emisión sin rango bloquea con mensaje nominativo (código + nombre).
- Nombres display B11/B13/B17 con código + nombre funcional completo.

### Unchanged
- Continuidad JUSTECH B11@11 / B13@213; sin rangos ficticios; Ventas intactas.

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
