# FASE 1 — Matriz rangos NCF por empresa (DEV baseline)

Fuente: `justech_dev` 2026-07-16. Disponibles = `max(fin - prox + 1, 0)` matemático (no UI forzada).

## JUSTECH S.R.L. (company_id=1)

| Flujo | Tipo | Estado | Ini | Fin | Próx | Disp | % calc | Vigencia | Diario | Obs |
|---|---|---|---:|---:|---:|---:|---:|---|---|---|
| Ventas | B01 | active | 1615 | 1656 | 1615 | 42 | 0 | 2026-07-13→2026-12-31 | (sin) | |
| Ventas | B04 | active | 18 | 100 | 18 | 83 | 0 | →2027-12-31 | (sin) | |
| Ventas | B14 | active | 22 | 39 | 22 | 18 | 0 | →2026-12-31 | (sin) | |
| Ventas | B15 | active | 141 | 144 | 141 | 4 | 0 | →2027-12-31 | (sin) | crítico bajo |
| Compras Emitidos | B11 | active | 11 | 15 | 12 | 4 | 20 | →2027-12-31 | (sin) | |
| Compras Emitidos | B13 | active | 213 | 217 | 213 | 5 | 0 | →2027-12-31 | (sin) | |
| Compras Emitidos | B17 | — | | | | | | | | **sin rango** |
| Compras Recibidos | * | n/a | | | | | | | | fuera de lógica |

## Just Office SRL (company_id=3)

| Flujo | Tipo | Estado | Ini | Fin | Próx | Disp | % | Vigencia | Diario | Obs |
|---|---|---|---:|---:|---:|---:|---:|---|---|---|
| Ventas | B01 | active | 342 | 343 | 342 | 2 | 0 | →2026-12-31 | (sin) | DEV aún no depleteado; incidente Prod fin=400 |
| Ventas | B02 | active | 46 | 100 | 46 | 55 | 0 | →2027-12-31 | (sin) | |
| Ventas | B04 | active | 8 | 1000 | 8 | 993 | 0 | →2027-12-31 | (sin) | |
| Ventas | B15 | active | 4 | 150 | 4 | 147 | 0 | →2026-12-31 | (sin) | |
| Compras Emitidos | B11/B13/B17 | — | | | | | | | | **sin rangos** |

## PlugSafe SRL (company_id=2)

| Flujo | Tipo | Estado | Ini | Fin | Próx | Disp | Vigencia | Obs |
|---|---|---|---:|---:|---:|---:|---|---|
| Ventas | B01 | active | 61 | 78 | 61 | 18 | →2026-12-31 | auth 00000001 |
| Otros | — | | | | | | | solo B01 |

## Omni Solutions SRL (company_id=4)

| Flujo | Tipo | Estado | Ini | Fin | Próx | Disp | Vigencia | Obs |
|---|---|---|---:|---:|---:|---:|---|---|
| Ventas | B01 | active | 36 | 46 | 36 | 11 | →2026-12-31 | |
| Ventas | B14 | active | 3 | 100 | 3 | 98 | →2027-12-31 | auth POR CONFIRMAR |
| Ventas | B15 | active | 107 | 108 | 107 | 2 | →2027-12-31 | crítico bajo |
| Compras Emitidos | — | | | | | | | sin rangos |

## Diferencias reales

- No todas las empresas tienen los mismos tipos.
- Solo JUSTECH tiene Compras Emitidos (B11/B13); ninguna tiene B17 en DEV.
- Ningún rango tiene diarios asociados (`journal_ids` vacío).
- Compras Recibidos no usan estos rangos.

## Responsables / grupos (baseline)

Ver `fase0/fiscal_users.csv` y grupos Usuario Fiscal / Responsable Fiscal / Administrador Fiscal.
