# P0.1 — Trazado de ejecución (DEV)

## Método

Análisis estático de MRO + revisión de servicios (sin logging permanente invasivo).  
Confirmación con flags de diario en BD DEV y feature flags.

## Cadena `_post` (empresa fiscal Justech + adel_freeze)

1. `justech_l10n_do_adel_freeze.account_move._post` — limpia `l10n_do_fiscal_sequence_id` → `super()`
2. `justech_l10n_do_ncf.account_move._post`:
   - `_justech_require_expense_type_before_post`
   - `_justech_validate_received_vendor_ncf_before_post` (LATAM NCF + prefijo)
   - `_justech_assign_ncf_before_post` → `assignment_service.assign_before_post`
   - **P0.1:** `_justech_validate_type_ncf_prefix_before_post` (todos los flows con tipo+NCF)
   - `super()._post`
3. Adel emission: `get_fiscal_number` **bloqueado** si Justech fiscal enabled
4. Journals: `l10n_latam_use_documents=False` (DEV: 0 journals con flag True)

## Assignment (emisión)

| Paso | Servicio | Escribe |
|---|---|---|
| resolve type | `ncf_document_type_resolver_service` | — |
| consume | `justech.do.ncf.range.consume_next` | range.next_sequence + consumption |
| write | `compat_sync.assignment_write_vals` | `justech_do_ncf`, range_id, doc_type; **LATAM solo si dual_write** |

## Lectura reportes/PDF

`fiscal_data_provider.get_ncf` / prefix / income / expense — sin writes.

## Evidencia BD DEV

- `ncf_dual_write` estaba `enabled=t` + `readonly_flag=t` → P0.1 lo desactiva vía migración.
- Diarios LATAM docs: 0 activos.

## Logging

No se dejó instrumentation permanente en Prod/DEV tras la fase.
