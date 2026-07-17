# 09 — Seguridad y accesos

## Grupos fiscales (DEV)

| XMLID | Nombre | Usuarios |
|---|---|---|
| `justech_l10n_do_base.group_justech_do_fiscal_user` | Usuario Fiscal | **0** |
| `justech_l10n_do_base.group_justech_do_fiscal_manager` | Responsable Fiscal | **0** |
| `justech_fiscal_admin.group_justech_fiscal_admin_user` | Fiscal Admin / Lectura | **0** |
| `justech_fiscal_admin.group_justech_fiscal_admin_manager` | Administrador Fiscal | **1** |
| `justech_ecf_core.group_ecf_admin` | Administrador e-CF | 1 |
| Otros e-CF (operator/responsible/auditor/readonly) | — | 0 |

## Implicaciones

- Alertas NCF caen a fallback (Admin Fiscal / system) — coherente con baseline.
- SoD Responsable vs Admin: grupos existen; población insuficiente para operación real.
- `justech_security_ux` mapea niveles fiscales → grupos (docs ROLE_MAPPING).

## Access / rules

- CSV + rules en base, ncf, reports, payments, ecf, fiscal_admin.
- No se modificaron permisos.
- Riesgo: permisos excesivos vía `base.group_system` / account managers (histórico; security_ux intenta cortar imply).

## Hallazgo

**FISC-AUD-003 ALTO** — roles fiscales vacíos salvo 1 admin.
