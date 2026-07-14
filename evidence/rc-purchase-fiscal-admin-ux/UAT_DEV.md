# UAT DEV — RC-PURCHASE-FISCAL-ADMIN-UX

Fecha: 2026-07-14  
BD: `justech_dev`  
Servicio: `odoo-dev`  
Resultado: **PASS 39 / FAIL 0**

## Módulos
- `justech_l10n_do_base` 19.0.1.25.0
- `justech_l10n_do_ncf` 19.0.2.9.0
- `justech_fiscal_admin` 19.0.1.8.5

## Integridad
| Métrica | Antes | Después |
|---|---|---|
| GL | 0.00 | 0.00 |
| in | 783 | 783 |
| pay | 699 | 699 |
| am | 2407 | 2407 |
| aml | 9033 | 9033 |
| B11 next | 11 | 11 |
| B13 next | 213 | 213 |
| ranges | 14 | 14 |
| B17 ficticios | 0 | 0 |

## Casos
- Costos/gastos distintos mismo proveedor: PASS
- Selección manual persiste: PASS
- E31 + 606 code: PASS
- B11 preview/post rollback (sin consumo neto): PASS
- B17 bloqueado sin rango: PASS
- Menús Compras + catálogo 11 códigos: PASS
- Multiempresa configs 4×3: PASS

Producción: **no modificada**.
