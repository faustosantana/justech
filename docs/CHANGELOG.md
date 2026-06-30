# Changelog — Hellenia Odoo

## [Unreleased]

### Added
- `docs/ENTERPRISE-LICENSING.md` — política oficial Odoo (sin suposiciones)
- `docs/UPGRADE-PATH.md` — actualización Odoo 20/21+ sin rehacer infra
- `config/credentials/README.md` — SSH key para GitHub Enterprise
- Esqueletos custom: `hellenia_base`, `hellenia_inventory`, `hellenia_reports`, `hellenia_account`, `hellenia_pos`, `justech_core`

### Changed
- Licenciamiento corregido: duplicación + neutralize (documentación oficial)
- Arquitectura permanente DEV → TEST → PROD documentada
- GitHub VPS: **SSH key dedicada** preferida sobre PAT permanente
- Enterprise: solo repo Git oficial (no ZIP manual)
- `E1-CHECKLIST.md` — validación final pre-ejecución revisada
- `clone-enterprise.sh` — soporte SSH + PAT fallback
- `E0.5`, `E0.6`, `ARCHITECTURE.md`, `ENTERPRISE_ANALYSIS.md` actualizados

### Pending (E1a — no ejecutado)
- Generar SSH key en VPS + usuario agrega `.pub` en GitHub
- Ejecutar `clone-enterprise.sh` + `web_enterprise`
- Registrar `M260616306091776` (E1b — aprobación separada)

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
