# Odoo Hellenia — Documentación

Proyecto Odoo **Enterprise 19** (objetivo) / Odoo **19 Community** (DEV/TEST actual) / Odoo **18** (PROD) para **Hellenia**.

## Arquitectura

```
Cursor local → GitHub → DEV → TEST → Producción
```

| Ambiente | URL | Stack Compose | Odoo | Estado |
|----------|-----|---------------|------|--------|
| DEV | https://dev.hellenia.cloud | `hellenia-dev` | 19.0-20260619 | Migrado |
| TEST | https://test.hellenia.cloud | `hellenia-test` | 19.0-20260619 | Migrado |
| PROD (actual) | https://odoo-pecv.srv1784296.hstgr.cloud | `odoo-pecv` | 18 | **Activo — no migrado** |
| PROD (futuro) | https://odoo.hellenia.cloud | TBD | — | Pendiente |

## Rutas

| Recurso | Ruta |
|---------|------|
| Addons custom | `/opt/odoo-projects/hellenia/custom/` |
| Enterprise (clone) | `/opt/odoo-projects/hellenia/enterprise/` |
| Community | Imagen Docker `odoo:19.0-20260619` |
| Compose DEV | `/opt/odoo-projects/hellenia/docker/dev/` |
| Compose TEST | `/opt/odoo-projects/hellenia/docker/test/` |
| Config DEV | `/opt/odoo-projects/hellenia/config/dev/` |
| Config TEST | `/opt/odoo-projects/hellenia/config/test/` |
| Scripts | `/opt/odoo-projects/hellenia/scripts/` |
| Git repo | `/opt/odoo-projects/hellenia/repository/` |

## Ramas Git

| Rama | Uso |
|------|-----|
| `main` | Producción aprobada |
| `develop` | Desarrollo |
| `test` | Pruebas / UAT |
| `feature/*` | Funcionalidades |
| `hotfix/*` | Correcciones urgentes |

## Documentación

- [Arquitectura](ARCHITECTURE.md) — separación Community / Enterprise / Custom
- [E0.5 Validación suscripción](E0.5-SUBSCRIPTION-VALIDATION.md)
- [E0.6 GitHub Enterprise](E0.6-GITHUB-ENTERPRISE.md)
- [E1 Checklist](E1-CHECKLIST.md) — pendiente aprobación
- [Estrategia Git](GIT-STRATEGY.md)
- [Infile — requisitos](INFILE-REQUIREMENTS.md)
- [Análisis Odoo Enterprise](ENTERPRISE_ANALYSIS.md)
- [Análisis técnico Odoo 19](VERSION-19-ANALYSIS.md)
- [Runbook migración 18→19](MIGRATION-19.md)

## Inicio rápido

Ver [DEPLOYMENT.md](DEPLOYMENT.md)
