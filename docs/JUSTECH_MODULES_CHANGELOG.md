# Justech Modules — Changelog

All notable changes to the **public SDK** (`justech.license.service`).

Format based on API major version. Module semver in parentheses.

---

## API v1 — Frozen (F31.1.3, extended F31.1.5)

**Freeze date:** 2026-07-05  
**Module version:** 19.0.1.5.0  
**Certification:** F31.1.3 SDK + F31.1.5 Platform Final

Public surface locked:

- `get_api_version`
- `is_active`
- `require_active`
- `get_feature`
- `validate_license`
- `check_dependencies`
- `activate_feature`
- `deactivate_feature`
- `register_from_manifest`
- `get_activation_catalog` *(F31.1.5 additive)*
- `activate_module` *(F31.1.5 additive)*
- `deactivate_module` *(F31.1.5 additive)*

Contract: `evidence/f31-1-5-platform-final/API_FINAL.json`

---

## [19.0.1.5.0] — F31.1.5 Platform Final (2026-07-05)

**Additive API (non-breaking):**

- `get_activation_catalog`, `activate_module`, `deactivate_module`
- `register_from_manifest` schema v2 (`features[]`, `dependencies[]`, `always_enabled`)
- Activation wizard UI
- Bulk manifest registration hook
- `justech.license.mixin` for future integration

**No behavior change:** all production modules `always_enabled: True`.

---

## [19.0.1.2.0] — F31.1.2 Hardening (2026-07-05)

**SDK behavior changes (non-breaking for v1 contract):**

- `is_active` now returns `False` when license is expired (LIFE-01)
- `activate_feature` / license activation enforce `max_users` (COMP-02)
- License keys stored as SHA-256 hash; `validate_license(key=...)` still accepts plaintext key at API boundary
- `is_active` / `get_feature` performance: ormcache + indexes (PERF-01)
- Duplicate `justech.license.company` prevented (CONC-01)

**No method signatures changed.**

---

## [19.0.1.1.0] — F31.1b P0 (2026-07-05)

- Added `activate_feature` / `deactivate_feature` to public API
- Added `check_dependencies` for commercial DAG
- Added `register_from_manifest` for module registration
- `API_VERSION = 1` introduced
- `justech.module.dependency` model (internal)
- `max_companies` enforcement on license assignment
- Platform seed via `register_platform_seed` hook (private)

---

## [19.0.1.0.0] — F31.1 Initial (2026-07-04)

- Initial `justech.license.service` abstract model
- Core methods: `is_active`, `require_active`, `get_feature`, `validate_license`
- Models: module catalog, features, licenses, audit
- `JustechLicenseError` exception
- Multi-company `ir.rule` scoping

---

## Unreleased / planned (API v2 candidates)

- `get_feature_info()` DTO replacing recordset return
- `JustechLicenseError.code` stable error enum
- `list_features(company)` / `list_active_features(company)` for IA/admin
- Audit failed `validate_license` attempts (SEC-02)
- `grace_days` behavior documented and enforced
- `activation.key` provisioning via admin SDK methods
- Consumer ACL hardening (deny direct ORM)
- Deprecate public `clear_license_cache`

---

## Migration notes

### From pre-F31.1 (none in production)

N/A — first platform release.

### Future v1 → v2

See [Versioning Guide](./JUSTECH_MODULES_VERSIONING.md).
