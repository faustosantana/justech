# 04 — Árbol de relaciones

Cada activación genera un árbol automático:

```
Motor
 └─ Fuerte F
     ├─ Grupo Tabla 1 (compañeros)
     ├─ Grupo Tabla 2 (vecinos / confirmadores posibles)
     └─ Resultados reales en D+1…D+7
         ├─ dist 0  FUERTE_EXACTO
         ├─ dist 1  COMPANERO_TABLA1
         ├─ dist 3  VECINO_TABLA2
         ├─ dist 4  RELACION_INDIRECTA
         └─ dist 5  SIN_RELACION
```

## Cómo leerlo

El árbol **no** afirma causa. Solo clasifica lo que apareció respecto a F.

Ejemplos narrados: `16_CASE_STUDIES.md`.
Estructura completa por caso: `artifacts/forensic_audit/cases.json` → `tree_summary`.

## Conteos globales (contenidos observados por distancia más cercana)

| Distancia (más cercana) | Activaciones | % |
|-------------------------|-------------:|--:|
| FUERTE_EXACTO | 1670 | 75.16% |
| COMPANERO_TABLA1 | 507 | 22.82% |
| VECINO_TABLA2 | 42 | 1.89% |
| RELACION_INDIRECTA | 2 | 0.09% |
| SIN_RELACION | 1 | 0.05% |

Interpretación: casi todas las activaciones encuentran algo ≤ dist 3 porque la ventana
cubre ~¾ del universo 1..100. Ver baseline en capítulo 01.
