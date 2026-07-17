# P0.1 — Resultados de pruebas (DEV)

**Fecha:** 2026-07-17  
**BD:** `justech_dev`  
**Artefacto:** `/opt/odoo-dev/backups/p0_1-ncf-sot-20260717_142449/exports/uat_results.json`

## Resultado

**all_pass: true**

| Check | PASS |
|---|---|
| dual_write_off | ✓ |
| mirror_empty (latam_mirror_vals={}) | ✓ |
| fdp_priority Justech→LATAM | ✓ |
| SoT JUSTECH / PlugSafe / Just Office / Omni | ✓ |
| gate_blocks_mismatch (B01 tipo + B02 NCF) | ✓ |
| consistent_ok | ✓ |
| exporters 606–623 presentes | ✓ |
| ranges fingerprint unchanged | ✓ |
| GL diff 0 | ✓ |
| mail NCF alerts 0 | ✓ |
| alert activities open 0 | ✓ |
| historic mismatches still 19 (untouched) | ✓ |

## Versiones tras upgrade

- `justech_l10n_do_base` 19.0.1.27.0
- `justech_l10n_do_ncf` 19.0.2.15.0
- `justech_fiscal_admin` 19.0.1.9.0

## Tests unitarios agregados

`custom/justech_l10n_do_ncf/tests/test_ncf_source_of_truth_p01.py` (tag `justech_ncf_sot_p01`)

## Secuencias / históricos

- Rangos next_sequence: sin cambio
- Posted moves count: sin cambio
- Históricos prefijo≠tipo: **no modificados**
