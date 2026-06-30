# Odoo Hellenia — Documentación

Proyecto Odoo **Enterprise 19** para **Hellenia**. Pipeline permanente: **DEV → TEST → PRODUCCIÓN**.

## Arquitectura y operaciones

| Documento | Contenido |
|-----------|-----------|
| [PROJECT_STRATEGY.md](PROJECT_STRATEGY.md) | **Estrategia v3.0** — plataforma, 12 fases, NCF, custom |
| [PHASE35_GOLDEN_CONFIGURATION_REPORT.md](PHASE35_GOLDEN_CONFIGURATION_REPORT.md) | **Fase 3.5** — Golden Configuration definitiva |
| [IMPLEMENTATION_DECISIONS.md](IMPLEMENTATION_DECISIONS.md) | Registro decisiones implementación |
| [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) | Plan maestro implementación |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Capas Community / Enterprise / Custom |
| [DEVOPS_GUIDE.md](DEVOPS_GUIDE.md) | Scripts, backups, despliegues |
| [UPGRADE_POLICY.md](UPGRADE_POLICY.md) | Gobernanza actualizaciones |
| [UPGRADE-PATH.md](UPGRADE-PATH.md) | Procedimiento técnico Odoo 20+ |

## Desarrollo

| Documento | Contenido |
|-----------|-----------|
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Flujo de trabajo + calidad (estrategia) |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | PEP8, Odoo, herencia |
| [CUSTOM_MODULE_GUIDE.md](CUSTOM_MODULE_GUIDE.md) | Estructura módulos custom |

## Enterprise y E1

| Documento | Contenido |
|-----------|-----------|
| [ENTERPRISE_ACCESS_OPTIONS.md](ENTERPRISE_ACCESS_OPTIONS.md) | **Git vs portal vs soporte** |
| [E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md) | Descarga oficial Sources |
| [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md) | GitHub (paralelo) |
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política oficial licenciamiento |
| [ENTERPRISE-UPGRADE-DEV.md](ENTERPRISE-UPGRADE-DEV.md) | **Upgrade DEV** — tarball portal, validación RD, gate TC-003 |
| [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md) | Plan pruebas NCF tradicional |
| [E1-CHECKLIST.md](E1-CHECKLIST.md) | Checklist E1 |
| [E1-ENTERPRISE-STATUS.md](E1-ENTERPRISE-STATUS.md) | Estado actual |
| [E1B-LICENSE-CHECKLIST.md](E1B-LICENSE-CHECKLIST.md) | E1b registro licencia (go-live) |
| [UNREGISTERED_ENTERPRISE_LIMITATIONS.md](UNREGISTERED_ENTERPRISE_LIMITATIONS.md) | **Laboratorio DEV sin registro** |
| [E0.5-SUBSCRIPTION-VALIDATION.md](E0.5-SUBSCRIPTION-VALIDATION.md) | Suscripción |

## Referencia

| Documento | Contenido |
|-----------|-----------|
| [GIT-STRATEGY.md](GIT-STRATEGY.md) | Qué va en Git |
| [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md) | Análisis técnico Enterprise |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Runbook despliegue VPS |
| [ROLLBACK.md](ROLLBACK.md) | Procedimientos rollback |

## Ambientes

| Ambiente | URL | Estado |
|----------|-----|--------|
| DEV | https://dev.hellenia.cloud | Odoo 19 — E1 pendiente |
| TEST | https://test.hellenia.cloud | Odoo 19 |
| PROD | odoo-pecv | Odoo 18 — no tocar |
