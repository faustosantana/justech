# PHASE PRE-J11A VALIDATION CLOSURE REPORT

## Isolation

| Field | Value |
|-------|--------|
| Branch | `feature/nr-motor-validation-lab` |
| Prior tip | `2b62a48` |
| Production | **intacta** |
| Motor / T1 / T2 | **unmodified** |
| FEATURED_SEVEN | **7** UUIDs intact |
| Methodology | `nr-historical-relations-j1.0.0` |
| DEV draws | 91,927 → **91,941** (+14 Jul 22–23) |

## Work completed

### 1. C2 official treatment

- Classification: **DIRECT_T2_NEIGHBOR_SIGNAL**
- Lab UI + API distinguish **Fuerte oficial** vs **Señal T2 directa**
- C2 display contract: manual 75 · motor sin fuerte 75 · 62→75 · no oficial

### 2. C2 historical backtest

- Script: `backend/scripts/c2_direct_t2_backtest.py`
- Evidence: `evidence/c2_direct_t2_backtest.json`
- Validation lift vs random_same_k (next day): **1.013**
- **Verdict: A — RECHAZADO**

### 3. C5 DEV sync + validation

- Script: `backend/scripts/dev_incremental_sync_c5.py`
- Evidence: `evidence/c5_dev_sync_report.json`
- NY 2:30 2026-07-22 = 35 · Nacional = 14 · Gana Mas 2026-07-23 = **54** (pos 1)
- Lab: **SI_FUERTE_OFICIAL**

### 4. Regression

| Check | Result |
|-------|--------|
| C1–C5 re-run | Prior official geometry unchanged |
| pytest NR + validation lab | **38 passed** |
| Tabla1 companions(35) | `[6,11,43,54,86]` intact |
| FEATURED_SEVEN count | 7 |
| Duplicates on sync | 0 |
| Production | untouched |

## Deliverables

- `C2_DIRECT_T2_SIGNAL_ANALYSIS.md`
- `C2_STATISTICAL_BACKTEST.md`
- `C5_HISTORY_SYNC_VALIDATION.md`
- `MANUAL_CASES_FINAL_DECISION.md`
- This report
- JSON evidence under `evidence/`
- Lab code/UI updates

## Criteria for J-11A

| # | Criterion | Status |
|---|-----------|--------|
| 1 | C2 classified correctly | ✅ |
| 2 | C2 not mixed with official fuerte | ✅ |
| 3 | Historical backtest documented | ✅ |
| 4 | C5 validated with synced history | ✅ |
| 5 | Official methodology intact | ✅ |
| 6 | Regression passed | ✅ |
| 7 | Production intact | ✅ |

## Final verdict

# GO PARA J-11A CON C2 COMO SEÑAL EXPERIMENTAL

Clarifications:

- “Experimental” here means **UI/lab labeling only** after statistical **rejection** as a predictive rule.
- C2 must never be taught to the Agent Runtime as an official strengthening path.
- No deploy. No J-11A start until express authorization.
