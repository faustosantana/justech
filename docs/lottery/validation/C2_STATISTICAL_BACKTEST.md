# C2 — Statistical Backtest (DIRECT_T2_NEIGHBOR_SIGNAL)

**Motor modified:** NO  
**Evidence:** `evidence/c2_direct_t2_backtest.json`  
**Split:** discovery `< 2023-01-01` · validation `≥ 2023-01-01`  
**Universe:** FEATURED_SEVEN draws in DEV (27,230 draws after C5 sync context; backtest used featured timeline)

## Protocol (bias controls)

- Activation unit: first number (posición 1) of each featured draw = observed N
- Predictor T2: full Tabla2 neighbor set of N (not cherry-picked)
- Baseline: random set of equal cardinality (`random_same_k`, seed fixed)
- Windows declared a priori: same draw · next draw · same day other · next calendar day · next 7 draws
- Discovery/validation temporal split — no peeking adjustments after seeing validation
- No Production data

## Validation results (primary window: next calendar day)

| Strategy | Precision | Wilson 95% CI | Lift vs random_same_k |
|----------|-----------|---------------|------------------------|
| DIRECT_T2 | 0.3978 | [0.3868, 0.4089] | **1.013** |
| random_same_k | 0.3925 | [0.3816, 0.4036] | 1.0 |

Next-7-draws window: lift **0.988** (T2 slightly worse than random).

## Comparison notes

Official F (same-day strengthened set → hit next calendar day) validation precision ≈ **0.286** on 707 activations.  
Not a head-to-head with T2 (different activation definition: F only fires when a same-day confirmer exists). Reported for context only.

## Verdict

### **A — RECHAZADO**

The direct T2 neighbor pattern does **not** show value above a same-size random draw on the held-out validation period (lift ≈ 1.01; CI overlaps random).

Therefore:

- Keep classification **DIRECT_T2_NEIGHBOR_SIGNAL** for notebook literacy / Lab labeling
- **Do not** promote to secondary validated signal
- **Do not** propose methodology change
- C2 manual “75” remains explained as T2 pair of 62, **not** as official fuerte

## What this means for the five cases

C2 stays useful as a **negative control**: it shows how a notebook “Fuerte” can be a non-official T2 adjacency. The Lab must keep that distinction visible forever.
