# SDK Final — API v1 Frozen (F31.1.5)

**Module:** `justech_modules` 19.0.1.5.0  
**API_VERSION:** `1`  
**Contract:** `API_FINAL.json` (this folder)

## Public API — Complete List

| # | Method | Since | Breaking |
|---|--------|-------|----------|
| 1 | `get_api_version()` | F31.1 | — |
| 2 | `is_active(feature_code, company=None)` | F31.1 | — |
| 3 | `require_active(feature_code, company=None)` | F31.1 | — |
| 4 | `get_feature(feature_code)` | F31.1 | — |
| 5 | `validate_license(...)` | F31.1 | — |
| 6 | `check_dependencies(feature_code, company=None)` | F31.1b | — |
| 7 | `activate_feature(feature_code, company=None)` | F31.1b | — |
| 8 | `deactivate_feature(feature_code, company=None)` | F31.1b | — |
| 9 | `register_from_manifest(module_name, register_data, manifest=None)` | F31.1b | — |
| 10 | `get_activation_catalog(company=None)` | F31.1.5 | No |
| 11 | `activate_module(module_code, company=None)` | F31.1.5 | No |
| 12 | `deactivate_module(module_code, company=None)` | F31.1.5 | No |

## Freeze Policy

- No public method may change signature or semantics without incrementing `API_VERSION`
- Additive methods allowed within v1 (documented in CHANGELOG)
- Internal models remain private

## Consumer Pattern

```python
service = self.env["justech.license.service"]
assert service.get_api_version() == 1

if service.is_active("l10n_do_ncf", company=self.env.company):
    ...

service.require_active("hellenia_reports")
```

## Manifest Registration (v2)

```python
"justech_register": {
    "module_code": "...",
    "features": [{"code": "...", "name": "..."}],
    "dependencies": ["other_module_code"],
    "always_enabled": True,
}
```

## Known Debt (F31.1.3)

- `get_feature()` returns ORM recordset — facade not fully enforced
- Recommend proxy before `hellenia_governance`

## Full Reference

See `docs/JUSTECH_MODULES_SDK.md`
