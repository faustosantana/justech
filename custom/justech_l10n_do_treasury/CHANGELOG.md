# Changelog — justech_l10n_do_treasury

## 19.0.1.4.1 — 2026-07-10

### Fixed
- `treasury_bank_state`: considera la cuenta outstanding (p. ej. `asset_current`) al evaluar conciliación bancaria; evita `bank_pending` falso cuando el pago ya está `paid` y la outstanding está conciliada.

## 19.0.1.4.0 — 2026-07-10

### Changed
- Menú Pagos unificado (6 opciones); conciliación bancaria fuera de Pagos.
- Hook reafirma desactivación de menús/acciones legacy de pagos múltiples.

## 19.0.1.3.4 — 2026-07-10

- Pagos abiertos, wizard de aplicación y navegación Contabilidad→Pagos.
