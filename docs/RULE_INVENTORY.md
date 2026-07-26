# RULE INVENTORY — Motor de Relaciones Numéricas (Fase 2)

**Branch:** `feature/nr-complete-analysis-prediction-engine`  
**Scope:** Inventario de reglas *implementadas* (no nuevas fórmulas).  
**Producción:** no modificada.

Clasificación:

| Código | Significado |
|--------|-------------|
| confirmada_por_evidencia | Respaldada por tests y/o match metodológico histórico |
| inferida | Observada en casos/reconstrucción; aún no formalizada como axioma |
| hipotesis | Plausible, sin evidencia suficiente para adoptar |
| regla_pendiente_de_validacion | Implementada o propuesta; métricas pendientes o mixtas |

## Reglas

Ver también `artifacts/scientific_validation/rule_inventory.json` (generado por el pipeline).

1. **R01_FULL_GRAPH_BEFORE_DISCOVERY** — confirmada_por_evidencia  
   Analizar todo el grafo antes de descubrir/rankear candidatos.

2. **R02_T1_MOTHER_COMPANIONS** — confirmada_por_evidencia  
   Tabla 1: observado como código madre → compañeros.

3. **R03_T2_CONFIRMATION** — confirmada_por_evidencia  
   Tabla 2: confirmador ∈ vecinos T2 del candidato.

4. **R04_NO_EARLY_GREEDY** — confirmada_por_evidencia  
   Prohibido detenerse en el primer match.

5. **R05_COMPANION_NEIGHBOR_SEPARATION** — confirmada_por_evidencia  
   COMPAÑERO_T1 ≠ VECINO_T2.

6. **R06_FUERTE_REQUIRES_T1xT2_STRICT** — confirmada_por_evidencia  
   Perfiles socio/estricto: fuerte oficial requiere T1+T2.

7. **R07_DIRECT_T2_SEPARATE** — confirmada_por_evidencia  
   VECINO_T2_DIRECTO separado (p.ej. 41+62→75).

8. **R08_T2_GROUP_SPECIFICITY** — inferida  
   Preferir grupos T2 más pequeños entre directos T2.

9. **R09_DERIVATION_DEPTH_CAP** — regla_pendiente_de_validacion  
   Derivaciones ≤2; aporte vs ablación `sin_derivaciones` se mide en benchmark.

10. **R10_MULTI_CONFIRMER_BOOST** — inferida  
    Más confirmadores T2 → mayor score (caso M3).

11. **R11_DEFAULT_FIRST_POSITION** — confirmada_por_evidencia  

12. **R12_SAME_DAY_CHAIN** — inferida  
    Flujo operativo de cierre + nuevo análisis.

13. **R13_PARTIAL_SELECTION_MULTI_FUERTE** — hipotesis  
    Selección parcial cuando hay varios oficiales el mismo día.

14. **R14_WEIGHT_PROFILE_SOCIO** — regla_pendiente_de_validacion  
    Completada tras calibration lab (ver recomendación en informe).

15. **R15_NO_ML_FOR_FUERTE** — confirmada_por_evidencia  
    ML no decide el fuerte.

## Pendientes de descubrir

- Desempate multi-fuerte mismo día  
- Política posiciones 2/3  
- Uso real de derivaciones en análisis manuales  
- Cadenas F→siguiente más allá del cierre simple  

## Cómo regenerar

```bash
backend/.venv-prej11a/bin/python scripts/run_scientific_validation_phase2.py --limit 500
```
