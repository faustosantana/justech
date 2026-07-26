# Historical Audit Methodology

## Engine

Module: `backend/app/lottery/numeric_relations/historical_manual_audit.py`  
Runner: `backend/app/lottery/numeric_relations/historical_audit_runner.py`  
CLI: `backend/scripts/run_historical_manual_logic_audit.py`

Methodology version: `nr-historical-relations-j1.0.0` (unchanged).

## Strengthening

For unique observed numbers \(O\) on a case day:

For each generator \(g \in O\):

1. Candidates = Tabla 1 companions of \(g\) (exclude self).
2. For each candidate \(c\): confirmers = Tabla 2 neighbors of \(c\) ∩ \((O \setminus \{g\})\).
3. If confirmers non-empty → \(c\) is official fuerte (merge confirmers if multiple generators).

Confirmers are never added as fuertes.

## Direct T2 (rejected)

If observed \(a\) has Tabla 2 neighbor \(b\) and \(b\) is not an official fuerte, emit `DIRECT_T2_NEIGHBOR_SIGNAL` with `rejected_as_predictive_rule=true`.

## Look-ahead control

- Strengthening uses only same-day observations.
- Window evaluation may read future draws **only for scoring**.
- Selection of the 10+ sample does not sort by posterior success.
- `known_manual_fuerte` is attached after computation for compare only.

## Baseline comparison (fair)

Window: `next_calendar_day`.

Hit iff `prediction_set ∩ unique_FEATURED_numbers(date+1) ≠ ∅`.

Denominator: cases with ≥1 official fuerte and at least one next-day featured draw.

Comparators:

1. Random one number in 1..100  
2. Random same \(k\) as official fuerte count  
3. Empirical base frequency = mean(|U|/100)  
4. Direct T2 neighbors of first observation (rejected rule)  
5. First-observation T1 companions without confirmation (cap 5)

Lift near 1 ⇒ no predictive claim.
