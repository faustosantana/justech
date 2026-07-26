# ERROR ANALYSIS — Catálogo de fallos (Fase 2)

**Branch:** `feature/nr-complete-analysis-prediction-engine`  
**Fuente:** `artifacts/scientific_validation/error_analysis.json`  
**Política:** Solo documentar. **No** autocorregir el motor.

## Resumen (run limit=250 sobre val+test ciego)

| Métrica | Valor |
|---------|-------|
| Análisis | 250 |
| Fallos metodológicos | 14 |
| Failure rate | 5.6% |
| Match rate | 94.4% |

## Patrón repetitivo dominante

**HIST_FUERTE_IN_ALTERNATIVES (14/14 fallos)**

El motor eligió un fuerte distinto al histórico oficial, pero el fuerte histórico **sí apareció en el ranking como alternativa**.

Interpretación:

- No es un fallo de “no descubrió la relación”.
- Es un fallo de **desempate / ranking entre varios candidatos T1×T2 válidos**.
- Coincide con la hipótesis R13 (selección parcial multi-fuerte).

## Estructura típica de un fallo

Para cada caso fallido el catálogo registra:

- números observados;
- número elegido por el motor y por qué (score, T1 sources, T2 confirmers);
- fuerte histórico;
- rank del histórico en el motor;
- flags de evidencia faltante;
- loterías origen/confirmador.

Ejemplo de lectura:

1. ¿Por qué eligió ese número? → mayor score bajo perfil socio tras cruce T1×T2.  
2. ¿Cuál terminó saliendo (histórico oficial)? → otro candidato también confirmado.  
3. ¿Qué evidencia faltó? → no faltó descubrimiento; faltó regla de desempate alineada al socio.  
4. ¿Rutas ignoradas? → no; el histórico estaba rankeado pero no primero.

## Qué NO se hizo

- No se cambiaron pesos automáticamente.
- No se hardcodearon casos.
- No se modificó Producción.
- No se alteraron fórmulas Tabla 1/2.

## Próximos pasos sugeridos (hipótesis, no implementadas)

1. Formalizar desempate por `n_confirmers` / lotería / posición cuando hay varios oficiales.  
2. Estudiar días con `n_fuertes_same_day > 1` del CSV de activaciones.  
3. Medir si el fuerte histórico fallido era el que el socio anotó o un oficial paralelo.
