# Hellenia Go-Live Guide

**Version:** F31.1.5  
**Audience:** Justech ops + Hellenia administrators

## Pre-requisites

1. Odoo 19 instance with all Hellenia/Justech modules installed
2. `justech_modules` upgraded to **19.0.1.5.0**
3. Dominican company configured (`l10n_do`)

## Phase 1 — Platform Validation

```bash
# After user-approved deploy to DEV only
odoo-bin -u justech_modules -d hellenia_dev --stop-after-init
```

1. Open **Justech → Licencias → Module Activation**
2. Confirm 13 modules listed with `Active = True`
3. Run license tests: `--test-tags=justech_modules`

## Phase 2 — Fiscal Configuration

| Item | Action |
|------|--------|
| NCF ranges | Accounting → NCF sequences, assign authorized ranges |
| ITBIS | Verify tax groups from `justech_l10n_do_base` |
| Diarios | Sales, purchases, bank journals |
| Plan de cuentas | Confirm l10n_do COA loaded |

## Phase 3 — Functional Smoke Tests

- [ ] Customer invoice with NCF (B01/B02 as applicable)
- [ ] Vendor bill + ITBIS
- [ ] Credit note / debit note
- [ ] Report 606 export
- [ ] Report 607 export
- [ ] Report 623 export (if withholdings used)
- [ ] Quotation PDF (`hellenia_reports`)
- [ ] Delivery note / conduce PDF
- [ ] POS session (if used)
- [ ] Inventory move

## Phase 4 — Operations

| Item | Owner |
|------|-------|
| SMTP outbound mail | Ops |
| Automated DB backup | Ops |
| Odoo cron jobs enabled | Ops |
| User roles / groups | Admin |
| Log rotation | Ops |

## Phase 5 — Go / No-Go

**GO** when all Phase 1–4 checks pass on DEV, then repeat on PROD during cutover window.

See `evidence/f31-1-5-platform-final/GO_LIVE_REPORT.md` for detailed status.

## Rollback

- Do not uninstall modules
- Use wizard to deactivate features if needed (post-enforcement phases)
- Restore DB backup for catastrophic rollback
