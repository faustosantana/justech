# Changelog — justech_l10n_do_base

## [19.0.1.14.0] — 2026-07-11 — Contactos RNC + padrón DGII

### Added
- Modelo `justech.do.rnc.padron` y wizard de importación TXT/CSV (formato DGII oficial).
- Validación RNC en formulario de contactos con Resultado y Fuente separados.
- Autocompletado de razón social cuando Nombre está vacío.
- Control de RNC duplicado (contacto existente + abrir).

### Changed
- Vista `res.partner`: bloques Identificación fiscal, Configuración fiscal y Relación comercial a ancho completo.
- Importador alineado al layout oficial `DGII_RNC.TXT`.

### Operational
- Padrón DGII cargado en `justech_dev` (fuente `dgii_txt`).

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
