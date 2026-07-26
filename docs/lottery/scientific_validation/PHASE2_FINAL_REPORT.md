# Fase 2 — Informe final de validación científica

**Branch:** `feature/nr-complete-analysis-prediction-engine`  
**Commit base motor:** `054b8f2` + este commit de Fase 2  
**Producción:** **NO modificada**  
**ML decide fuerte:** **NO**

## Objetivo

Medir si el motor reproduce la metodología del socio sobre histórico **ciego** (sin los 5 casos manuales).

## Dataset ciego

| Split | N |
|-------|---|
| train | 1462 |
| validation | 487 |
| test | 488 |

Origen: `artifacts/deep_mathematical_audit/all_activations.csv`  
Excluidos fingerprints manuales M1–M5 (reservados como benchmark final).

## Validación histórica (perfil_socio, n=250 val+test)

| Métrica | Valor |
|---------|-------|
| Methodology match | **94.4%** |
| Fallos | 14 |
| Exact D+1 (si match) | 52 |
| Exact D1–D3 | 117 |
| Exact D1–D7 | 194 |

Limitación: el dataset son activaciones oficiales T1×T2; el match metodológico mide reproducción de geometría, no edge predictivo vs azar.

## Benchmark de variantes

| Variante | Match | D+1 | D1–D3 | D1–D7 | Fallos |
|----------|------:|----:|------:|------:|-------:|
| motor_actual | 0.944 | 52 | 117 | 194 | 14 |
| sin_derivaciones | 0.944 | 52 | 117 | 194 | 14 |
| perfil_socio | 0.944 | 52 | 117 | 194 | 14 |
| perfil_experimental | 0.944 | 52 | 117 | 194 | 14 |
| sin_tabla2 | 0.216 | 11 | 28 | 47 | 196 |
| solo_tabla1 | 0.216 | 11 | 28 | 47 | 196 |

**Conclusión objetiva:** Tabla 2 es indispensable. Las derivaciones no mejoran el match metodológico en este set. Perfiles de peso empatan porque el ranking oficial T1×T2 ya está determinado por evidencia cruzada.

## Calibración

Mejor etiqueta reportada: `perfil_conservador` (empate técnico 0.944 con socio/balanceado/agresivo/experimental).  
**Recomendación:** usar **`perfil_socio` / `manual_reconstruido`** como perfil operativo de metodología (explícito, auditable, alineado al socio). Conservador es equivalente en esta muestra.

## Benchmark manual final (no usado en train)

M1–M5 → **100% match** en socio / motor_actual / sin_derivaciones.

## Errores

14/14 = histórico en alternativas (desempate). Ver `docs/ERROR_ANALYSIS.md`.

## Patrones

Frecuencias origen→fuerte y pares lotería con soporte ≥5 en train (ver `patterns_discovered.json`).  
Hipótesis pendientes: multi-fuerte mismo día; política DIRECT_T2.

## Entregables

1. Benchmark: `artifacts/scientific_validation/benchmark.json` + dashboard  
2. Dashboard: `artifacts/scientific_validation/dashboard.html` y UI `/lottery/scientific-validation`  
3. Inventario: `docs/RULE_INVENTORY.md`  
4. Errores: `docs/ERROR_ANALYSIS.md`  
5. Patrones: `artifacts/scientific_validation/patterns_discovered.json`  
6. Calibración: `artifacts/scientific_validation/calibration_lab.json`  
7. Recomendación perfil: **socio** (empate métrico; claridad metodológica)  
8. Pendientes: R13 desempate multi-fuerte; uso real derivaciones; posiciones 2/3  
9. Evidencia Producción intacta: sin migraciones; branch feature; `production_modified=false`

## Cómo ejecutar

```bash
backend/.venv-prej11a/bin/python scripts/run_scientific_validation_phase2.py --limit 500
# o --full para todo el set ciego
```

## J-11A investigador

Intents: “¿Qué regla falla más?”, “¿Cuál fue la segunda mejor opción?”, “¿Qué patrón nuevo descubriste?”, “¿Mejor perfil?”
