# Matriz de diferencias — histórico vs elegido

Artefactos:

- `artifacts/tiebreak/feature_matrix.json`
- `artifacts/tiebreak/feature_matrix.csv`

## Qué compara

Para cada uno de los 14 errores: candidato histórico correcto vs candidato incorrectamente elegido por el motor Fase 2.

## Hallazgos principales

| Señal | Observación |
|-------|-------------|
| `score_gap` | 0.0 en todos (empate real) |
| `diff_t1_sources` / `diff_t2_confirmers` | 0 en la mayoría — misma estructura |
| `both_cross_table` | true en casos tipados |
| `hist_has_origin_as_t1` vs `chosen_has_origin_as_t1` | Distingue el subtipo role-swap |
| `competitors_tied` | ≥2 cuando hay empate real |

## Implicación

Las hipótesis basadas solo en “más T1 / más T2 / más rutas” **no separan** el subtipo estructural idéntico.  
El desempate útil es: (a) preferencia generator-first cuando hay asimetría de roles; (b) declarar multi-fuerte cuando las claves socio son iguales.
