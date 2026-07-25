# Pre-J11A — Implementation Plan

Confirmed from audit tip `0435642` against base `564a8c0`.

## Principles

1. Do not reinterpret audit findings.
2. Do not change NR methodology or FEATURED_SEVEN.
3. Do not touch Production.
4. Do not start J-11A Agent Runtime in this phase.
5. Fail closed on missing SQLite config (no silent prod path).
6. Rate limits must not break normal FE usage.

## Block details

### B1 — SQLite

- Single typed setting: `LOTTERY_SYNC_SQLITE_PATH` → `settings.lottery_sync_sqlite_path`
- Resolver: explicit arg → env/settings → clear error
- No `/Users/...` fallback
- Tests: valid / missing / nonexistent / permissions / no hardcoded absolutes

### B2 — API guards

- In-process rate limiter per user+route (Redis optional later)
- Date range max days (document value; allow full historic span of product data)
- Max lotteries / numbers / page size
- Spanish HTTP 400/429 errors + rate-limit headers when possible

### B3 — AppShell

- Mirror Control Center layout pattern
- Remove alternate header/sidebar from `admin/ai/layout.tsx`
- Keep AI sub-nav as in-content navigation only

### B4 — CI

- Workflow: backend pytest+guards, frontend lint/typecheck/build, lottery Playwright smoke, methodology/security checks
- No Production credentials or URLs

### B5 — LLM secrets

- Reuse / restore Fernet vault with master key outside DB
- Abstraction for store/mask/rotate/audit
- Plan document only + minimal code foundation (no real provider connect)

## Commit / push cadence

Push after each stable block. Stop on failed mandatory tests.
