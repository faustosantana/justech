# Changelog — justech_l10n_do_reports

## 19.0.1.24.2 — 2026-07-13

### Fixed
- 623: catálogo Gobierno global + legado `RET5%`; elegibilidad sin exigir conciliación bancaria.
- Carga de período vacía con mensaje accionable (empresa/fechas/causas).
- Chatter de revisión fiscal: HTML vía `Markup` (sin tags crudos).

## 19.0.1.24.0 — 2026-07-11

- ACL de lectura para `justech.do.dgii.period` (AbstractModel) — evita AccessError al invocar utilidades de período DGII.
- Menús de Auditoría Fiscal restringidos a grupos del Centro Fiscal.

## 19.0.1.20.0 — 2026-07-10

- Estabilización menú Auditoría Fiscal: 14 opciones bajo Contabilidad, nombres DGII exactos.
- Corrección Odoo 19: `group_ids` en menús Pendientes y Centro Fiscal.
- Clasificación fiscal desactivada en menú de auditoría.
