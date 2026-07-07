# justech — Odoo Hellenia Enterprise

Implementación Odoo **Enterprise 19 On-Premise** para Hellenia, S.R.L. (República Dominicana).  
Referencia profesional RD — administrado por **Justech**. Pipeline: **DEV → TEST → PRODUCCIÓN**.

**Versión producto:** **Hellenia 1.0.0** — ver [evidence/release-1.0/](evidence/release-1.0/)

**Estrategia v3.0:** [docs/PROJECT_STRATEGY.md](docs/PROJECT_STRATEGY.md)

## Estructura del repositorio

```
├── custom/           # Módulos propios (único código de negocio)
├── docker/           # Infraestructura Docker Compose
├── config/           # Configuración por ambiente
├── data/             # Datos iniciales transversales
├── scripts/          # Automatización (deploy, backup, upgrade)
├── docs/             # Documentación
├── community/        # Referencia Community (imagen Docker)
└── enterprise/       # Placeholder — clone Git en VPS (no en Git)
```

**VPS:** `/opt/odoo-projects/hellenia/` con clone Git en `repository/`.

## Ambientes

| Ambiente | URL | Odoo |
|----------|-----|------|
| DEV | https://dev.hellenia.cloud | 19.0 Community → Enterprise (E1) |
| TEST | https://test.hellenia.cloud | 19.0 |
| PROD | https://odoo.hellenia.cloud | 19.0 EE — **Hellenia 1.0.0** |

## Documentación principal

| Documento | Contenido |
|-----------|-----------|
| [docs/PROJECT_STRATEGY.md](docs/PROJECT_STRATEGY.md) | **Estrategia v3.0** — hoja de ruta 12 fases |
| [docs/IMPLEMENTATION_MASTER_PLAN.md](docs/IMPLEMENTATION_MASTER_PLAN.md) | Plan maestro por fase |
| [docs/INFRASTRUCTURE_REVIEW.md](docs/INFRASTRUCTURE_REVIEW.md) | Revisión infra + deuda técnica |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura capas |
| [docs/E1-CHECKLIST.md](docs/E1-CHECKLIST.md) | Pre-E1 (pendiente aprobación) |
| [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) | Guía desarrollo |
| [docs/DEVOPS_GUIDE.md](docs/DEVOPS_GUIDE.md) | Operaciones y scripts |

## Inicio rápido (VPS)

```bash
# Desplegar DEV
/opt/odoo-projects/hellenia/scripts/deploy-dev.sh hellenia-odoo-infra

# Healthcheck
/opt/odoo-projects/hellenia/scripts/healthcheck.sh
```

**Nunca** commitear `.env` ni credenciales.

## Git

```bash
git remote add origin git@github.com:faustosantana/justech.git
```

Rama activa infraestructura: `hellenia-odoo-infra` / `cursor/odoo19-migration-dev-test-dd85`
