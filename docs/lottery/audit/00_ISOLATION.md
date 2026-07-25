# Audit Isolation Record

| Field | Value |
|-------|--------|
| Branch | `audit/nr-post-j10x-pre-j11` |
| Base commit | `564a8c0` (approved J-10X tip) |
| Worktree | `/Users/faustosantana/Projects/justech-audit-post-j10x` |
| Created (UTC) | 2026-07-25 |
| Production | **untouched** — no image/DB/compose/deploy changes |
| production_forbidden | **true** |
| DEV DB (reference) | `jaios_lottery_dev` @ `127.0.0.1:5433` |
| DEV API (reference) | `127.0.0.1:8001` (was down during perf smoke; baseline deferred) |
| Scope | Documentation + non-invasive inventory only |

Constraints: no formulas, UUID, FEATURED_SEVEN, draws, migrations, or J-11 implementation.
