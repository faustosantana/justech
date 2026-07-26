# C2 — DIRECT_T2_NEIGHBOR_SIGNAL

## Classification (official)

**DIRECT_T2_NEIGHBOR_SIGNAL**

Not:

- candidato fortalecido
- fuerte oficial
- confirmación oficial
- equivalente a geometría T1 × T2

## Case facts

| Field | Value |
|-------|--------|
| Date (manual) | 2026-06-21 |
| Observations (manual) | Nacional=41, Loteka=62 |
| Manual result | **75** |
| Official F (T1×T2) | ∅ — 75 not strengthened |
| Relation found | **62 → Tabla2 direct neighbor → 75** |

## Geometry contrast

```
OFICIAL:
  N → compañeros T1 (candidatos) → vecinos T2 del candidato → confirmador
  → fortalece SOLO el candidato T1

C2 (secundaria):
  N_obs=62 → vecinos T2 directos = {75}
  75 ∉ compañeros T1 de 41
  62 no confirma ningún candidato de 41
```

## Application representation

Validation Lab must show:

| Panel | Content for C2 |
|-------|----------------|
| Fuerte oficial | Sin candidato fortalecido 75 |
| Señal T2 directa | 62 → 75 |
| Estado | Señal T2 directa, no fuerte oficial |

## Policy

Do **not** fold this pattern into methodology `nr-historical-relations-j1.0.0` without a separate authorized phase.

See `C2_STATISTICAL_BACKTEST.md` for historical measurement and verdict A/B/C/D.
