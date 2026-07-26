# 11 — Distancias matemáticas

## Escala

| d | Etiqueta |
|--:|----------|
| 0 | Fuerte exacto |
| 1 | Compañero Tabla 1 |
| 2 | Mismo código T1 |
| 3 | Vecino Tabla 2 |
| 4 | Relación indirecta |
| 5 | Sin relación |

## Distribución (distancia más cercana por activación)

| Etiqueta | Activaciones | % |
|----------|-------------:|--:|
| FUERTE_EXACTO | 1670 | 75.16% |
| COMPANERO_TABLA1 | 507 | 22.82% |
| VECINO_TABLA2 | 42 | 1.89% |
| RELACION_INDIRECTA | 2 | 0.09% |
| SIN_RELACION | 1 | 0.05% |

## Lectura

- Distancia 0 domina (~75.16%).
- Distancia 1 absorbe casi todos los misses.
- Distancia 5 es casi inexistente (**0.18%** de misses):
  con mediana ~76 números únicos en la ventana,
  “no tocar la familia” es raro.

La métrica de distancia es útil para **clasificar**; no implica por sí sola ventaja predictiva.
