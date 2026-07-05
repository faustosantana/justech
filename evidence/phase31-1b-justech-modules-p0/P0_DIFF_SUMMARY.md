# F31.1b P0 — Diff summary (pre-commit)

**Module:** `justech_modules` · **19.0.1.0.0 → 19.0.1.1.0**

## Archivos nuevos

| Archivo | Propósito |
|---------|-----------|
| `models/justech_module_dependency.py` | DAG dependencias comerciales |
| `tests/test_dependencies.py` | T-05 |
| `tests/test_multi_company.py` | T-06 |
| `tests/test_audit_log.py` | T-07 + API_VERSION |

## Archivos eliminados

| Archivo | Razón |
|---------|-------|
| `data/justech_platform_features.xml` | P0-06 — seed único vía `post_init_hook` |

## Cambios principales por archivo

### `models/justech_license.py`
- `UNIQUE(license_key)` SQL constraint
- `license_key` required + auto-generación
- `action_activate()` exige ≥1 company + `_check_max_companies()`
- `_sync_company_features()` orden topológico + `activate_feature()`

### `models/justech_license_company.py`
- Enforcement `max_companies` en create/write/unlink

### `models/justech_license_service.py`
- `API_VERSION = 1`, `get_api_version()`
- `check_dependencies()`, `activate_feature()`, `deactivate_feature()`
- `_get_active_license_for_company()` — solo licencias con company explícita
- `_topological_sort_modules()`, `_order_features_by_module_dependencies()`

### `models/justech_module.py`
- `dependency_ids` One2many

### `security/justech_modules_security.xml`
- `ir.rule` company scope para `group_justech_license_user`

### `security/ir.model.access.csv`
- ACL `justech.module.dependency`

### `__manifest__.py`
- Version 19.0.1.1.0, removed XML data seed

### `README.md`
- API v1 contract documented

## Líneas aproximadas

- **+~450** líneas productivas/tests
- **−846** bytes XML seed eliminado
