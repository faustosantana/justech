# Changelog — justech_l10n_do_payments_withholding

## 19.0.1.6.1 — 2026-07-13

### Fixed
- Catálogo de retenciones global (`company_id` vacío) + override por empresa; ACL Administrador de Retenciones.
- Legado `RET5%` alineado a 623 (código DGII / affects_623) sin recalcular asientos.
- Retenciones navegables en pago y factura; stamp 623 reconoce códigos Gobierno.

## 19.0.1.5.0 — 2026-07-10

### Changed
- Flujo único operativo: el botón de factura `Registrar pago` abre `justech.payment.partner.wizard`.
- Prefill de partner/facturas al abrir desde `account.move`.
- Acciones/menús de `multi.invoice.manual.payment.wizard` sin binding UI (módulo conservado por histórico).

### Notes
- Default fiscal del cliente vacío → **P2 mejora UX futura** (la factura resuelve tipo/NCF; no es bloqueo).

## 19.0.1.3.1 — 2026-07-10

- Estabilización wizard unificado cobro/pago (banco, método, retenciones).
- Eliminación menú duplicado Administrar Retenciones.
- Scripts de diagnóstico y limpieza de pago de prueba.
