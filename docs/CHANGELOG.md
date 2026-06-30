# Changelog — Hellenia Odoo

## [Unreleased]

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

### Pending (E1a-revised — portal)
- Usuario: entregar URL temporal o archivo adjunto a Cursor
- Aprobación explícita: `e1a-portal-pipeline.sh --execute` en DEV

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
