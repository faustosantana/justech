# 05 — Auditoría NCF (solo lectura)

## Tipos / rangos DEV

14 rangos activos (B01/B02/B04/B11/B13/B14/B15) en 4 compañías.  
Sin solapes. Sin next fuera de bounds. Sin active+agotado matemático.

Umbrales compañía: preventivo 20, crítico 5, expiry 15 (las 4).

## Almacenamiento real del NCF

| Campo | Posted invoices/refunds con valor |
|---|---|
| `l10n_latam_document_number` | **1540** |
| `justech_do_ncf` | **1** |
| Ambos distintos | **0** |

Conclusión: **fuente operativa = LATAM/Adel**, Justech field residual.

## Unicidad (alcance v2.0)

| Prueba | Resultado |
|---|---|
| Mismo company+NCF en dos ventas | **0** |
| Mismo company+partner+NCF en dos compras | **0** |
| Mismo company+NCF venta+compra | Esperado / no es corrupción |

Naive `GROUP BY company_id, ncf` marca 9 pares — **descartado como FISC-AUD-X01 falso positivo**.

## Consistencia prefijo ↔ tipo

**20** documentos posted con `left(NCF) ≠ doc_code_prefix` (LATAM).  
Muestras: B02 bajo tipo B01; `PROFORMA14`; E31 bajo B15; NCF lowercase `b0190290121` bajo E31.

→ **FISC-AUD-002 ALTO**.

## Formato

2 NCF con minúsculas. Resto pasa regex flexible.  
Validadores Justech existen; no aplicados uniformemente al stack LATAM.

## Consumo / borrador

Conteo NCF por state: solo `posted` tiene NCF en `justech_do_ncf` (1). LATAM numbers predominantemente en posted.

## Alertas (baseline)

Cron `Justech NCF: alertas internas consolidadas` activo.  
Open activities NCF: 0. Mail NCF: 0.  
**No modificado.**

## Evidencia

`evidence/fiscal-audit/SQL/ncf_latam_stats.txt`, `duplicates_scoped.txt`, `data_quality_audit.txt`.
