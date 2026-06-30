# Changelog — Hellenia Odoo

## [Unreleased]

### Added
- Arquitectura profesional: `community/`, `enterprise/`, `custom/` separados
- `docs/ARCHITECTURE.md`, `GIT-STRATEGY.md`, `E0.5`, `E0.6`, `INFILE-REQUIREMENTS.md`
- Scripts: `validate-subscription-env.sh`, `clone-enterprise.sh`, `install-enterprise-dev.sh`, `validate-enterprise-dev.sh`
- `config/credentials/github.env.example`

### Changed
- `docker-compose`: volúmenes `/mnt/enterprise` y `/mnt/custom`
- `addons_path`: Enterprise → Community (imagen) → Custom
- `addons/` migrado a `custom/`
- DEV recreado con nueva arquitectura de volúmenes

### Pending (E1)
- Crear `config/credentials/github.env` en VPS
- Vincular GitHub en portal Odoo
- Ejecutar `install-enterprise-dev.sh`
- Registrar `M260616306091776` en UI DEV

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
