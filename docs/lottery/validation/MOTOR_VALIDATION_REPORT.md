# Motor Validation Report

## Objective

Determinar si el Motor NR vigente explica matemáticamente los “Fuerte” manuales, usando únicamente Tabla 1, Tabla 2 e histórico — sin nuevas reglas.

## Official methodology (unchanged)

```
Número observado N
  → compañeros Tabla 1 (candidatos)
  → cada candidato consulta vecinos Tabla 2 (confirmadores)
  → si aparece un confirmador
  → solo el candidato de Tabla 1 se fortalece
```

Version: `nr-historical-relations-j1.0.0`

## What the official `/analyze` API does vs this validation

| | `/analyze` v1 | Validation Lab (this phase) |
|--|---------------|-----------------------------|
| Observed numbers | **One** | Many (same-day set) |
| Ranking | Historical confirmer hits on past occurrences of N | Same-day T1×T2 crosses + evidence weights |
| Mutates motor | — | **No** |

The Lab applies the **same geometric relation** (candidato T1 + confirmador T2) to a multi-lottery same-day observation set. That is the natural reading of the manual notebooks.

## Results summary

| Caso | Manual | Motor-shaped (F) | ¿Explica? |
|------|--------|------------------|-----------|
| C1 | 29 | 29 | **SÍ — exacto** |
| C2 | 75 | — | **NO (forma-motor)**; sí vía par T2 de 62 |
| C3 | 35 | 22 y 35 | **SÍ — con otro candidato** |
| C4 | 54 | 54 | **SÍ — exacto** + histórico día+1 |
| C5 | 54 | 54 | **SÍ — exacto estructural**; histórico Jul ausente en DEV |

### Scorecard

- Exact motor-shaped singleton: **3/5** (C1, C4, C5)
- Motor-shaped recovers manual (incl. non-unique): **4/5** (C1, C3, C4, C5)
- Full miss of motor-shaped: **1/5** (C2)

## Detailed explanations (when match)

### C1 — 29

```
N=41 → T1 companions {13,29,93}
candidate 29 → T2 neighbors include 70
same-day confirmer = Leidsa 70
→ strengthens 29 only
```

### C4 / C5 — 54

```
N=35 → T1 companions {6,11,43,54,86}
candidate 54 → T2 neighbors {14}
same-day confirmer = 14
→ strengthens 54 only
```

### C3 — 35 (non-unique)

```
N=49 → T1 companions {35,40,83}
candidate 35 → neighbors include 44 and 70
both appear same day → 35 strengthened
also: candidate 22 is strengthened by the same geometry → set {22,35}
```

## Detailed divergence (C2)

```
Manual Fuerte = 75
Motor-shaped F produced = []
Evidence used by motor-shaped:
  companions(41) = {13,29,93}
  companions(62) = ∅
  neighbors(13/29/93) do not contain 62
  therefore no candidate of 41 is confirmed by 62

Relation that does produce 75:
  neighbors(62) = {75}  (singleton T2 pair)
```

**Hypothesis:** the manual notebook for C2 may have treated Loteka’s T2 pair as the “Fuerte”, not a T1 candidate of Nacional/GM 41. That is a **different relation** than the official strengthening rule.

## DB integrity notes (not methodology failures)

1. On 2026-06-21, Lotería Nacional first number is **44**, not 41. Manual C1/C2 label “Nacional=41” does not match DEV; GM first number is 41.
2. DEV history ends **2026-07-21** — Case 5 calendar verification impossible until sync catches up.
3. Draw count remained 91,927; featured seven untouched.

## Verdict for methodology

The official T1-candidate × T2-confirmer geometry **reproduces 4 of 5 manual Fuertes** when applied to the stated same-day observation sets (3 exact singletons + 1 multi-candidate).

**Case 2 is the structural miss** under the official rule. Before J-11A, decide whether:

1. C2 was a notebook use of the T2-pair shortcut (document as non-motor), or  
2. A missing mathematical relation must be researched further **with more cases** (do not patch the motor from one case).

## Artifacts

- Lab module: `backend/app/lottery/numeric_relations/validation_lab.py`
- API: `POST /api/v1/lottery/admin/numeric-relations/validation-lab`
- UI: `/lottery/admin/control-center/motor/validation-lab`
- Runner: `backend/scripts/nr_manual_cases_validation.py`
- Evidence JSON: `docs/lottery/validation/evidence/`
