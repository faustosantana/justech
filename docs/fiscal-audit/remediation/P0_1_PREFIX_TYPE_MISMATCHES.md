# P0.1 — Inventario prefijo ≠ tipo (históricos DEV)

**Fuente:** SQL DEV 2026-07-17 — `evidence/fiscal-audit/remediation/P0_1/SQL/prefix_mismatches_20.txt`  
**Cantidad:** 19 filas (auditoría previa reportó ~20; 1 diferencia por normalización de mayúsculas).  
**Modificados en P0.1:** **0**

| ID | Co | Tipo | Doc | Fecha | Tipo LATAM | Prefijo tipo | NCF | Prefijo NCF | Clasificación | Causa probable |
|---|---|---|---|---|---|---|---|---|---|---|
| 1338 | 1 | out | CxC/2024/00008 | 2024-06-10 | B01 Crédito Fiscal | B01 | PROFORMA14 | PRO | compatibilidad legacy / migración | Diario Migración CxC |
| 1436 | 1 | in | FP/2026/03/0026 | 2026-03-09 | B15 Gubernamental | B15 | E310000046397 | E31 | inconsistencia real | tipo B15 vs e-CF E31 |
| 1537 | 1 | out | FC/2026/00083 | 2026-01-02 | B01 | B01 | B1400000018 | B14 | inconsistencia real | tipo B01 vs NCF B14 |
| 3787 | 1 | in | FP/2026/07/0003 | 2026-07-16 | E31 | E31 | b0190290121 | B01 | inconsistencia real | case + prefijo B01 vs E31 |
| 2318–2484,2902 | 3 | out | INV/* | 2025–2026 | B01 | B01 | B02… / B16… | B02/B16 | inconsistencia real | series consumidor/especial tipadas B01 |
| 3540 | 3 | in | FACTU/2026/06/0005 | 2026-06-01 | B15 | B15 | E310000008337 | E31 | inconsistencia real | B15 vs E31 |

## Plan de saneamiento (NO en este paquete)

1. Clasificar por humano contable/fiscal cada fila.
2. Corregir tipo **o** NCF según documento soporte (nunca ambos a ciegas).
3. Re-exportar períodos DGII afectados si ya enviados.
4. UAT por compañía + backup antes de tocar Prod.

## Gate futuros

Nuevos documentos con esta inconsistencia **no publican** tras P0.1.
