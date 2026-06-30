# Odoo Hellenia — Documentación

Proyecto Odoo **Enterprise 19** (objetivo) / Odoo **19 Community** (DEV/TEST actual) / Odoo **18** (PROD) para **Hellenia**.

## Arquitectura permanente

```
DEV  ──►  TEST  ──►  PRODUCCIÓN
```

| Ambiente | URL | Odoo | Estado |
|----------|-----|------|--------|
| DEV | https://dev.hellenia.cloud | 19.0-20260619 | Community — Enterprise pendiente E1 |
| TEST | https://test.hellenia.cloud | 19.0-20260619 | Community |
| PROD (actual) | odoo-pecv | 18 | **Activo — no migrar** |
| PROD (futuro) | odoo.hellenia.cloud | TBD | Pendiente |

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Capas + pipeline DEV→TEST→PROD |
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política oficial licenciamiento |
| [UPGRADE-PATH.md](UPGRADE-PATH.md) | Odoo 20/21+ sin rehacer infra |
| [E0.5 Validación suscripción](E0.5-SUBSCRIPTION-VALIDATION.md) | Checklist portal |
| [E0.6 GitHub Enterprise](E0.6-GITHUB-ENTERPRISE.md) | SSH key + repo Git oficial |
| [E1 Checklist](E1-CHECKLIST.md) | Validación final pre-E1 |
| [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md) | Análisis técnico Enterprise |
| [GIT-STRATEGY.md](GIT-STRATEGY.md) | Enterprise fuera de Git Justech |

## Inicio rápido

Ver [DEPLOYMENT.md](DEPLOYMENT.md)
