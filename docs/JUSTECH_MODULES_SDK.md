# Justech Modules SDK — Official Reference (API v1)

**Module:** `justech_modules`  
**Module version:** `19.0.1.5.0`  
**SDK API version:** `1` (frozen F31.1.3, extended F31.1.5)  
**Facade:** `env["justech.license.service"]`  
**Status:** Platform closed F31.1.5 — activation wizard + manifest registry

---

## Purpose

`justech_modules` is the **platform licensing SDK** for Justech ERP. Every future module (governance, admin, marketplace, IA, localizations, countries) must interact with licensing **only** through this service.

Direct access to internal models (`justech.license`, `justech.feature`, etc.) is **prohibited** for consumer modules.

---

## Quick start

```python
service = self.env["justech.license.service"]

# Version gate (recommended at module load)
assert service.get_api_version() == 1

# Runtime gate in business logic
if service.is_active("dgii_reports", company=self.env.company):
    ...

# Hard gate (raises if inactive)
service.require_active("dgii_reports")

# Activate / deactivate (governance/admin only)
service.activate_feature("dgii_reports", company=company)
service.deactivate_feature("dgii_reports", company=company)
```

---

## Public API v1 — complete inventory

| Method | Parameters | Returns | Raises |
|--------|------------|---------|--------|
| `get_api_version()` | — | `int` (always `1`) | — |
| `is_active(feature_code, company=None)` | `feature_code: str`, `company?: res.company` | `bool` | — |
| `require_active(feature_code, company=None)` | same | `None` | `JustechLicenseError` |
| `get_feature(feature_code)` | `feature_code: str` | `justech.feature` recordset | — |
| `validate_license(key=None, feature_code=None, company=None)` | optional key/feature/company | `dict` (see below) | — |
| `check_dependencies(feature_code, company=None)` | `feature_code: str`, `company?` | `dict` `{ok, missing}` | — |
| `activate_feature(feature_code, company=None)` | `feature_code: str`, `company?` | `True` | `JustechLicenseError` |
| `deactivate_feature(feature_code, company=None)` | `feature_code: str`, `company?` | `True` | `JustechLicenseError` |
| `register_from_manifest(module_name, register_data, manifest=None)` | hook registration | `(module, features)` recordsets | — |
| `get_activation_catalog(company=None)` | `company?` | `list[dict]` module/feature rows | — |
| `activate_module(module_code, company=None)` | module + company | `True` | `JustechLicenseError` |
| `deactivate_module(module_code, company=None)` | module + company | `True` | `JustechLicenseError` |

**Default company:** all methods use `env.company` when `company` is omitted.

---

## Method reference

### `get_api_version()`

Returns the **major API version** integer. Breaking changes increment this value.

```python
>>> env["justech.license.service"].get_api_version()
1
```

---

### `is_active(feature_code, company=None)`

Returns whether a feature is **licensed and operationally active** for the company.

**Rules (F31.1.2):**
- `always_on` features → always `True` (e.g. `platform_core`)
- Expired licenses → `False` even if feature was previously activated
- Requires valid license grant + active `justech.feature.company` row (or `default_active`)

```python
if service.is_active("hellenia_governance_core"):
    return super().action_confirm()
return self._fallback_confirm()
```

---

### `require_active(feature_code, company=None)`

Same as `is_active`, but raises `JustechLicenseError` if inactive.

```python
from odoo.addons.justech_modules.exceptions import JustechLicenseError

try:
    service.require_active("pos_fiscal_mixed")
except JustechLicenseError as exc:
    raise UserError(str(exc)) from exc
```

---

### `get_feature(feature_code)`

Returns the `justech.feature` record (or empty recordset).

> **Stability note:** Returns an internal ORM model. Prefer using `feature_code` strings in consumer code. A DTO-based `get_feature_info()` is recommended for API v2.

```python
feature = service.get_feature("platform_core")
if feature:
    name = feature.name  # display only — do not write
```

---

### `validate_license(key=None, feature_code=None, company=None)`

Validates license state without raising. Returns a **frozen contract dict**:

| Field | Type | Description |
|-------|------|-------------|
| `valid` | `bool` | Overall validity |
| `reason` | `str` | Reason code (enum below) |
| `expires` | `date \| False` | Expiration date if applicable |
| `tier` | `str \| False` | `TRIAL`, `STD`, `PRO`, `ENT` |

**Reason codes (frozen v1):**

| Code | Meaning |
|------|---------|
| `ok` | Valid |
| `invalid_key` | Key not found |
| `no_license` | No key provided and no company license |
| `revoked` | License revoked |
| `not_active` | License in draft/other non-active state |
| `expired` | Past `expires_at` |
| `unknown_feature` | Feature code not in catalog |
| `feature_not_included` | License active but feature not granted |

```python
result = service.validate_license(
    key="JT-STD-XXXX",
    feature_code="dgii_reports",
    company=company,
)
if not result["valid"]:
    log.warning("License invalid: %s", result["reason"])
```

---

### `check_dependencies(feature_code, company=None)`

Checks commercial module dependency DAG.

```python
deps = service.check_dependencies("child_feature", company=company)
if not deps["ok"]:
    codes = [m["module_code"] for m in deps["missing"]]
    raise UserError("Missing modules: %s" % ", ".join(codes))
```

**Missing item shape:** `{module_code, module_name, dependency_type}`

---

### `activate_feature(feature_code, company=None)`

Activates a feature for a company. Validates:
- Feature exists
- Not `always_on` (noop if always_on → returns `True` without write)
- Dependencies satisfied
- Active non-expired license includes feature (if `license_required`)
- `max_users` not exceeded (F31.1.2)

**Intended callers:** `hellenia_governance`, `justech_admin`, license managers.

---

### `deactivate_feature(feature_code, company=None)`

Deactivates operational flag. Cannot deactivate `always_on` features.

---

### `register_from_manifest(module_name, register_data)`

**Call only from your module's `post_init_hook`.**

Registers module + feature in the commercial catalog.

**`__manifest__.py` example:**

```python
{
    "name": "My Module",
    "justech_register": {
        "code": "my_module",
        "feature_code": "my_module_core",
        "name": "My Module",
        "category": "fiscal",
        "license_required": True,
        "tier_minimum": "STD",
    },
    "post_init_hook": "post_init_hook",
}
```

**`hooks.py`:**

```python
def post_init_hook(env):
    from odoo.modules.module import load_manifest
    manifest = load_manifest("my_module")
    data = manifest.get("justech_register")
    if data:
        env["justech.license.service"].register_from_manifest("my_module", data)
```

---

## Exception

```python
from odoo.addons.justech_modules.exceptions import JustechLicenseError
```

- Subclass of `odoo.exceptions.UserError`
- Raised by `require_active`, `activate_feature`, `deactivate_feature`
- **Not** raised by `validate_license` (returns dict instead)

---

## Platform seed

On install, `justech_modules` seeds via hook (not XML):

| Module code | Feature code | Flags |
|-------------|--------------|-------|
| `justech_modules` | `platform_core` | `always_on=True`, `license_required=False` |

---

## Integration matrix

| Consumer | Primary methods |
|----------|-----------------|
| **Any business module** | `is_active`, `require_active` |
| **hellenia_governance** | `activate_feature`, `deactivate_feature`, `check_dependencies`, `validate_license` |
| **justech_admin** | `validate_license`, `activate_feature`, `deactivate_feature` |
| **Marketplace** | `register_from_manifest`, `check_dependencies` |
| **IA / Blobby** | `is_active`, `get_feature` (read metadata), `validate_license` |
| **Localizations / countries** | `register_from_manifest`, `is_active`, `require_active` |

---

## Related documents

- [API Guide](./JUSTECH_MODULES_API_GUIDE.md) — examples (Python, ORM, RPC, XML, actions)
- [Developer Guide](./JUSTECH_MODULES_DEVELOPER_GUIDE.md) — allowed / forbidden
- [Versioning](./JUSTECH_MODULES_VERSIONING.md) — v1 vs v2, breaking changes
- [Changelog](./JUSTECH_MODULES_CHANGELOG.md)
- Contract: `evidence/f31-1-3-sdk-certification/api-contract.json`

---

## Certification

| Check | Status |
|-------|--------|
| API v1 inventoried | ✅ |
| Contract JSON | ✅ |
| Examples | ✅ |
| Behavior unchanged F31.1.3 | ✅ |
| Facade-only enforcement | ⚠️ Documented; not technically enforced |

See `evidence/f31-1-3-sdk-certification/` for scorecard and diagrams.
