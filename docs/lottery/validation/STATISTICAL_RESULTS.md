# Statistical Results — Manual Cases vs NR Geometry

Sample size: **5 cases** (small; treat as forensic, not population inference).

## Definitions (case level)

- **TP / coincidence:** hypothesis `produced` contains `manual_fuerte`
- **FN:** fuerte not in `produced`
- **Exact singleton:** `produced == [manual_fuerte]`
- **Avg extras:** mean of `|produced \ {fuerte}|` across cases (false-positive mass)
- **Precision / Recall / F1:** here computed as case-recovery rates (TP/n); with n=5 these equal success rate for binary recovery

## Table

| Hypothesis | Cases | TP | FN | Success % | Exact % | Avg extras | Precision | Recall | F1 | Evidence |
|------------|------:|---:|---:|----------:|--------:|-----------:|----------:|-------:|---:|----------|
| A compañeros∩vecinos | 5 | 4 | 1 | 80 | 60 | ~0.4 | 0.80 | 0.80 | 0.80 | media |
| B vecinos∩vecinos | 5 | 1 | 4 | 20 | 0 | — | 0.20 | 0.20 | 0.20 | baja |
| C compañeros∩compañeros | 5 | 0 | 5 | 0 | 0 | — | 0.00 | 0.00 | 0.00 | nula |
| D ∈ compañeros | 5 | 4 | 1 | 80 | 0 | 4.0 | 0.80 | 0.80 | 0.80 | baja |
| E ∈ vecinos | 5 | 5 | 0 | 100 | 0 | 9.4 | 1.00 | 1.00 | 1.00 | media* |
| **F forma-motor** | 5 | **4** | **1** | **80** | **60** | **0.2** | **0.80** | **0.80** | **0.80** | **alta para fidelidad** |
| G T2 singleton | 5 | 3 | 2 | 60 | 60 | 0.0 | 0.60 | 0.60 | 0.60 | media (explica C2) |
| H peers T1 código | 5 | 0 | 5 | 0 | 0 | — | 0.00 | 0.00 | 0.00 | nula |

\*E’s perfect recall is not actionable — large neighbor sets of 70/44 inflate membership hits.

## Confusion focus — Hypothesis F (official shape)

| | Predicted contains fuerte | Predicted misses fuerte |
|--|---------------------------|-------------------------|
| Manual fuerte is the intended strengthened candidate | C1, C3, C4, C5 | C2 |

False negative: **C2 only**.

## Historical appearance checks

| Caso | Claim | Result in DEV |
|------|-------|---------------|
| C4 | 54 appears next day | **YES** — Loteka 2026-06-24 `[54,69,13]` |
| C5 | 54 appears next day in Gana Más | **UNKNOWN** — no draws on 2026-07-22/23 (DB max 2026-07-21) |

## Machine-readable

`docs/lottery/validation/evidence/summary.json`
