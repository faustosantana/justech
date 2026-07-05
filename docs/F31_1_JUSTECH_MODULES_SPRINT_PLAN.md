# Sprint F31.1 — justech_modules (Plan Detallado)

**Versión:** 1.0 · **Estado:** Plan aprobado — pendiente implementación  
**Fecha:** 2026-07-05  
**Duración:** 3 semanas · **120 horas**  
**Ambiente:** DEV únicamente (`hellenia_dev`)  
**Prerequisito:** Arquitectura F31 v2.0 aprobada · commit `9a2dc24`

> **Este documento es el plan de ejecución.** No implementar hasta autorización explícita de Sprint F31.1.

---

## 1. Objetivo del sprint

Entregar el módulo Odoo **`justech_modules`** — motor de licencias, catálogo comercial y activación de features — con API pública estable consumible por `hellenia_governance` (F31.2) y módulos funcionales futuros.

### Criterio de éxito (Definition of Done)

| # | Criterio |
|---|----------|
| G-01 | Módulo instala en DEV sin errores |
| G-02 | API `is_active`, `require_active`, `get_feature`, `validate_license` operativa |
| G-03 | Registro automático vía `justech_register` en manifest de prueba |
| G-04 | Tests T-01–T-08 green en CI local |
| G-05 | Multi-company: feature aislada por `company_id` |
| G-06 | Audit log en cada transición de licencia/feature |
| G-07 | Cero dependencias a hellenia_* / fiscal / governance |
| G-08 | Evidencia JSON + checklist en `evidence/phase31-1-justech-modules/` |
| G-09 | Rollback documentado (desinstalar módulo) |
| G-10 | No desplegado en TEST/PROD |

---

## 2. Alcance

### In scope

- Módulo nuevo `custom/justech_modules/`
- Modelos catálogo + licencia + audit
- Servicio `justech.license.service` (AbstractModel)
- Hook registro post_init / post_load
- Extensión manifest `justech_register`
- Vistas backend básicas (sin justech_admin)
- Seguridad ACL + ir.rule multi-company
- Tests unitarios TransactionCase
- Datos seed: features plataforma (`platform_core`, trial license DEV)
- Documentación README módulo

### Out of scope (F31.1)

- `hellenia_governance` — F31.2
- `justech_admin` — F31.3
- Registro masivo módulos Hellenia existentes — F31.4
- Integración módulos fiscales (`require_active` en reports) — F32
- API REST externa — F33
- Portal activación online — F36
- Marketplace — F35

---

## 3. Estructura del módulo

```
custom/justech_modules/
├── __init__.py
├── __manifest__.py
├── README.md
├── hooks.py                          # post_init_hook
├── exceptions.py                     # JustechLicenseError
├── models/
│   ├── __init__.py
│   ├── justech_module.py             # justech.module
│   ├── justech_feature.py            # justech.feature
│   ├── justech_module_dependency.py  # justech.module.dependency
│   ├── justech_license.py            # justech.license
│   ├── justech_license_feature.py    # justech.license.feature
│   ├── justech_license_company.py    # justech.license.company
│   ├── justech_feature_company.py    # justech.feature.company
│   ├── justech_activation_key.py     # justech.activation.key
│   ├── justech_license_audit.py      # justech.license.audit
│   └── justech_license_service.py    # justech.license.service (API)
├── wizard/
│   ├── __init__.py
│   └── justech_activation_wizard.py  # activar clave UI
├── security/
│   ├── justech_modules_security.xml  # grupos
│   └── ir.model.access.csv
├── data/
│   ├── justech_platform_features.xml # platform_core always-on
│   └── justech_dev_trial_license.xml # solo noupdate DEV seed opcional
├── views/
│   ├── justech_module_views.xml
│   ├── justech_feature_views.xml
│   ├── justech_license_views.xml
│   ├── justech_activation_key_views.xml
│   ├── justech_license_audit_views.xml
│   └── menu.xml
├── tests/
│   ├── __init__.py
│   ├── test_license_service.py       # T-02, T-03, T-04
│   ├── test_module_registry.py       # T-01, T-05
│   ├── test_multi_company.py         # T-06
│   ├── test_audit_log.py             # T-07
│   └── test_license_cache.py         # T-08
└── i18n/
    └── es.po
```

---

## 4. Manifest inicial

```python
{
    "name": "Justech Modules",
    "version": "19.0.1.0.0",
    "category": "Justech/Platform",
    "summary": "Motor de licencias y catálogo comercial Justech",
    "author": "Justech",
    "website": "https://justech.cloud",
    "depends": ["base", "mail"],
    "data": [
        "security/justech_modules_security.xml",
        "security/ir.model.access.csv",
        "data/justech_platform_features.xml",
        "views/justech_module_views.xml",
        "views/justech_feature_views.xml",
        "views/justech_license_views.xml",
        "views/justech_activation_key_views.xml",
        "views/justech_license_audit_views.xml",
        "views/menu.xml",
        "wizard/justech_activation_wizard_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
```

**Nota:** `application: True` temporalmente — menú propio hasta F31.3 absorba en justech_admin.

---

## 5. Modelos — especificación

### 5.1 `justech.module`

| Campo | Tipo | Notas |
|-------|------|-------|
| code | Char, required, index | PK lógico, unique |
| name | Char | Nombre comercial |
| description | Text | |
| version | Char | Semver manifest |
| category | Selection | platform, fiscal, reports, pos, integration |
| license_required | Boolean | False para platform_core |
| tier_minimum | Selection | STD, PRO, ENT, TRIAL |
| ir_module_id | Many2one ir.module.module | Link Odoo module |
| state | Selection | draft, registered, deprecated |
| feature_ids | One2many justech.feature | |
| dependency_ids | One2many justech.module.dependency | |

### 5.2 `justech.feature`

| Campo | Tipo | Notas |
|-------|------|-------|
| code | Char, required, unique | ej. `dgii_reports` |
| name | Char | |
| module_id | Many2one justech.module | |
| license_required | Boolean | |
| default_active | Boolean | False default |
| always_on | Boolean | platform features |
| company_activation_ids | One2many justech.feature.company | |

### 5.3 `justech.feature.company`

| Campo | Tipo | Notas |
|-------|------|-------|
| company_id | Many2one res.company | |
| feature_id | Many2one justech.feature | |
| is_active | Boolean | |
| activated_at | Datetime | |
| activated_by_id | Many2one res.users | |
| _sql_constraints | unique(company_id, feature_id) | |

### 5.4 `justech.license`

| Campo | Tipo | Notas |
|-------|------|-------|
| name | Char | Referencia interna |
| license_key | Char, unique | Hash almacenado opcional |
| tier | Selection | STD, PRO, ENT, TRIAL |
| state | Selection | draft, active, expired, revoked |
| expires_at | Date | |
| max_users | Integer | 0 = unlimited |
| max_companies | Integer | |
| feature_ids | Many2many via justech.license.feature | |
| company_ids | One2many justech.license.company | |
| grace_days | Integer | default 7 |

### 5.5 `justech.activation.key`

| Campo | Tipo | Notas |
|-------|------|-------|
| key | Char, unique | JT-STD-XXXXXXXXXXXX |
| tier | Selection | |
| state | Selection | unused, used, revoked |
| license_id | Many2one justech.license | post-activación |
| used_at | Datetime | |
| used_by_id | Many2one res.users | |

### 5.6 `justech.license.audit`

| Campo | Tipo | Notas |
|-------|------|-------|
| action | Selection | register, activate, deactivate, validate, revoke, expire |
| feature_id | Many2one | optional |
| license_id | Many2one | optional |
| company_id | Many2one | |
| user_id | Many2one | |
| details | Json | |
| ip_address | Char | optional |

---

## 6. API — implementación `justech.license.service`

AbstractModel `_name = "justech.license.service"`.

### 6.1 `is_active(feature_code, company=None)`

```python
def is_active(self, feature_code, company=None):
    company = company or self.env.company
    feature = self._get_feature(feature_code)
    if not feature:
        return False
    if feature.always_on:
        return True
    if not self._license_valid(company):
        return False
    if feature.license_required and not self._feature_in_license(feature, company):
        return False
    return self._feature_active_for_company(feature, company)
```

**Cache:** `@tools.ormcache('feature_code', 'company.id')` — invalidar en write license/feature.company.

### 6.2 `require_active(feature_code, company=None)`

```python
def require_active(self, feature_code, company=None):
    if not self.is_active(feature_code, company=company):
        raise JustechLicenseError(
            _("Feature '%s' is not licensed or active for this company.") % feature_code
        )
```

### 6.3 `get_feature(feature_code)`

Retorna `justech.feature` record o empty recordset.

### 6.4 `validate_license(key, feature_code=None, company=None)`

Retorna dict:
```python
{
    "valid": bool,
    "reason": str,  # "ok" | "expired" | "revoked" | "feature_not_included" | "invalid_key"
    "expires": date | False,
    "tier": str,
}
```

### 6.5 `register_module(module_name)` (interno)

1. Leer manifest del módulo vía `load_manifest`
2. Si `justech_register` presente → upsert `justech.module` + `justech.feature`
3. Crear dependencias comerciales
4. Audit log `register`
5. Link `ir.module.module` si instalado

### 6.6 Excepción

```python
class JustechLicenseError(UserError):
    """Feature not licensed or inactive."""
```

---

## 7. Hook registro

```python
# hooks.py
def post_init_hook(env):
    env["justech.license.service"].register_platform_modules()
    # Registra justech_modules itself + scan installed justech_* modules
```

Al instalar cualquier módulo con `justech_register`, llamar registry desde `base` module install hook pattern:

```python
# En ir.module.module override (optional F31.1)
def button_install(self):
    res = super().button_install()
    for mod in self:
        if mod.name.startswith("justech_"):
            self.env["justech.license.service"].register_module(mod.name)
    return res
```

---

## 8. Seguridad

### Grupos

| Grupo | XML ID | Acceso |
|-------|--------|--------|
| Justech License User | `group_justech_license_user` | Read features, own company activation |
| Justech License Manager | `group_justech_license_manager` | CRUD licencias, activación |
| Justech License Admin | `group_justech_license_admin` | Full + audit + keys |

**Inicial:** solo `base.group_system` + `group_justech_license_manager` en F31.1.

### ir.rule

| Modelo | Regla |
|--------|-------|
| justech.feature.company | company_id in company_ids |
| justech.license.company | company_id in company_ids |
| justech.license.audit | company_id in company_ids or admin |

---

## 9. Plan de tareas (3 semanas)

### Semana 1 — Fundamentos (40h)

| ID | Tarea | h | Dep |
|----|-------|--:|-----|
| W1-01 | Scaffold módulo + manifest + security groups | 4 | — |
| W1-02 | Modelos justech.module, justech.feature, dependency | 8 | W1-01 |
| W1-03 | Modelos justech.license, license.feature, license.company | 8 | W1-02 |
| W1-04 | Modelos feature.company, activation.key, audit | 6 | W1-03 |
| W1-05 | justech.license.service — is_active, get_feature | 8 | W1-04 |
| W1-06 | require_active, validate_license, JustechLicenseError | 6 | W1-05 |

### Semana 2 — Registro + UI (40h)

| ID | Tarea | h | Dep |
|----|-------|--:|-----|
| W2-01 | register_module + post_init_hook | 8 | W1-06 |
| W2-02 | ir.module.module install hook (scan justech_*) | 4 | W2-01 |
| W2-03 | Data seed platform features + trial license | 4 | W2-01 |
| W2-04 | Vistas módulo, feature, license | 12 | W1-04 |
| W2-05 | Wizard activación clave | 6 | W2-04 |
| W2-06 | Menú Justech > Licencias (temporal) | 2 | W2-04 |
| W2-07 | Dependencia comercial — validación activación | 4 | W2-01 |

### Semana 3 — Tests + evidencia (40h)

| ID | Tarea | h | Dep |
|----|-------|--:|-----|
| W3-01 | Tests T-01–T-04 (registry + API) | 12 | W2-01 |
| W3-02 | Tests T-05–T-08 (deps + multi-co + cache) | 12 | W3-01 |
| W3-03 | Instalar DEV + smoke manual | 4 | W3-02 |
| W3-04 | Módulo prueba `justech_modules_test` (justech_register) | 4 | W2-01 |
| W3-05 | Evidencia JSON + checklist + rollback doc | 4 | W3-03 |
| W3-06 | README + i18n es.po strings críticos | 4 | W3-03 |

---

## 10. Módulo de prueba (F31.1)

Crear `custom/justech_modules_test/` (EXCLUIDO SKU — solo DEV):

```python
"justech_register": {
    "code": "justech_modules_test",
    "feature_code": "test_feature",
    "license_required": True,
    "dependencies": [],
}
```

Valida T-01 registro automático sin tocar módulos producción.

---

## 11. Despliegue DEV

### Pre-requisitos

- [ ] Backup BD hellenia_dev
- [ ] Rama feature: `feature/f31-1-justech-modules`
- [ ] `-u` no aplicar en PROD/TEST

### Comandos (referencia — ejecutar solo en implementación)

```bash
# Backup
ssh root@2.25.69.179 'pg_dump hellenia_dev > /backup/hellenia_dev_pre_f31_1.sql'

# Install
odoo-bin -d hellenia_dev -i justech_modules --stop-after-init

# Tests
odoo-bin -d hellenia_dev --test-enable -i justech_modules --stop-after-init
```

### Rollback

1. Desinstalar `justech_modules` desde Apps (DEV)
2. Restaurar backup si corrupción
3. Evidencia rollback en `evidence/phase31-1-justech-modules/ROLLBACK.md`

---

## 11. Feature codes seed (catálogo inicial F31.1)

| Feature code | always_on | license_required | Notas |
|--------------|:---------:|:----------------:|-------|
| platform_core | ✅ | ❌ | justech_modules itself |
| governance | ❌ | ❌ | Placeholder F31.2 — pre-registrar |
| admin_panel | ❌ | ❌ | Placeholder F31.3 |
| fiscal_base | ❌ | ✅ | Placeholder — activar F31.4 |
| fiscal_ncf | ❌ | ✅ | Placeholder |
| dgii_reports | ❌ | ✅ | Placeholder |

Solo `platform_core` activo en F31.1. Resto registra estructura sin activar.

---

## 12. Riesgos sprint

| ID | Riesgo | Prob | Mitigación |
|----|--------|------|------------|
| R-01 | Scope creep hacia governance | Alta | Checklist out-of-scope estricto |
| R-02 | Cache stale is_active | Media | T-08 + invalidación explícita |
| R-03 | Conflict con justech_core skeleton | Baja | No tocar justech_core; módulo independiente |
| R-04 | DEV regression módulos existentes | Media | Solo install additive; no -u fiscal |
| R-05 | Odoo 19 AbstractModel patterns | Baja | Seguir justech_l10n_do_base patterns |

---

## 13. Checklist pre-implementación

- [x] Arquitectura F31 v2.0 aprobada
- [x] Docs commitadas (`9a2dc24`)
- [ ] Rama feature creada
- [ ] Backup DEV programado
- [ ] Autorización explícita sprint F31.1

---

## 14. Entregables post-sprint

| Entregable | Ubicación |
|------------|-----------|
| Módulo justech_modules | `custom/justech_modules/` |
| Módulo test | `custom/justech_modules_test/` |
| Evidencia | `evidence/phase31-1-justech-modules/` |
| Checklist DoD | `evidence/phase31-1-justech-modules/checklist.csv` |
| JSON resultado | `evidence/phase31-1-justech-modules/f31_1_result.json` |

---

## 15. Handoff a F31.2

Al completar F31.1, `hellenia_governance` consumirá:

```python
# En enable_feature (governance F31.2)
if not env["justech.license.service"].is_active(feature_code, company):
    raise UserError(_("Feature not licensed"))
```

API estable — **no cambiar signatures** post F31.1 sin ADR.

---

## Referencias

- `docs/JUSTECH_MODULES_ARCHITECTURE.md`
- `docs/ERP_PLATFORM_ARCHITECTURE.md`
- `docs/ERP_INFRASTRUCTURE_ROADMAP.md`
- `docs/ERP_DEVELOPMENT_STANDARD.md`
