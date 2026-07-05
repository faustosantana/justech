# Changelog — F31.1.5 Platform Final

**Module:** `justech_modules` 19.0.1.5.0  
**API:** v1 (frozen, additive methods only)

## Added

- `hooks_register.py` — manifest-driven bulk registration
- `register_all_installed_manifests()` — post_init scan of justech_*/hellenia_* modules
- `get_activation_catalog()`, `activate_module()`, `deactivate_module()` — public API v1
- `justech.module.activation.wizard` — admin activation UI
- `justech.license.mixin` — optional `_justech_is_active` / `_justech_require_active`
- Fields on `justech.module`: `country`, `localization`, `required_module`
- `justech_register` in all 13 production module manifests

## Changed

- `register_from_manifest` — schema v2 support (`features[]`, `dependencies[]`, `always_enabled`)
- post_init hook calls bulk registration after platform seed

## Unchanged (by design)

- All modules `always_enabled: True` — no functional blocking
- No Odoo install/uninstall from wizard
- No fiscal logic changes
- Existing 24/24 tests unchanged

## Documentation

- GO LIVE GUIDE, MODULE REGISTRY, INSTALL ORDER, WIZARD ACTIVATION GUIDE
- Evidence pack: `evidence/f31-1-5-platform-final/`

## Not Done (per restrictions)

- No deploy to DEV/TEST/PROD
- No commit/push/merge
