# RC-PURCHASE-FISCAL-IMPLEMENTATION — DEV

## Versiones
- `justech_l10n_do_base` → **19.0.1.24.0**
- `justech_l10n_do_ncf` → **19.0.2.8.0**

## Entregables código
- Modelo `justech.do.purchase.emission.config` (B11/B13/B17 × empresa; `emission_enabled` solo con rango activo).
- Campo `justech_do_purchase_registration_mode` en `account.move` (`received` | `issued`).
- UX Compras: radio + LATAM dominio recibidos vs Justech solo purchase docs.
- Assignment: recibidos no consumen; emitidos bloquean sin rango con mensaje nominativo.
- Post-migrate: configs 4×3 sin rangos ficticios; modo `received` en históricos null.
- Tests: `test_purchase_registration_mode.py`.

## Continuidad preservada (no tocar)
- JUSTECH B11 next **11** / B13 next **213** — no recalcular.
- B17 y empresas sin rango: config inactiva.

## Producción
- **No desplegado / no modificado.**
