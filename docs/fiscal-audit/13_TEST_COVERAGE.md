# 13 — Cobertura de pruebas (inventario)

## Existentes (no ejecutadas en esta fase salvo inventario)

### justech_l10n_do_base
- `test_justech_l10n_do_base.py`, hardening, validators, fiscal_data_provider

### justech_l10n_do_ncf
- core, sprint2, sprint2_part2, purchase_registration_mode
- **`test_ncf_alerts_consolidated_baseline.py`** (baseline protegida)

### justech_l10n_do_reports
- phase19–21 DGII 606/607/review/approval/framework; hardening; FDP reports

### e-CF / security_ux
- tests core/mock/signature/admin/multicompany engines; operational permissions

## Gaps

| Área | Cobertura |
|---|---|
| Alertas NCF consolidadas | Alta (baseline tests) |
| Unicidad v2.0 / multiempresa NCF | Media-alta |
| Prefijo≠tipo en LATAM stack | **Baja** (gap) |
| 608/609 E2E con datos reales | Baja |
| Roles fiscales ACL matriz completa | Media (security_ux) |
| payments_withholding / treasury / adel_freeze | **Sin tests propios** |
| Dual-stack sync Justech↔LATAM | Baja |

## Política esta fase

No se crearon pruebas nuevas (solo scripts SQL de auditoría no invasivos en evidencia).
