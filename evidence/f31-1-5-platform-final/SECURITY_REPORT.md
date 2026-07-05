# Security Report — F31.1.5

**Scope:** `justech_modules` + wizard (new/changed code)  
**Date:** 2026-07-05

## ACL

| Model | Groups | Access |
|-------|--------|--------|
| `justech.module.activation.wizard` | license.manager, system | CRUD |
| `justech.module.activation.wizard.line` | license.manager, system | CRUD |
| Existing license models | Unchanged | PASS |

## Record Rules

- No new record rules; wizard is transient
- License models retain company-scoped rules from F31.1.2

## sudo() Usage

| Location | Justification | Risk |
|----------|---------------|------|
| `_audit()` | Audit log write bypasses user ACL | LOW — audit-only, no business data mutation |

## SQL Injection

- All queries via Odoo ORM `search()` / `browse()` — no raw SQL in new code

## CSRF / Web

- Wizard uses standard Odoo form actions — CSRF protected by framework

## Cache Security

- `ormcache` keys scoped by `feature_code` + `company_id` — no cross-tenant leakage in single-db model

## Portal / Public

- Wizard not exposed to portal or public users

## Findings

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| SEC-F315-01 | INFO | Wizard restricted to manager/system | None |
| SEC-F315-02 | INFO | Audit on all activate/deactivate | None |
| SEC-F315-03 | LOW | `get_feature` returns ORM (F31.1.3 debt) | Defer to governance sprint |

**Overall:** PASS — no new security regressions
