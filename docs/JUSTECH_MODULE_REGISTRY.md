# Justech Module Registry

**Generated:** F31.1.5  
**Source of truth:** `justech_register` in each `__manifest__.py` + `evidence/f31-1-5-platform-final/MODULE_REGISTRY.csv`

## Production Modules (13)

| Technical Name | Module Code | Category | Required | Features |
|----------------|-------------|----------|----------|----------|
| `justech_modules` | justech_modules | platform | — | platform_core |
| `justech_core` | justech_core | platform | — | justech_core |
| `justech_l10n_do_base` | justech_l10n_do_base | fiscal | ✅ | l10n_do_base |
| `justech_l10n_do_ncf` | justech_l10n_do_ncf | fiscal | ✅ | l10n_do_ncf |
| `justech_l10n_do_reports` | justech_l10n_do_reports | reports | ✅ | l10n_do_reports |
| `justech_report_design` | justech_report_design | reports | — | justech_report_design |
| `hellenia_base` | hellenia_base | platform | ✅ | hellenia_base |
| `hellenia_ui` | hellenia_ui | ux | — | hellenia_ui |
| `hellenia_account` | hellenia_account | accounting | ✅ | hellenia_account |
| `hellenia_ux` | hellenia_ux | ux | — | hellenia_ux |
| `hellenia_reports` | hellenia_reports | reports | ✅ | hellenia_reports |
| `hellenia_inventory` | hellenia_inventory | inventory | — | hellenia_inventory |
| `hellenia_pos` | hellenia_pos | pos | — | hellenia_pos |

## Excluded (test only)

- `justech_modules_test`
- `justech_report_templates_test`

## Registration

Automatic on `justech_modules` post_init via `register_all_installed_manifests()`.

Per-module optional hook:

```python
def post_init_hook(env):
    from odoo.addons.justech_modules.hooks_register import register_from_manifest_hook
    register_from_manifest_hook(env, "my_module")
```

## Default Policy (F31.1.5)

All modules: `always_enabled: True` → no functional blocking.

## Manifest Schema (v2)

```python
"justech_register": {
    "module_code": "hellenia_pos",
    "module_name": "Hellenia POS",
    "version": "19.0.1.0.0",
    "category": "pos",
    "country": "DO",
    "description": "...",
    "dependencies": ["hellenia_base"],  # commercial DAG
    "always_enabled": True,
    "required_module": False,
    "features": [{"code": "hellenia_pos", "name": "Hellenia POS"}],
}
```
