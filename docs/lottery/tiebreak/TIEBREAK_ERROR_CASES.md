# Auditoría de los 14 errores (HIST_FUERTE_IN_ALTERNATIVES)

Fuente estructurada: `artifacts/tiebreak/error_cases.json`.

## Conclusión de auditoría

Los 14 fallos de Fase 2 **no son errores de descubrimiento**.  
En todos, el fuerte histórico estaba entre las alternativas (rank 2).  
La causa dominante es **empate real de score** (`score_gap = 0`) más un desempate lexicográfico previo (número menor gana).

### Subtipos

1. **Par estructural idéntico** (ej. 22 vs 70 desde 44←T1 / 63←T2): misma evidencia T1×T2 → no existe desempate honesto → debe quedar `EMPATE_MULTI_FUERTE`.
2. **Intercambio de roles** (origen como T2 en el elegido, como T1 en el histórico): corregible con orden generator-first + preferencia de la primera observación como fuente T1 (`TIEBREAK_PROFILE_SOCIO` / `TIEBREAK_SOURCE_ORDER`).

## Campos auditados por caso

fecha, loterías, posiciones, números observados (sorted y generator-first), candidato motor Fase 2, histórico, rank del histórico, gap de score, empate real, relaciones T1/T2 de ambos, rutas independientes/duplicadas, profundidad implícita vía paths, componentes de score, alternativas.

## Política

Esta auditoría **no corrige** los casos; solo documenta.  
La corrección (cuando es posible) ocurre vía Tiebreak Engine + política multi-fuerte.
