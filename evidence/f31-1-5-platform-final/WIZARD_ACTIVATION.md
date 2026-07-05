# Module Activation Wizard — F31.1.5

## Location

**Menu:** Justech → Licencias → Module Activation  
**Models:** `justech.module.activation.wizard`, `justech.module.activation.wizard.line`

## Purpose

Allow Justech administrators to activate/deactivate commercial modules and features per company **without** installing or uninstalling Odoo technical modules. Acts as feature flags + licensing gate.

## Displayed Fields

| Field | Source |
|-------|--------|
| Module / Feature name | `justech.module` / `justech.feature` |
| Description | Manifest `justech_register` |
| Category | Module category |
| State (active/inactive) | `justech.license.service.is_active()` |
| Dependencies | Commercial DAG (`justech.module.dependency`) |
| Required | `required_module` flag |
| Licenciable | `license_required` |
| Company | Wizard `company_id` |
| Activation date / user | `justech.feature.company` |

## Actions

- **Refresh** — reload catalog from `get_activation_catalog()`
- **Activate Selected** — `activate_module()` or `activate_feature()`
- **Deactivate Selected** — `deactivate_module()` or `deactivate_feature()` (blocks always-on features)

## API Used (Public v1)

```python
service = env["justech.license.service"]
catalog = service.get_activation_catalog(company=company)
service.activate_module("hellenia_pos", company=company)
service.deactivate_feature("hellenia_pos", company=company)
```

## Security

- ACL: `justech.license.manager` and `base.group_system`
- All mutations audited via `_audit()`
- License validation enforced when `license_required=True`

## F31.1.5 Behavior

All production modules registered with `always_enabled: True` → everything active by default. Wizard is functional but does not block any current workflow.

## DEV Validation Steps (post-deploy)

1. Upgrade: `-u justech_modules`
2. Open wizard → verify 13 modules + features listed
3. Select non-always-on feature → deactivate → verify audit log
4. Reactivate → verify cache invalidation
