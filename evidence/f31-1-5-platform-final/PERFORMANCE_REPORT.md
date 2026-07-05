# Performance Report — F31.1.5

**Scope:** New/changed code in F31.1.5  
**Date:** 2026-07-05

## Existing Optimizations (unchanged)

- `is_active` / `_get_feature_id_cached` — `@ormcache`
- DB indexes on `justech.feature.code`, license company lines (F31.1.2 PERF-01)
- Cache invalidation via `clear_license_cache()` on mutations

## New Code Analysis

### `get_activation_catalog`

- Iterates all `justech.module` records (13 modules — negligible)
- Per-feature: 1 `search` on `justech.feature.company` + 1 `is_active` (cached)
- **Assessment:** Acceptable for admin wizard; not hot path

### `register_all_installed_manifests`

- Runs once on post_init/upgrade
- **Assessment:** No runtime impact

### Wizard `_reload_lines`

- Rebuilds transient lines from catalog
- **Assessment:** Admin-only, acceptable

## N+1 Review

| Area | Status |
|------|--------|
| Catalog loop | Minor N+1 on feature.company search — 13 modules × ~1 feature = ~26 queries max |
| Business modules | No new queries added |

## Recommendations (non-blocking)

1. Batch `justech.feature.company` lookup in catalog if module count grows >50
2. Prefetch `feature_ids` on module search in catalog

**Overall:** PASS — no performance regressions; wizard is admin-scoped
