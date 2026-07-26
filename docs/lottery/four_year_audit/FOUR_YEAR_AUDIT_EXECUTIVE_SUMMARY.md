# Resumen ejecutivo — Auditoría 4 años / 7 loterías

**Aviso:** frecuencias históricas e intervalos. No es garantía predictiva.

## Qué se analizó

Período real **2022-07-26 → 2026-07-23** sobre las **7** loterías FEATURED_SEVEN.
Fechas con ≥2 observados: **1457**.
Días con fuerte oficial: **795**.

## Qué se encontró

- Hit rate día siguiente (W3): **226/794 = 0.284635**
- IC95: **[0.254343, 0.317001]**
- Lift vs random same-k: **1.066**
- Lift vs random one: **1.4868**
- Diferencia absoluta vs random same-k: **0.017632**

## Qué significa

La geometría T1×T2 reproduce la lógica manual. El lift frente a una selección aleatoria con la **misma cantidad de candidatos** está **cerca de 1** (1.066). Eso indica **sin ventaja estadística suficiente** para uso predictivo.

## Qué tan confiable

Veredicto matemático: **GEOMETRIA_CORRECTA**  
Veredicto estadístico: **SIN_VENTAJA**  
Lift cerca de 1: **True**

## Limitaciones

- Unidad = primeros números in-universe por lotería/día (no todas las posiciones).
- Ventana W2 (mismo día) es estructuralmente vacía en esa unidad.
- Múltiples relaciones → riesgo de falsos descubrimientos; se usan umbrales de muestra.

## Decisión

- GO_PARA_J11A_SOLO_COMO_COPILOTO_ANALITICO
- NO_GO_PARA_J11A_PREDICTIVO

No se inicia J-11A automáticamente.
