# Consistencia tipo ↔ NCF recibido

## Controles
1. Publicación compras recibidas: bloqueo si prefijo tipo ≠ prefijo NCF.
2. Exportador 606: documento incompleto / no exportable; NCF no se reescribe.

## Inventario (solo lectura / sin modificación histórica)
- DEV: 3 inconsistencias (`inventory/inventory_dev.csv`)
- Prod: 2 inconsistencias (`inventory/inventory_prod_readonly.csv`)

## Caso prueba FP/2026/07/0003
E31 + B0190290121 — no válido como E31; 606 lo marca inconsistente.

## Rollback
Restaurar módulos desde backup previo y `-u justech_l10n_do_base,justech_l10n_do_ncf,justech_l10n_do_reports`.
