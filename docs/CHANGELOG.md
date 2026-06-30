# Changelog — Hellenia Odoo

## [Unreleased]

### Changed — Pivot estratégico v3.0 (2026-06-30)
- `docs/PROJECT_STRATEGY.md` — plataforma Odoo 19 EE On-Premise; hoja de ruta 12 fases
- Sin perseguir saas-19.3; NCF = línea base producto; limitaciones documentadas sin bloquear
- Política custom: 4 comprobaciones obligatorias
- TC-003+ desbloqueados para continuar implementación funcional
- G-01: limitación conocida, no bloqueante

### Changed — Gate portal + G-01 provisional (2026-06-30)
- `--execute` requiere `HELLENIA_APPROVE_ENTERPRISE_EXECUTE=yes` (evita ejecución accidental)
- G-01: pendiente decisión final hasta verificación portal + upgrade DEV + re-TC-001/002
- Sin desarrollo custom hasta cerrar G-01 post-upgrade

### Added — Upgrade Enterprise DEV + gate TC-003 (2026-06-30)
- `docs/ENTERPRISE-UPGRADE-DEV.md` — pipeline upgrade DEV, estado tarball `20260629` vs imagen `20260619`
- `scripts/upgrade-enterprise-dev.sh` — orquestador: `--status`, `--validate-only`, `--execute`, `--rerun-tc001-tc002`
- Validación RD Etapa 1 en `validate_enterprise_archive.py` (`--rd-stage1`): l10n_do, l10n_do_reports, l10n_do_edi, l10n_latam*

### Changed
- TC-003 y pruebas funcionales NCF **bloqueadas** hasta DEV en última versión Enterprise disponible
- `receive-enterprise-archive.sh` valida con `--rd-stage1`

### Added — Pre-E1 enterprise platform (arquitectura congelada)
- `docs/INFRASTRUCTURE_REVIEW.md` — revisión 10 años + deuda técnica
- `docs/DEVELOPMENT_GUIDE.md`, `CODING_STANDARDS.md`, `DEVOPS_GUIDE.md`
- `docs/CUSTOM_MODULE_GUIDE.md`, `UPGRADE_POLICY.md`
- `scripts/lib/common.sh` — funciones compartidas
- `scripts/restore-dev.sh`, `restore-test.sh`
- `scripts/upgrade-community.sh`, `upgrade-enterprise.sh`, `update-custom-modules.sh`
- `data/README.md` — datos iniciales transversales
- `tools/quality/README.md` — estrategia calidad (sin implementar)
- Módulos custom: estructura completa (tests, i18n, static, README por módulo)

### Changed — Mejoras estructurales pre-E1
- Backups: nombres dinámicos contenedor/volumen; dump si DB up
- Deploy: sincroniza docker, config, scripts, data (no solo custom)
- Docker compose: healthcheck Odoo
- ROLLBACK.md: restore automatizado + custom.tar.gz
- restore-production-to-test.sh: path custom/

### Previous (E0.5–E0.9)
- ENTERPRISE-LICENSING.md, UPGRADE-PATH.md, SSH GitHub, arquitectura DEV→TEST→PROD

### Added — Estrategia portal Enterprise (2026-06-30)
- `ENTERPRISE_ACCESS_OPTIONS.md`, `E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md`, `L10N-RD-READINESS.md`
- Scripts: `extract-enterprise-portal.sh`, `fetch-enterprise.sh`, `validate-enterprise-archive.sh`
- `downloads/enterprise/` staging

### Added — Entrega semi-automática Enterprise (2026-06-30)
- `docs/E0.6c-ENTERPRISE-DELIVERY-FLOW.md` — flujos A/B/C sin SCP del usuario
- `scripts/lib/validate_enterprise_archive.py` — validación exhaustiva (19.0, integridad, web_enterprise)
- `scripts/download-enterprise-portal.sh` — descarga desde URL temporal del portal
- `scripts/receive-enterprise-archive.sh` — recibe archivo vía Cursor al VPS
- `scripts/e1a-portal-pipeline.sh` — `--validate-only` / `--execute`
- Verificación VPS: Enterprise requiere sesión; no hay URL wget permanente

### Added — E1a Enterprise image DEV (2026-06-30)
- Imagen `hellenia-odoo:19-enterprise` (Enterprise + custom horneados, sin volumen)
- `docker/dev/Dockerfile.enterprise`, `docker-compose.community.yml` (rollback)
- Scripts: `extract-enterprise-full.sh`, `prepare-enterprise-addons.sh`, `build-hellenia-odoo-image.sh`, `e1a-enterprise-image.sh`
- DEV: `web_enterprise` instalado; TEST/PROD sin cambios

### Added — Estrategia licencia diferida (2026-06-30)
- `docs/UNREGISTERED_ENTERPRISE_LIMITATIONS.md` — alcance DEV sin registrar M260616306091776
- Registro reservado para go-live BD definitiva; l10n_do_edi ausente en tarball 19.0+e

### Added (previo)
- `docs/ENTERPRISE_ANALYSIS.md` — análisis Enterprise, suscripción M260616306091776, módulos RD, plan DEV propuesto (sin ejecución)

### Changed
- DEV y TEST migrados a **Odoo 19.0-20260619** (imagen fija, no `latest`)
- Análisis técnico completo pre-migración → `docs/VERSION-19-ANALYSIS.md`
- Runbook migración → `docs/MIGRATION-19.md`
- Scripts `upgrade-odoo19.sh` y `validate-odoo19.sh`
- `healthcheck.sh` valida versión Odoo 19 en DEV/TEST

### Unchanged
- Producción activa en `/docker/odoo-pecv` — **Odoo 18, sin modificaciones**
- Wizard de configuración — **no ejecutado**
- Usuarios — **no creados**

## [2026-06-30] — Infraestructura inicial

### Added
- Estructura `/opt/odoo-projects/hellenia/` (DEV, TEST, scripts, docs)
- Plantilla reutilizable en `/opt/odoo-projects/template/`
- Documentación producción actual (`config/production/README.md`)
- Scripts backup/deploy/healthcheck con retención
