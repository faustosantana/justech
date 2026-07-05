# Hellenia Go-Live Readiness Report — F31.1.5

**Environment audited:** Local codebase + module inventory  
**Runtime DEV validation:** Pending user-approved deploy  
**Date:** 2026-07-05

## Executive Summary

The Hellenia ERP stack on Odoo 19 is **functionally complete for Dominican fiscal operations** at the module level. Platform licensing (F31.1.5) is closed in code. **Production go-live requires** DEV runtime validation, SMTP/backups/cron configuration on target VPS, and fiscal range verification on the live instance.

## Module Coverage

| Domain | Module | Status |
|--------|--------|--------|
| Platform / Licensing | `justech_modules` | ✅ 19.0.1.5.0 |
| Core | `justech_core` | ✅ Registered |
| Fiscal Base | `justech_l10n_do_base` | ✅ 19.0.1.4.2 |
| NCF | `justech_l10n_do_ncf` | ✅ 19.0.1.5.2 |
| DGII Reports (606/607/623) | `justech_l10n_do_reports` | ✅ 19.0.1.12.4 |
| Report Design | `justech_report_design` | ✅ 19.0.7.3.1 |
| Hellenia Base/UI/UX | `hellenia_base`, `hellenia_ui`, `hellenia_ux` | ✅ Registered |
| Accounting | `hellenia_account` | ✅ 19.0.1.0.27 |
| Reports/PDF | `hellenia_reports` | ✅ 19.0.1.5.7 |
| Inventory | `hellenia_inventory` | ✅ Registered |
| POS | `hellenia_pos` | ✅ Registered |

## Go-Live Checklist

### Fiscal / DGII

| Check | Code Evidence | Runtime |
|-------|---------------|---------|
| NCF sequences & types | `justech_l10n_do_ncf` | ⏳ DEV |
| ITBIS / tax mapping | `justech_l10n_do_base` | ⏳ DEV |
| Report 606 (Purchases) | `justech_l10n_do_reports` | ⏳ DEV |
| Report 607 (Sales) | `justech_l10n_do_reports` | ⏳ DEV |
| Report 623 (Withholdings) | `justech_l10n_do_reports` | ⏳ DEV |
| Fiscal ranges configured | NCF module | ⏳ DEV |
| Retenciones | `hellenia_account` + l10n | ⏳ DEV |

### Operations

| Check | Status | Notes |
|-------|--------|-------|
| Facturación (Sales invoices) | ✅ Module stack | Validate PDF + NCF on DEV |
| Compras | ✅ purchase deps | Validate vendor bills |
| Inventario | ✅ `hellenia_inventory` | Smoke test moves |
| Contabilidad / Plan de cuentas | ✅ `hellenia_account` + l10n_do | Verify COA |
| Cotizaciones / Conduces | ✅ `hellenia_reports` | PDF smoke test |
| POS | ✅ `hellenia_pos` | Session + NCF if used |

### Infrastructure

| Check | Status | Notes |
|-------|--------|-------|
| Usuarios / grupos | ⏳ | Verify on DEV |
| SMTP | ⏳ | Not in repo — ops task |
| Backups | ⏳ | VPS cron — ops task |
| Cron jobs | ⏳ | Verify Odoo cron on DEV |
| Logs / monitoring | ⏳ | Datadog optional |
| Healthcheck | ✅ | `HEALTHCHECK.json` (static) |

### Platform (F31.1.5)

| Check | Status |
|-------|--------|
| Module registry complete | ✅ 13/13 |
| Activation wizard | ✅ Implemented |
| All modules always_enabled | ✅ No blocking |
| API v1 frozen | ✅ |

## Blockers for Production

1. **No runtime validation this phase** — user restricted deploy; wizard and `-u justech_modules` not executed on `hellenia_dev`
2. **Operational items** — SMTP, backups, user provisioning on PROD
3. **Fiscal smoke tests** — NCF issuance, 606/607/623 export on real data
4. **SDK facade debt (F31.1.3)** — `get_feature` returns ORM; acceptable for go-live, should be addressed before governance

## Recommendation

**GO LIVE: CONDITIONAL YES** — proceed after:
1. Approved deploy to DEV + upgrade `justech_modules`
2. Wizard smoke test + existing 24/24 license tests
3. Fiscal regression (NCF, DGII reports, POS if used)
4. Ops checklist (SMTP, backup, cron)
