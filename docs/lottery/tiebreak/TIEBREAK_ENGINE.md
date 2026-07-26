# Tiebreak Engine

## Purpose

Reorder **already discovered** candidates when scores are tied (real or practical).  
Does **not** rediscover candidates. Does **not** change Tabla 1 / Tabla 2 formulas.

## Pipeline position

```
Candidate Ranker → Tiebreak Engine → ranking final
```

## Module

`backend/app/lottery/numeric_relations/analysis_engine/tiebreak_engine.py`

- Version: `tiebreak-engine-j1.0.0`
- Selected rule id: `TIEBREAK_PROFILE_SOCIO_V1`
- Default practical threshold: `0.0` (all Phase-2 errors were exact score ties)

## Responsibilities

1. Detect `EMPATE_REAL` (identical score) or `EMPATE_PRÁCTICO` (gap ≤ threshold).
2. Apply hierarchical socio criteria on the leading tie group.
3. Preserve original scores (`score_before == score_after`).
4. Emit a decision trace per candidate.
5. When evidence remains identical → `EMPATE_MULTI_FUERTE` (no lexicographic fake winner).

## Decision fields

| Field | Meaning |
|-------|---------|
| `original_rank` / `final_rank` | Position before/after tiebreak |
| `score_before` / `score_after` | Preserved score |
| `tiebreak_triggered` | Whether this number was in the tie group |
| `tiebreak_rule` | Hypothesis / selected rule id |
| `tiebreak_evidence` | Key tuple, threshold, tie kind |
| `candidates_compared` | Numbers in the tie group |
| `decision_margin` | Score gap to winner (0 under multi) |
| `tie_status` | `none` / `real` / `practical` / `unresolved_multi` |
| `unresolved_tie` | True when multi-fuerte |
| `shared_rank` | Shared rank for unresolved peers |
| `engine_version` | Traceability |

## Integration

`complete_analysis_service.run_complete_analysis(..., enable_tiebreak=True)`  
Result payload includes `tiebreak` with decisions and `multi_fuerte_numbers`.

## Non-goals

- No hardcoding of M1–M5 or the 14 historical errors.
- No ML / future-label features.
- No Production changes.
