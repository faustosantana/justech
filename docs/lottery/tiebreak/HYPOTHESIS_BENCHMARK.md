# Benchmark de hipótesis de desempate

Artefacto: `artifacts/tiebreak/hypothesis_results.json`  
Resumen final: `artifacts/tiebreak/final_benchmark.json`

## Protocolo anti-overfitting

| Split | Uso |
|-------|-----|
| train | exploración |
| validation | **selección** de regla |
| test | evaluación final **después** de seleccionar |

`test_used_for_selection = false` en el artefacto final.

## Hipótesis evaluadas (separadas)

1. `TIEBREAK_MORE_INDEPENDENT_SOURCES`
2. `TIEBREAK_STRONGER_CROSS_TABLE`
3. `TIEBREAK_MORE_DIRECT_T2_CONFIRMERS`
4. `TIEBREAK_MORE_DIRECT_T1_SOURCES`
5. `TIEBREAK_LOWER_DEPTH`
6. `TIEBREAK_FEWER_DUPLICATE_PATHS`
7. `TIEBREAK_FIRST_POSITION_SUPPORT`
8. `TIEBREAK_SHORT_WINDOW_HISTORY`
9. `TIEBREAK_EXACT_HISTORY`
10. `TIEBREAK_RECENT_EQUIVALENT_CASES`
11. `TIEBREAK_SOURCE_ORDER`
12. `TIEBREAK_REPEATED_INPUT`
13. `TIEBREAK_PROFILE_SOCIO`
14. `TIEBREAK_PROFILE_SOCIO_MULTI` (misma regla + `EMPATE_MULTI_FUERTE`)

## Criterio de selección

Maximizar en validation: `top2_rate`, luego `top1_rate`.  
No aceptar una regla solo porque corrija los 14 errores.

## Umbral práctico

Se probaron umbrales conceptuales; los 14 errores son empates exactos → umbral operativo `0.0` (configurable).
