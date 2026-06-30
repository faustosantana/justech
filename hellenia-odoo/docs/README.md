# Odoo Hellenia — Documentación

Proyecto Odoo 18 multi-ambiente para **Hellenia**.

## Arquitectura

```
Cursor local → GitHub → DEV → TEST → Producción
```

| Ambiente | URL | Stack Compose | Estado |
|----------|-----|---------------|--------|
| DEV | https://dev.hellenia.cloud | `hellenia-dev` | Pendiente despliegue |
| TEST | https://test.hellenia.cloud | `hellenia-test` | Pendiente despliegue |
| PROD (actual) | https://odoo-pecv.srv1784296.hstgr.cloud | `odoo-pecv` | **Activo** — no migrado |
| PROD (futuro) | https://odoo.hellenia.cloud | TBD | Pendiente |

## Rutas

| Recurso | Ruta |
|---------|------|
| Addons | `/opt/odoo-projects/hellenia/addons/` |
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

## Inicio rápido

Ver [DEPLOYMENT.md](DEPLOYMENT.md)
