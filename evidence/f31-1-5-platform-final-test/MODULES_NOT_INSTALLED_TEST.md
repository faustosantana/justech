# Módulos con justech_register NO instalados en TEST

**Entorno:** `hellenia_test`  
**Fecha:** 2026-07-05  
**Decisión:** No instalar en esta fase (por aprobación explícita)

| Technical name | module_code | Estado ir.module.module | justech_register en repo |
|----------------|-------------|-------------------------|--------------------------|
| `justech_core` | justech_core | `uninstalled` | ✅ |
| `hellenia_inventory` | hellenia_inventory | `uninstalled` | ✅ |

## Impacto

- El wizard muestra **11 módulos** (solo instalados).
- El registry completo de producción tiene **13 módulos**.
- Al instalar estos módulos en el futuro, `register_all_installed_manifests()` los registrará automáticamente en el próximo `-u justech_modules`.

## Instalados en TEST (11)

`justech_modules`, `justech_l10n_do_base`, `justech_l10n_do_ncf`, `justech_l10n_do_reports`, `justech_report_design`, `hellenia_base`, `hellenia_ui`, `hellenia_account`, `hellenia_ux`, `hellenia_reports`, `hellenia_pos`
