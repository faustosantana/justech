# Changelog — justech_l10n_do_ncf

## [19.0.2.1.0] — 2026-07-09 — Fase 3A Sprint 2 (parte 2)

### Added
- Validadores `validators/business_rules.py` — reglas Adel: **B14** (sin ITBIS), **RD$250k+RNC**, **B16** exportaciones.
- Servicio `ncf.business.rules.service` — invocado pre-post desde `ncf.assignment.service`.
- Pruebas Sprint 2b (`test_ncf_sprint2_part2.py`): NC/ND/compras, multiempresa 4 compañías, B14, 250k, B16.
- Plan documentado índice SQL v2.0 (`evidence/fiscal-phase3/NCF_INDEX_V2_PLAN.md`) — **sin aplicar**.

### Changed
- Smoke test `test_extended_document_types_assign_ncf` adaptado a reglas B14/B16.
- Integridad lab extendida: pagos, conciliaciones, GL (`scripts/fiscal-phase3-sprint2-lab-integrity.py`).

### Known limitation
- Índice SQL v1 permanece; migración v2.0 requiere aprobación explícita (ver plan).

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
