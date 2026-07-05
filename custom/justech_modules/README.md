# Justech Modules

Platform licensing engine for Justech ERP (F31.1 / F31.1b).

## Public API — version 1

Stable contract: `justech.license.service.API_VERSION = 1`

```python
service = env["justech.license.service"]
service.get_api_version()          # → 1
service.is_active("platform_core")
service.require_active("dgii_reports")
service.get_feature("platform_core")
service.validate_license(key="JT-STD-...", feature_code="dgii_reports")
service.check_dependencies("dgii_reports")
service.activate_feature("dgii_reports")
service.deactivate_feature("dgii_reports")
```

Breaking changes require incrementing `API_VERSION` and a migration note.

## Seed data

Platform catalog (`justech_modules`, `platform_core`) is seeded **only** via
`post_init_hook` → `register_platform_seed()`. No XML data seed.

## DEV install (product module only)

```bash
odoo-bin -d hellenia_dev -u justech_modules --test-enable --stop-after-init \
  --test-tags=/justech_modules
```

`justech_modules_test` is **DEV-only** and excluded from the product commit.

## Product commit scope

See `evidence/phase31-1b-justech-modules-p0/PRODUCT_COMMIT_FILES.txt`.
