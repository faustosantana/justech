# 01 — Resumen ejecutivo

Esta auditoría reconstruye, con datos históricos exactos, **qué ocurrió después de cada activación oficial** del motor: posiciones en Tabla 1/2, distancias, cadenas, loterías y plazos D+1…D+7.

No clasifica el trabajo como “el motor acierta” o “falla”.
No usa comparaciones aleatorias como eje.
No modifica fórmulas ni Producción.

## Volumen

| Métrica | Valor |
|---------|------:|
| Activaciones cadena O→F←C | 2477 |
| Activaciones fuerte (únicas/día) | 2222 |
| Fuertes distintos | 84 |
| Filas de apariciones posteriores | 351227 |
| Días con ≥2 observados | 2549 |
| Días con ≥1 fuerte | 1333 |

## Primera aparición del fuerte exacto

| Día | Primera aparición | % activaciones |
| --- | --- | --- |
| D+1 | 400 | 18.0 |
| D+2 | 335 | 15.08 |
| D+3 | 287 | 12.92 |
| D+4 | 206 | 9.27 |
| D+5 | 175 | 7.88 |
| D+6 | 147 | 6.62 |
| D+7 | 120 | 5.4 |

![exact by day](assets/exact_by_day.svg)

### Acumulado

| Ventana | Conteo | % activaciones |
| --- | --- | --- |
| D+1 | 400 | 18.0 |
| D+1–D+2 | 735 | 33.08 |
| D+1–D+3 | 1022 | 45.99 |
| D+1–D+4 | 1228 | 55.27 |
| D+1–D+5 | 1403 | 63.14 |
| D+1–D+6 | 1550 | 69.76 |
| D+1–D+7 | 1670 | 75.16 |

## Distancias posicionales T1 más frecuentes

| Distancia | Conteo | % |
| --- | --- | --- |
| 0 | 3483 | 21.17% |
| -1 | 2521 | 15.32% |
| 1 | 2194 | 13.33% |
| -2 | 1932 | 11.74% |
| 2 | 1649 | 10.02% |
| 3 | 1098 | 6.67% |
| -3 | 984 | 5.98% |
| 4 | 774 | 4.7% |
| -4 | 619 | 3.76% |
| 5 | 363 | 2.21% |
| 6 | 312 | 1.9% |
| -5 | 229 | 1.39% |
| 7 | 130 | 0.79% |
| -6 | 125 | 0.76% |
| -7 | 40 | 0.24% |

![t1 dist](assets/t1_distances.svg)

## Etiquetas de relación más frecuentes (nivel aparición)

| Etiqueta | Conteo |
| --- | --- |
| SIN_RELACION_DIRECTA_IDENTIFICADA | 105300 |
| RELACION_DE_TERCER_NIVEL | 104696 |
| RELACION_DE_SEGUNDO_NIVEL | 74843 |
| CANDIDATO_ORIGINAL_ALTERNATIVO | 32161 |
| MISMO_GRUPO_T2 | 23765 |
| MISMO_CODIGO_T2 | 23765 |
| VECINO_DEL_CONFIRMADOR | 20198 |
| MISMO_GRUPO_T1 | 16453 |
| MISMO_CODIGO_T1 | 16453 |
| COMPANERO_DEL_CONFIRMADOR | 12945 |
| POSICION_T1_CERCANA | 5663 |
| POSICION_T2_ADYACENTE | 5535 |
| POSICION_T1_ADYACENTE | 4715 |
| FUERTE_ALTERNATIVO | 4261 |
| CONFIRMADOR_ORIGINAL | 3567 |
| FUERTE_EXACTO | 3483 |
| POSICION_T1_LEJANA | 2592 |

## Lectura

1. El fuerte exacto tiene una trayectoria temporal medible por D+n (capítulo 06/15).
2. Cuando no es exacto, las apariciones posteriores se clasifican por **posición y distancia** en T1/T2, no solo como “compañero”.
3. Las cadenas O→F←C→R más repetidas están rankeadas con niveles de consistencia (capítulo 10/23).

Detalle: [30_FINAL_REPORT.md](30_FINAL_REPORT.md).
