# 17 — Resultados estadísticos

## Totales

| Métrica | Valor |
|---------|------:|
| Activaciones | 2222 |
| Exact hits | 1670 (75.16%) |
| Misses | 552 (24.84%) |
| Familia (exacto∪compañero) | 97.97% |
| Lift exacto vs azar | 1.0018 |
| Lift familia vs azar | 1.0032 |

## Ranking cuando NO sale el fuerte

| Bucket | n | % misses |
|--------|--:|---------:|
| COMPANERO_TABLA1 | 507 | 91.85% |
| VECINO_TABLA2 | 42 | 7.61% |
| MISMO_CODIGO_T1 | 0 | 0.0% |
| RELACION_INDIRECTA | 2 | 0.36% |
| SIN_RELACION | 1 | 0.18% |

## Por número (top 25 por veces fuerte)

| Número | Veces fuerte | Exactos | Tasa | Miss→compañero | Miss→vecino | Miss→nada |
|-------:|-------------:|--------:|-----:|---------------:|------------:|----------:|
| 42 | 85 | 69 | 81.18% | 14 | 2 | 0 |
| 9 | 81 | 61 | 75.31% | 20 | 0 | 0 |
| 44 | 81 | 56 | 69.14% | 25 | 0 | 0 |
| 7 | 79 | 60 | 75.95% | 19 | 0 | 0 |
| 29 | 79 | 58 | 73.42% | 19 | 2 | 0 |
| 70 | 76 | 57 | 75.0% | 19 | 0 | 0 |
| 22 | 75 | 48 | 64.0% | 27 | 0 | 0 |
| 63 | 75 | 56 | 74.67% | 19 | 0 | 0 |
| 53 | 72 | 49 | 68.06% | 22 | 1 | 0 |
| 35 | 66 | 52 | 78.79% | 14 | 0 | 0 |
| 90 | 65 | 49 | 75.38% | 16 | 0 | 0 |
| 71 | 43 | 35 | 81.4% | 8 | 0 | 0 |
| 28 | 41 | 35 | 85.37% | 6 | 0 | 0 |
| 77 | 41 | 28 | 68.29% | 0 | 13 | 0 |
| 56 | 38 | 26 | 68.42% | 12 | 0 | 0 |
| 87 | 38 | 34 | 89.47% | 4 | 0 | 0 |
| 23 | 37 | 28 | 75.68% | 9 | 0 | 0 |
| 27 | 36 | 27 | 75.0% | 7 | 2 | 0 |
| 73 | 35 | 26 | 74.29% | 7 | 2 | 0 |
| 89 | 33 | 24 | 72.73% | 6 | 3 | 0 |
| 69 | 32 | 23 | 71.88% | 5 | 4 | 0 |
| 92 | 32 | 29 | 90.62% | 3 | 0 | 0 |
| 94 | 32 | 25 | 78.12% | 7 | 0 | 0 |
| 26 | 31 | 22 | 70.97% | 9 | 0 | 0 |
| 41 | 31 | 24 | 77.42% | 7 | 0 | 0 |

CSV completo: `artifacts/forensic_audit/by_number.csv`  
Outcomes: `artifacts/forensic_audit/outcomes_summary.csv`  
JSON: `artifacts/forensic_audit/statistics.json`
