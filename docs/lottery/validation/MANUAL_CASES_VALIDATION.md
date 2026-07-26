# Manual Cases Validation

**Branch:** `feature/nr-motor-validation-lab`  
**Motor modified:** NO  
**Tables modified:** NO  
**Production:** intact  
**Methodology reference:** `nr-historical-relations-j1.0.0`  
**DEV draws counted:** 91,927 (max `draw_date` = 2026-07-21)

These cases were used only as external oracles. They were not encoded as rules.

## Case matrix

| Caso | Fecha | Observados (manual) | Fuerte manual | Forma-motor F | Coincidencia lab | Evidencia DB |
|------|-------|---------------------|---------------|---------------|------------------|--------------|
| C1 | 2026-06-21 | GM=41, Nacional=41, Leidsa=70 | **29** | **29** (exact) | SI | GM=41✓ Leidsa=70✓; **Nacional DB=44 ≠ 41** |
| C2 | 2026-06-21 | Nacional=41, Loteka=62 | **75** | ∅ | PARCIAL (solo T2 de 62) | Loteka=62✓; **Nacional DB=44 ≠ 41** |
| C3 | 2026-06-21 | Real=49, Nacional=44, Leidsa=70 | **35** | {22, **35**} | SI_CON_OTROS_CANDIDATOS | Los tres coinciden con DB |
| C4 | 2026-06-23 | Nacional=35, Loteka=14 | **54** | **54** (exact) | SI | Ambos✓; día siguiente 54 en Loteka✓ |
| C5 | 2026-07-22 | NY Día=35, Nacional=14 | **54** | **54** (exact) | SI (estructural) | **Sin sorteos en DEV** (max 2026-07-21); no se pudo verificar GM=54 al día siguiente |

## Per-case technical notes

### Caso 1 — Fuerte 29

- Compañeros T1 de 41: `[13, 29, 93]`
- Vecinos T2 de 70 incluyen `29`
- Forma-motor: observado **41** → candidato **29** → confirmador **70** ∈ vecinos(29)
- Relación exacta y única bajo hipótesis F/A

### Caso 2 — Fuerte 75

- Forma-motor F **no** produce 75 a partir de {41, 62}
- 62 tiene un único vecino T2: **75** (hipótesis G singleton)
- 75 ∉ compañeros(41)
- Divergencia: el “Fuerte” manual coincide con el **par T2 de Loteka=62**, no con un candidato T1 de 41 confirmado por 62

### Caso 3 — Fuerte 35

- Forma-motor F produce **[22, 35]**
- Detalle para 35: observado 49 → candidato 35 → confirmadores {44, 70}
- El manual elige 35; el motor-shaped también lo obtiene, pero no como singleton

### Caso 4 — Fuerte 54

- Compañeros T1 de 35: `[6, 11, 43, 54, 86]`
- Vecinos T2 de 14: `[54]`
- Forma-motor: 35 → candidato 54 → confirmador 14
- Histórico: 2026-06-24 Loteka = `[54, 69, 13]`

### Caso 5 — Fuerte 54

- Misma geometría estructural que C4 (35×14→54)
- Histórico Jul-22/23 **ausente** en DEV — verificación de aparición en Gana Más: **no disponible** aquí

## Evidence files

`docs/lottery/validation/evidence/C1.json` … `C5.json`, `summary.json`
