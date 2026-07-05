# Roadmap — Post F31.1.5

## Completed (F31.1.x)

- [x] F31.1 — Licensing engine initial
- [x] F31.1.2 — Hardening (LIFE, CONC, SEC, PERF)
- [x] F31.1.3 — SDK documentation + certification
- [x] F31.1.5 — Platform closure + wizard + registry

## Recommended Next Sprint: F31.2 — DEV Validation + Hellenia Go-Live Prep

1. Deploy F31.1.5 to `hellenia_dev` (user approval)
2. `-u justech_modules` + register verification
3. Wizard smoke test + audit log verification
4. Fiscal regression suite (NCF, 606/607/623, PDF, POS)
5. Ops checklist (SMTP, backup cron, users)

## Then: F32 — hellenia_governance (when approved)

**Prerequisites:**
- DEV validation of wizard complete
- Decision on SDK facade enforcement (`get_feature` proxy)
- Wire `service.require_active()` in 2–3 pilot modules

**Scope:**
- Policy engine for feature enforcement
- Admin dashboards (not full justech_admin)
- Audit views for activation history

## Deferred (explicitly out of scope)

- justech_admin (full SaaS admin)
- Marketplace
- IA / Blobby integration
- Multi-tenant
- e-CF

## Timeline Suggestion

| Sprint | Focus |
|--------|-------|
| F31.2 | DEV deploy + go-live validation |
| F32 | hellenia_governance MVP |
| F33 | Enforcement rollout (pilot modules) |
| F34 | PROD go-live Hellenia |
