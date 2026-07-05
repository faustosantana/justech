# F31.1.5 — Final Architecture: justech_modules Platform

**Date:** 2026-07-05  
**Module version:** `justech_modules` 19.0.1.5.0  
**API version:** **1 (FROZEN)**

## Summary

`justech_modules` is the stable licensing and feature-flag platform for all Justech/Hellenia Odoo 19 modules. F31.1.5 closes the platform layer with:

1. **Frozen public API v1** — no breaking changes allowed without `API_VERSION` bump
2. **Manifest-driven registry** — `justech_register` in every production module
3. **Bulk registration hook** — `register_all_installed_manifests` on post_init
4. **Activation Wizard** — admin UI for module/feature toggles without Odoo install/uninstall
5. **Optional mixin** — `justech.license.mixin` for future `is_active` / `require_active` integration

## Layer Model

```
┌─────────────────────────────────────────────────────────┐
│  Hellenia / Justech Business Modules                    │
│  (hellenia_*, justech_l10n_*, justech_report_*)         │
└───────────────────────────┬─────────────────────────────┘
                            │ justech_register (manifest)
                            │ service.is_active() [future]
┌───────────────────────────▼─────────────────────────────┐
│  justech_modules — Platform                             │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │ Public API v1   │  │ Internal models              │  │
│  │ license.service │  │ justech.module, .feature,    │  │
│  │                 │  │ .license, .audit, .dependency  │  │
│  └────────┬────────┘  └──────────────────────────────┘  │
│           │                                             │
│  ┌────────▼────────┐  ┌──────────────────────────────┐    │
│  │ Activation      │  │ Cache (ormcache) + indexes   │  │
│  │ Wizard (UI)     │  │ Audit log + rollback hooks   │  │
│  └─────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Public vs Private

| Surface | Classification | Stability |
|---------|----------------|-----------|
| `justech.license.service` methods documented in SDK | PUBLIC | Frozen v1 |
| `justech.module`, `justech.feature`, ORM models | INTERNAL | May evolve |
| `hooks_register.py`, `_audit`, `_upsert_*` | PRIVATE | Implementation detail |
| Activation Wizard | ADMIN UI | Uses public API only |

## Registration Flow

1. `justech_modules` post_init → `register_platform_seed()` + `register_all_installed_manifests()`
2. Each manifest `justech_register` block defines module metadata, features, commercial dependencies
3. `always_enabled: True` → `license_required=False`, `default_active=True` (no functional blocking in F31.1.5)

## Multi-Company

- Feature activation is per `res.company` via `justech.feature.company`
- License assignment respects `max_companies` (F31.1.2)
- Wizard scoped to selected company

## Backward Compatibility

- Schema v1 (`feature_code`) still supported in `register_from_manifest`
- Schema v2 (`features[]`, `dependencies[]`, `always_enabled`) additive
- All existing modules remain active by default — zero behavior change

## Out of Scope (F31.1.5)

- hellenia_governance, justech_admin, Marketplace, IA, SaaS, multi-tenant, e-CF
- Enforcement in business modules (Part D prepared, not wired)
- TEST/PROD deployment

## Certification Status

| Area | Status |
|------|--------|
| Separation of concerns | PASS |
| API v1 freeze | PASS |
| Odoo 19 compatibility | PASS |
| Cache + invalidation | PASS |
| Security (ACL, audit) | PASS |
| Performance (ormcache, indexes) | PASS |
| Constraints + rollback | PASS |
| Multi-company | PASS |
| Documentation | PASS |
| Semver / versioning | PASS |

**Platform closure:** COMPLETE (pending DEV runtime validation after user-approved deploy)
