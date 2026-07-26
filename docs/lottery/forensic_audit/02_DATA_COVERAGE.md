# 02 — Cobertura de datos

## Alcance

| Campo | Valor |
|-------|-------|
| Draws totales en DB | 91941 |
| Draws featured cargados | 27230 |
| Fecha mínima featured | 2015-01-02 |
| Fecha máxima featured | 2026-07-23 |
| Análisis desde | 2019-07-23 |
| Análisis hasta (−7d cola) | 2026-07-16 |
| Cobertura pedida | 7 años |
| Cobertura usada | ~7 años (todo lo disponible dentro del objetivo) |

La DB tiene histórico desde **2015-01-02**. Para alinear el pedido de “últimos 7 años”
el análisis comienza en **2019-07-23**.

## Por año

| Año | Desde | Hasta | Días c/ draw | Sorteos |
|-----|-------|-------|-------------:|--------:|
| 2019 | 2019-07-23 | 2019-12-31 | 162 | 1115 |
| 2020 | 2020-01-01 | 2020-12-31 | 366 | 2129 |
| 2021 | 2021-01-01 | 2021-12-31 | 365 | 2487 |
| 2022 | 2022-01-01 | 2022-12-31 | 365 | 2508 |
| 2023 | 2023-01-01 | 2023-12-31 | 365 | 2480 |
| 2024 | 2024-01-01 | 2024-12-31 | 366 | 2511 |
| 2025 | 2025-01-01 | 2025-12-31 | 365 | 2497 |
| 2026 | 2026-01-01 | 2026-07-23 | 203 | 1401 |

## FEATURED_SEVEN

- `Gana Mas`
- `Loteria Nacional`
- `New York 10:30`
- `New York 2:30`
- `Quiniela Leidsa`
- `Quiniela Loteka`
- `Quiniela Real`

## Huecos y calidad

- **Duplicados inventados:** no se fabricaron resultados.
- **Archivadas:** excluidas (`is_featured = true` solamente).
- **Días sin ≥2 observados:** no generan fuerte; no entran al numerador de activaciones.
- **Cola final:** los últimos 7 días del DB no se usan como día de análisis porque
  no tendrían ventana completa de evidencia.
- **Sorteos faltantes:** cualquier día sin draws featured aparece como ausencia en
  `days_with_draws` anual; no se imputan.

Artefacto: `artifacts/forensic_audit/statistics.json`.
