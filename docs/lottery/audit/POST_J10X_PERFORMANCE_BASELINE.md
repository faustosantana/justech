# POST J-10X — Performance Baseline

## Environment

| Item | Value |
|------|--------|
| Audit worktree | `/Users/faustosantana/Projects/justech-audit-post-j10x` |
| DEV API @ audit time | **DOWN** (`127.0.0.1:8001` health failed) |
| Production | Not load-tested (forbidden) |
| Evidence file | `evidence/post_j10x_pre_j11/PERF_DEV_SMOKE.txt` → `DEV_API_DOWN` |

## Qualitative baseline (from code + prod soak)

| Surface | Observation |
|---------|-------------|
| Prod soak post J-10X | 30/30 × 30s front/api/lottery = 200 |
| NR historical | Loads in-memory universe — cost grows with date span |
| `/analyze` v1 | Risk of N×M DB roundtrips (code review) |
| FE bundle | Next standalone image ~2.85GB (includes runtime); BUILD_ID `dO2ikilyvSLTeD5HlOupN` on prod j10x |
| historial-numero | Heaviest client page (~976 LOC, many sequential API calls) |

## Required baseline before J-11 coding (non-destructive)

When DEV API is up, capture p50/p95 for:

1. `GET /lottery/dashboard/v3`
2. `GET /lottery/catalog?featured_only=true`
3. `GET /lottery/admin/numeric-relations/tables`
4. `POST .../history/numbers/profile` (n=35, FEATURED_SEVEN, date_from=2015-01-01)
5. `POST .../history/compare` (35 vs candidate 50)
6. `POST .../history/numbers/why-strengthened`

Store under `evidence/post_j10x_pre_j11/PERF_DEV_BASELINE.json`.

## J-11 implication

Agent Runtime must:

- require date bounds on history tools;
- cache table catalog;
- debounce concurrent identical tool calls;
- stream long plans (not implemented today).
