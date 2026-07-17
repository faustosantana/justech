# P0.1 — Implementación mínima

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `justech_l10n_do_base/services/fiscal_config_service.py` | SoT helper; dual_write default OFF |
| `justech_l10n_do_base/__manifest__.py` + CHANGELOG | 19.0.1.27.0 |
| `justech_fiscal_admin/data/justech_fiscal_feature_flag_data.xml` | dual_write default False, no readonly |
| `justech_fiscal_admin/migrations/19.0.1.9.0/post-migrate.py` | UPDATE flag OFF en BD existentes |
| `justech_fiscal_admin/__manifest__.py` + CHANGELOG | 19.0.1.9.0 |
| `justech_l10n_do_ncf/models/account_move.py` | gate prefijo post-assign |
| `justech_l10n_do_ncf/tests/test_ncf_source_of_truth_p01.py` | tests |
| `justech_l10n_do_ncf/__manifest__.py` + CHANGELOG | 19.0.2.15.0 |

## No tocado

- Baseline alertas (`ncf_range` protected methods)
- Documentos históricos
- Exporters DGII (siguen FDP)
- Desinstalación LATAM/Adel
- Campos renombrados/eliminados

## Comportamiento

1. Assignment escribe solo Justech si dual_write OFF.
2. Publicación falla si tipo≠prefijo NCF.
3. FDP sigue leyendo históricos LATAM-only.
