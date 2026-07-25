# POST J-10X — Backend & API Audit

## Router inclusion

Lottery routers registered from API v1 router (numeric-relations + historical + lottery + AI admin + predictions). ~110 lottery-related endpoints (approx.).

## Endpoint families (map)

| Family | Prefix | Purpose | J-11 tool potential |
|--------|--------|---------|---------------------|
| Ordinary lottery | `/lottery/*` | dashboard, catalog, favorites, chat | get_lottery_results, get_active_lotteries, chat bridge |
| Admin ops | `/lottery/admin/*` | sync, scheduler, lotteries | get_system_status (guarded) |
| NR core | `/lottery/admin/numeric-relations/*` | tables, groups, analyze | get_table1/2_group, get_companions/confirmers |
| NR historical | `.../numeric-relations/history/*` | profile, occurrences, compare, why | primary Agent tools |
| AI admin | `/lottery/admin/ai/*` | prompts, models, benchmarks | admin System Agent only |
| Predictions | control-center predicciones APIs | motors | optional later |

### NR historical (canonical tool surface)

| Method | Path | Service |
|--------|------|---------|
| POST | `.../history/numbers/profile` | NumberExplorerService |
| POST | `.../history/numbers/occurrences` | NumberExplorerService |
| POST | `.../history/numbers/occurrences/detail` | NumberExplorerService |
| POST | `.../history/numbers/occurrences/next-draws` | NumberExplorerService |
| POST | `.../history/numbers/compare` | NumberExplorerService |
| POST | `.../history/numbers/why-strengthened` | NumberExplorerService |
| POST | `.../history/compare` | HistoricalAggregatesService |
| POST | `.../history/conditions/search` | HistoricalRelationsService |
| POST | `.../history/matrix` / `combinations` / `patterns/detail` / `cycles` | Aggregates/Relations |
| POST | `.../history/evidence/by-draw` | HistoricalRelationsService |

Permissions: `require_ai_admin` with `lottery_admin_ai` / `lottery.admin` / `lottery_admin_tools` on NR admin routes.  
**Note for J-11:** product users currently reach Historial via FE that calls these admin-prefixed routes after J-10X opened module access — permission matrix must be revalidated before exposing tools to `lottery_client`.

## Findings

### P0 — AUD-BE-001 Hardcoded SQLite path

Evidence:
- `backend/app/api/v1/lottery.py:1272`
- `backend/app/services/lottery_sync_service.py:326`
- `backend/app/services/lottery_sync_writer.py:145`

Path: `/Users/faustosantana/Projects/lottery-history-scraper/data/lottery.db`  
Impact: dry-run/sync defaults broken outside one laptop; Agent System tools must not inherit this.

### P1 — AUD-BE-002 No rate limiting on expensive NR endpoints

### P1 — AUD-BE-003 Unbounded / heavy universe loads

Historical `_prepare` can load large draw universes when dates omitted.

### P1 — AUD-BE-004 LLM keys as plain strings (no SecretStr/vault)

### P2 — AUD-BE-005 Raw `dict` bodies on many AI admin mutating endpoints

### P2 — AUD-BE-006 Umbrella permission `lottery.admin`

### P2 — AUD-BE-007 N×M query risk in v1 analyze path

## Strengths

- Pydantic schemas for historical bodies (`historical/api_schemas.py`).
- Scope clamp FEATURED_SEVEN on historical router.
- Audit logging hooks `_audit_nr_query` with `trace_id`.
- Tool executor does not recompute formulas.
