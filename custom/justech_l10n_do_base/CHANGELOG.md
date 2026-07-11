# Changelog — justech_l10n_do_base

## [19.0.1.20.0] — 2026-07-11 — Padrón DGII Enterprise

### Fixed
- Lock concurrente con `pg_advisory_lock` + `FOR UPDATE NOWAIT`.
- Si la importación falla tras mutar, restaura automáticamente el snapshot vigente.
- Rollback ACL alineado a Administrador Fiscal / Settings.
- `run_hour` aplicado al programar `next_run_at` y como ventana del cron.
- Cron horario sincronizado con `auto_update_enabled` (activo/inactivo).

### Added
- Adjunto del archivo fuente en historial para reintento real (`source=retry`).
- Acción «Reintentar con este archivo» y servicio `retry_last_failed`.
- Campo `cron_active` en configuración; guía restore/reimportación en status.

## [19.0.1.19.0] — 2026-07-11 — Contactos: cédula + padrón

### Fixed
- Validación DGII también para personas con cédula (11 dígitos), no solo RNC empresa (9).
- Visibilidad del bloque «Validar con DGII» para tipo persona/cédula.
- Integridad de padrón: logs `running` huérfanos ya no marcan el padrón como «a medias».

### Changed
- `_compute_justech_do_rnc_valid` y `action_justech_validate_rnc` alineados a longitudes 9/11.

## [19.0.1.15.0] — 2026-07-11 — Administración padrón DGII

### Added
- Historial de importaciones (`justech.do.rnc.padron.import.log`).
- Configuración de actualización automática (`justech.do.rnc.padron.config`).
- Servicios de importación por lotes, integridad, snapshot/rollback y descarga DGII.
- Cron de actualización automática (frecuencia configurable, default 45 días).
- Administración del padrón restringida a `base.group_system`.

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
