# GO LIVE FINAL REPORT — Hellenia (F31.4)

**Environment validated:** hellenia_test (https://test.hellenia.cloud)  
**Date:** 2026-07-05  
**Branch:** `feature/f31-1-justech-modules`  
**Commits:** F31.1.6 `0da5461` · F31.2 `f56e953` · F31.3 `68b7342` · F31.4 (this commit)  
**Tag:** `v1.0.0-licensing-engine`  
**PROD status:** NOT touched  
**Decision:** CONDITIONAL GO — ready for PROD after explicit approval

## Platform pillars (TEST)

| Pillar | Module | Status |
|--------|--------|--------|
| Licensing | justech_modules 19.0.1.5.0 | ✅ Installed, 27/27 tests |
| Governance | hellenia_governance 19.0.1.0.0 | ✅ Installed, 6/6 tests |
| Admin | justech_admin 19.0.1.0.0 | ✅ Installed, 1/1 tests |

## Functional regression (TEST)

| Area | Status |
|------|--------|
| Cotizaciones / PDF | ✅ PASS (F31.1.5) |
| Facturas / PDF | ✅ PASS |
| DGII 606/607/623 exporters | ✅ Present |
| POS | ✅ Installed + configured |
| NCF | ✅ No regression observed |
| Healthcheck | ✅ PASS |

## Operational checklist (pre-PROD)

| Item | TEST | PROD |
|------|------|------|
| SMTP | ⏳ Verify | ⏳ Required |
| Backups cron | ⏳ Verify | ⏳ Required |
| Odoo cron | ✅ | ⏳ |
| Users / roles | ⏳ Partial | ⏳ Required |
| NCF ranges | ⏳ Verify data | ⏳ Required |
| ITBIS / COA | ✅ l10n_do | ⏳ Verify |

## Hide from client

- Justech Admin (Centro de Control) — internal Justech only
- Module Activation wizard — Justech license managers
- Governance configuration — assign via Soporte Justech role only
- Technical audit logs (license + governance)

## Requires client approval

- User matrix (roles per person)
- POS visibility policy
- Go-live date / cutover window
- PROD NCF ranges authorization

## PROD promotion plan

See ROLLBACK_PLAN.md — backup PROD → deploy branch → `-u justech_modules,hellenia_governance,justech_admin` → smoke tests → sign-off
