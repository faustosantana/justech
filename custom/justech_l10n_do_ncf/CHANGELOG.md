# Changelog — justech_l10n_do_ncf

## [19.0.2.0.0] — 2026-07-09 — Fase 3A Sprint 2

### Added
- **Centro de Administración Fiscal** (`justech.do.ncf.admin.center`) — hub operativo con accesos rápidos.
- **Diagnóstico Fiscal** (`justech.do.fiscal.diagnostic.wizard`) — escaneo read-only automatizado.
- Servicios `ncf.range.audit.service` y `ncf.diagnostic.service`.
- Validadores `validators/duplicate_scope.py` — alcance v2.0 ventas/compras.
- Campo calculado `% consumido` en rangos NCF.
- Pestaña **Comprobante fiscal** en facturas (menos ruido visual).
- Pruebas Sprint 2 (`test_ncf_sprint2.py`).

### Changed
- Duplicados NCF: lógica **v2.0** (ventas por empresa; compras por proveedor).
- Mensajes de error en español con referencia al Centro Administrativo.
- Menú fiscal reorganizado — Centro Admin como entrada principal (managers).
- Website manifest → `justech.do`.

### Removed
- Código muerto `_justech_purchase_ncf_prefixes`.

### Known limitation
- Índice SQL único `(company_id, justech_do_ncf)` permanece (v1) por compatibilidad histórica.
  La lógica v2.0 en Python permite venta/compra con mismo string; el índice se revisará en Sprint 3.

## [19.0.1.8.0] — 2026-07-09 — Fase 3A Sprint 1

### Added
- Capa `services/` (resolver, duplicate, assignment).
- Refactor `account.move` sin cambio funcional.
