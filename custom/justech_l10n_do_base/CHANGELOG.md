# Changelog — justech_l10n_do_base

## [19.0.1.6.0] — 2026-07-09 — Fase 3A Sprint 1

### Added
- Capa `validators/` (RNC, NCF, contexto fiscal v2.0 duplicados).
- Capa `services/` (`fiscal.validator`, `fiscal.config`, `document.type.provider`).
- Placeholders `providers/` y `adapters/` para extensiones futuras.
- Pruebas `test_fiscal_validators.py` (Odoo) + runner standalone en `tools/`.
- Documentación técnica: ARCHITECTURE, MIGRATION, ROADMAP, diagramas.

### Changed
- `res.partner` delega validación RNC al servicio fiscal (sin cambio funcional).
- `fiscal.document.type.parse_ncf` delega a validador puro.

### Unchanged (compatibilidad)
- Datos maestros NCF, vistas, permisos y reglas de negocio existentes.
