# Hypothesis Analysis

All hypotheses measured on the 5 manual cases. None were written into the motor.

## Catalogue

| ID | Hypothesis | Definition (predictive) |
|----|------------|-------------------------|
| A | Intersección compañeros×vecinos | ∪ companions(a)∩neighbors(b) over pairs |
| B | Intersección vecinos×vecinos | ∪ neighbors(a)∩neighbors(b) |
| C | Intersección compañeros×compañeros | ∪ companions(a)∩companions(b) |
| D | Membresía en compañeros | Fuerte ∈ ∪ companions(obs) |
| E | Membresía en vecinos | Fuerte ∈ ∪ neighbors(obs) (wide; high recall, low precision) |
| F | **Forma del motor oficial** | companion(N) confirmed when another obs ∈ neighbors(candidate) |
| G | Par T2 singleton | If obs has exactly one T2 neighbor, emit it |
| H | Peers mismo código T1 del número | ∩ t1_peers(a) |

## Measured outcomes (n=5)

| ID | Coincidencias | Success % | Exact singleton % | Avg extras | F1 (case recovery) | Evidence |
|----|---------------|-----------|-------------------|------------|--------------------|----------|
| A | 4 | 80 | 60 | low | 0.80 | media |
| B | 1 | 20 | 0 | — | 0.20 | baja |
| C | 0 | 0 | 0 | — | 0.00 | nula |
| D | 4 | 80 | 0 | 4.0 | 0.80 | baja (no predictivo) |
| E | 5 | 100 | 0 | 9.4 | 1.00 | media-engañosa (demasiado ancha) |
| **F** | **4** | **80** | **60** | **0.2** | **0.80** | **principal** |
| G | 3 | 60 | 60 | 0 | 0.60 | explica C2/C4/C5 pairs |
| H | 0 | 0 | 0 | — | 0.00 | nula |

Source: `evidence/summary.json` after fair G predictor.

## Case × hypothesis hits

| Caso | A | F | G | Notas |
|------|---|---|---|-------|
| C1 | ✓ exact 29 | ✓ exact 29 | — | Motor oficial |
| C2 | — | — | ✓ exact 75 | Solo par T2 de 62 |
| C3 | ✓ (set) | ✓ {22,35} | — | Manual elige 35; F también lo tiene |
| C4 | ✓ exact 54 | ✓ exact 54 | ✓ 54 | Motor + par T2 de 14 |
| C5 | ✓ exact 54 | ✓ exact 54 | ✓ 54 | Igual C4 estructuralmente |

## Interpretation

1. **F is the best motor-faithful explanation** for the notebook when “Fuerte” means a strengthened T1 candidate.
2. **G explains C2** without needing a new table — but G is **not** the official strengthening rule; it is “emit the T2 pair of an observed number”.
3. **E must not be treated as success** — almost any fuerte that is a neighbor of Leidsa/large groups will hit.
4. No evidence in this sample for H (shared T1 code of the drawn numbers) as the fuerte selector.
5. **Do not add a motor rule from C2 alone.** Collect more notebook cases that look like C2 before proposing a formal relation.

## Missing-relation candidates (evidence-gated)

| Candidate relation | Supported by | Risk |
|--------------------|--------------|------|
| Singleton T2 pair of a same-day number | C2, also C4/C5 | Overfits pairs; many numbers have multi-neighbor groups |
| Rank motor-shaped candidates by #confirmers | C3 (35 has 2 confirmers vs 22) | Needs more multi-candidate days |
| Prefer first-position quiniela only | labeling hygiene | Data quality, not math |

## What was NOT done

- No formula changes
- No hardcoded case tables
- No Production writes
