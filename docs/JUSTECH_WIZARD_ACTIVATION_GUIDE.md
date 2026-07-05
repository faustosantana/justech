# Wizard Activation Guide — Justech Module Activation

## Overview

The **Module Activation Wizard** lets Justech administrators toggle commercial modules and features per company without changing Odoo's technical module installation state.

## Access

- **Path:** Justech → Licencias → Module Activation
- **Groups:** Justech License Manager, Settings / System

## Workflow

### 1. Open wizard

Select the target **company** (multi-company environments).

### 2. Review catalog

Each row shows:
- **Module** row — commercial module summary
- **Feature** rows — individual feature flags under the module

Columns include category, dependencies, required flag, license requirement, active state, activation date, and activating user.

### 3. Activate

1. Check **Selected** on desired rows
2. Click **Activate Selected**
3. System validates:
   - Commercial dependencies (`check_dependencies`)
   - Valid license (when `license_required=True`)
4. Audit log entry created

### 4. Deactivate

Same flow with **Deactivate Selected**. Always-on features (e.g. `platform_core`) cannot be deactivated.

### 5. Refresh

Click **Refresh** to reload state after external changes.

## Important Rules

| Rule | Detail |
|------|--------|
| No install/uninstall | Odoo `ir.module.module` state unchanged |
| Feature flags | Uses `justech.feature.company.is_active` |
| Cache | Cleared automatically after mutations |
| F31.1.5 default | All modules `always_enabled` — everything active |

## API Reference

See `docs/JUSTECH_MODULES_SDK.md` — methods:
- `get_activation_catalog`
- `activate_module` / `deactivate_module`
- `activate_feature` / `deactivate_feature`

## Future Integration (Part D)

Business modules may inherit `justech.license.mixin`:

```python
if self._justech_is_active("hellenia_pos"):
    ...
self._justech_require_active("l10n_do_ncf")
```

Not wired in F31.1.5 — no behavior change.

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Module not in list | Verify `justech_register` in manifest + `-u justech_modules` |
| Cannot activate | Check license assignment or missing dependency |
| Still active after deactivate | Feature may be `always_on` |

Evidence: `evidence/f31-1-5-platform-final/WIZARD_ACTIVATION.md`
