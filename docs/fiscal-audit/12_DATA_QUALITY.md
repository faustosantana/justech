# 12 — Calidad de datos (solo lectura)

## Controles verdes

- Rangos: 0 solapes, 0 next fuera, 0 active+agotado/vencido math.
- Duplicados venta reales: 0.
- Duplicados compra+proveedor: 0.
- GL diff: 0.
- Mail NCF: 0.

## Anomalías

| Métrica | Valor | Severidad |
|---|---|---|
| Posted sin Justech document type | 1539 | CRÍTICO/estructural (dual stack) |
| Prefijo ≠ tipo LATAM | 20 | ALTO |
| NCF lowercase | 2 | MEDIO |
| Naive duplicates company+NCF | 9 pares | **Descartado** (v2.0) |
| `justech_do_ncf` poblado | 1 | informativo |

## Muestras prefijo mismatch

Incluyen: `PROFORMA14` como B01; series B02/B14/B16 tipadas como B01; E31 tipado B15; lowercase b01…

Evidencia: `evidence/fiscal-audit/SQL/duplicates_scoped.txt`, `ncf_latam_stats.txt`.

## No se limpió ningún registro.
