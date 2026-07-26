# 03 — Reconstrucción 21-jun-2026

## FEATURED primeras posiciones (DEV)

| Lotería | Hora | 1er número |
| --- | --- | --- |
| Loteria Nacional | 18:16:31 | 44 |
| Gana Mas | None | 41 |
| New York 10:30 | None | 65 |
| New York 2:30 | None | 39 |
| Quiniela Leidsa | None | 70 |
| Quiniela Loteka | None | 62 |
| Quiniela Real | None | 49 |

## Geometría

Libreta escribe 41+41+70; en FEATURED primeras del 21-jun hay un solo 41 (Gana Más) y 70 (Leidsa). El motor trata números únicos: 41+70→29 igual que 41+41+70.

Oficial 41+70 → [{'fuerte': 29, 'origin': 41, 'confirmers': [70], 'n_confirmers': 1, 'origin_lotteries': ['Gana Mas'], 'confirmer_lotteries': ['Leidsa']}]

Flujo: combinaciones del día = [{'fuerte': 9, 'origin': 39, 'confirmers': [44, 70], 'n_confirmers': 2, 'origin_lotteries': ['New York 2:30'], 'confirmer_lotteries': ['Loteria Nacional', 'Quiniela Leidsa']}, {'fuerte': 29, 'origin': 41, 'confirmers': [44, 70], 'n_confirmers': 2, 'origin_lotteries': ['Gana Mas'], 'confirmer_lotteries': ['Loteria Nacional', 'Quiniela Leidsa']}, {'fuerte': 35, 'origin': 49, 'confirmers': [44, 70], 'n_confirmers': 2, 'origin_lotteries': ['Quiniela Real'], 'confirmer_lotteries': ['Loteria Nacional', 'Quiniela Leidsa']}, {'fuerte': 22, 'origin': 44, 'confirmers': [70], 'n_confirmers': 1, 'origin_lotteries': ['Loteria Nacional'], 'confirmer_lotteries': ['Quiniela Leidsa']}, {'fuerte': 75, 'origin': 44, 'confirmers': [62], 'n_confirmers': 1, 'origin_lotteries': ['Loteria Nacional'], 'confirmer_lotteries': ['Quiniela Loteka']}]  
Estados: ['RESULTADOS_NUEVOS', 'EXPLORACION_T1', 'CONFIRMACION_T2', 'FUERTE_ACTIVO', 'FUERTE_ACTIVO']  
Nuevo pendiente: {'fuerte': 9, 'origin': 39, 'confirmers': [44, 70]}


## Selección parcial

FEATURED primeras del 21-jun producen VARIOS fuertes oficiales: 9, 29, 35, 22, 75. La libreta solo escribe 41+41+70→29. No escribía todas las combos oficiales; enfocaba el par observado 41+70.
