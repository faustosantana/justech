# Historical Manual Logic Audit — Spec

## Purpose

Validate the partner’s same-day multi-lottery manual logic (Tabla 1 → candidates → Tabla 2 confirmers → fuerte) over FEATURED_SEVEN history **before** any J-11A work.

## Non-goals

- Do not modify motor formulas, Tabla 1/2, draws, or Production.
- Do not start J-11A in this phase.
- Do not treat results as a predictive guarantee.

## Official methodology (immutable)

```
observed → Tabla 1 companions → candidates
each candidate → Tabla 2 neighbors → confirmers
if confirmer ∈ other same-day observations → strengthen candidate only
```

Absolute rules:

1. Confirmer is never strengthened.
2. Direct Tabla 2 neighbor is **not** fuerte by itself (`DIRECT_T2_NEIGHBOR_SIGNAL` rejected).
3. Only Tabla 1 candidates may be strengthened.
4. C2 (41×62 → 75) remains rejected as a predictive rule.
5. FEATURED_SEVEN only; archived lotteries excluded.
6. No look-ahead in candidate selection; manual fuerte used only for final compare.

## Unit of analysis

`date + FEATURED_SEVEN first in-universe numbers (1..100) that day`

Anchors C1/C3/C4/C5(/C2) use partner subsets on those dates.

## Validation windows (reported separately)

| Window | Definition |
|--------|------------|
| A next_chronological_draw | First FEATURED draw after max case draw index |
| B same_day_other_draws | Same calendar day, draw_id ∉ case inputs |
| C next_calendar_day | All FEATURED draws on date+1 |
| D next_7_featured_draws | Next 7 FEATURED draws chronologically |

Note: for full-day units, B is structurally empty (all featured draws that day are inputs).

## Selection of 10+ cases

- Seed: `20260726`
- Fixed anchors: C1, C3, C4, C5
- Forced: C2 rejected
- Fill quotas by seeded shuffle: ≥5 hits / ≥3 fails / ≥1 multi / ≥1 none / ≥1 DIRECT_T2
- Remainder chronological
- No reordering by posterior success

## API (read-only)

| Method | Path |
|--------|------|
| POST | `/api/lottery/admin/numeric-relations/historical-audit` |
| GET | `/api/lottery/admin/numeric-relations/historical-audit/{audit_id}` |
| GET | `/api/lottery/admin/numeric-relations/historical-audit/{audit_id}/cases` |
| POST | `/api/lottery/admin/numeric-relations/historical-audit/{audit_id}/cancel` |

UI: `/lottery/admin/control-center/motor/historical-audit`

## Isolation

See `00_ISOLATION.md`. Branch `feature/nr-historical-manual-logic-audit` from `47192af`.
