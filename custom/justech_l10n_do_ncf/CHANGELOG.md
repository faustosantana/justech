# Changelog — justech_l10n_do_ncf

## [19.0.1.8.0] — 2026-07-09 — Fase 3A Sprint 1

### Added
- Capa `services/`:
  - `justech.do.ncf.document.type.resolver.service`
  - `justech.do.ncf.duplicate.service`
  - `justech.do.ncf.assignment.service`
- Documentación técnica completa y diagramas de dependencias.

### Changed
- `account.move` refactorizado: métodos `_justech_*` delegan en servicios (comportamiento idéntico).
- `ncf.range._validate_ncf_format` delega en `justech.do.fiscal.validator.service`.

### Unchanged (compatibilidad)
- Índice único NCF, consumo de rangos, anulación, PDF, tests existentes.
