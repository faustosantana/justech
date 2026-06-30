# Revisión de infraestructura — Hellenia Odoo Enterprise

**Fecha:** 2026-06-30  
**Objetivo:** Evaluar deuda técnica antes de E1; horizonte 10 años  
**Estado:** Arquitectura congelada tras esta revisión

---

## Resumen ejecutivo

| Área | Estado | Deuda técnica |
|------|--------|---------------|
| Docker / Compose | ✅ Sólido | Baja — mejoras aplicadas |
| Traefik | ✅ Adecuado | Baja — externo al repo |
| PostgreSQL | ✅ Adecuado | Baja |
| Backups | ✅ Mejorado | Media → Baja (scripts corregidos) |
| Logs | ✅ Adecuado | Baja — rotación pendiente en VPS |
| Git | ✅ Sólido | Baja |
| Enterprise | ✅ Preparado | Pendiente E1 (clone) |
| Community | ✅ Pinneado | Baja |
| Custom | ✅ Estructura pro | Baja |
| Calidad / CI | 📋 Documentado | Pendiente post-E1 |
| Producción futura | 📋 Planificado | odoo-pecv separado (correcto) |

**Conclusión:** No hay deuda técnica estructural bloqueante para E1. Las mejoras aplicadas en esta revisión eliminan inconsistencias críticas en scripts y deploy.

---

## Separación de capas (definitiva)

```
┌─────────────────────────────────────────────────────────────┐
│  INFRAESTRUCTURA     docker/          Compose, imágenes     │
├─────────────────────────────────────────────────────────────┤
│  CONFIGURACIÓN       config/          odoo.conf, .env       │
├─────────────────────────────────────────────────────────────┤
│  DATOS INICIALES     data/            CSV/XML transversales │
│                      custom/*/data/   Datos por módulo      │
├─────────────────────────────────────────────────────────────┤
│  MÓDULOS             custom/          Único código propio   │
├─────────────────────────────────────────────────────────────┤
│  ENTERPRISE          enterprise/      Git odoo/enterprise   │
│  COMMUNITY           (imagen Docker)  odoo:19.0-*           │
├─────────────────────────────────────────────────────────────┤
│  SCRIPTS             scripts/         Automatización        │
├─────────────────────────────────────────────────────────────┤
│  DOCUMENTACIÓN       docs/            Guías y políticas     │
└─────────────────────────────────────────────────────────────┘
```

Una actualización Odoo **no debe tocar** la estructura de directorios — solo tags, ramas Git y código en `custom/`.

---

## Análisis por componente

### Docker

| Aspecto | Evaluación |
|---------|------------|
| Imagen pinneada | ✅ `odoo:19.0-20260619` — no `latest` |
| Sin imagen Enterprise | ✅ Correcto — volumen montado (oficial Odoo) |
| `restart: unless-stopped` | ✅ En odoo y db |
| Healthcheck Odoo | ✅ Añadido `/web/login` |
| Healthcheck PostgreSQL | ✅ `pg_isready` |
| Resource limits | ⚠️ No definidos — aceptable en DEV/TEST; documentar para PROD futuro |
| Multi-stage build custom | ❌ No necesario — volumen es más mantenible |

### Docker Compose

| Aspecto | Evaluación |
|---------|------------|
| Proyectos aislados | ✅ `hellenia-dev` / `hellenia-test` |
| Volúmenes nombrados | ✅ `${COMPOSE_PROJECT_NAME}_*` |
| Variables en `.env` | ✅ Paths absolutos VPS |
| `depends_on` + healthy | ✅ DB antes de Odoo |
| Redes | ✅ Red por stack; Traefik vía Docker provider |

**Nota Traefik:** No hay red externa explícita en compose. Funciona si Traefik usa socket Docker (configuración actual VPS). Si se migra a red dedicada, añadir `TRAEFIK_NETWORK` en `.env` — documentado en DEVOPS_GUIDE.

### Traefik

| Aspecto | Evaluación |
|---------|------------|
| Labels TLS | ✅ Let's Encrypt |
| Host rules | ✅ `dev.` / `test.` + `TRAEFIK_HOST` |
| Config en repo | ❌ Correcto — stack compartido VPS |
| Healthcheck incluye Traefik | ✅ `healthcheck.sh` |

### PostgreSQL

| Aspecto | Evaluación |
|---------|------------|
| Versión | ✅ 17-alpine (≥ requisito Odoo 19) |
| Aislamiento | ✅ Instancia por ambiente |
| Backups | ✅ `pg_dumpall` desde contenedor db |
| Exposición pública | ✅ Sin puerto publicado |
| PG en host vs contenedor | ✅ Contenedor — portable |

### Backups

| Problema detectado | Corrección aplicada |
|--------------------|---------------------|
| Hardcoded `hellenia-dev-odoo-1` | ✅ Usa `COMPOSE_PROJECT_NAME` vía `common.sh` |
| Dump solo si Odoo up | ✅ Dump si contenedor **db** up |
| Symlinks retention incorrectos | ✅ `mark_backup_tier` en backup_root |
| Sin `restore-dev/test.sh` | ✅ Scripts añadidos |
| ROLLBACK mencionaba `addons.tar.gz` | ✅ Corregido a `custom.tar.gz` |
| restore-prod-to-test usaba `addons/` | ✅ Corregido a `custom/` |

**Pendiente (no bloqueante):** cron automatizado, backup off-site, restore test trimestral.

### Logs

| Aspecto | Evaluación |
|---------|------------|
| Odoo → stdout | ✅ Correcto para Docker |
| Scripts → `logs/deploy/` | ✅ Gitignored |
| Rotación | ⚠️ Configurar logrotate en VPS (documentado) |
| Centralización | ⚠️ Futuro (Datadog/Loki) — no requerido ahora |

### Git

| Aspecto | Evaluación |
|---------|------------|
| Enterprise fuera de Git | ✅ `.gitignore` |
| Credentials fuera de Git | ✅ |
| Deploy sincroniza todo | ✅ Corregido (antes solo custom) |
| Rama unificada | ✅ `hellenia-odoo-infra` default en deploy |
| `repository/` en VPS | ✅ Layout documentado |

### Enterprise

| Aspecto | Evaluación |
|---------|------------|
| Clone independiente | ✅ `enterprise/` |
| SSH auth | ✅ Preferido sobre PAT |
| Rama alineada | ✅ `19.0` |
| Montaje RO | ✅ `/mnt/enterprise:ro` |
| `addons_path` orden | ✅ Enterprise primero |

### Community

| Aspecto | Evaluación |
|---------|------------|
| Solo imagen Docker | ✅ Sin duplicar repo odoo/odoo |
| `community/README.md` | ✅ Documenta versión |
| Upgrade script | ✅ `upgrade-community.sh` |

### Custom Addons

| Aspecto | Evaluación |
|---------|------------|
| 6 módulos esqueleto | ✅ Estructura profesional completa |
| README por módulo | ✅ |
| tests/ placeholder | ✅ |
| i18n/es.po | ✅ |
| Sin lógica prematura | ✅ |

---

## Mejoras implementadas en esta revisión

| # | Mejora |
|---|--------|
| 1 | `scripts/lib/common.sh` — funciones compartidas |
| 2 | Backups usan nombres dinámicos de contenedor/volumen |
| 3 | `restore-dev.sh` / `restore-test.sh` |
| 4 | `deploy-*.sh` sincroniza docker, config, scripts, data |
| 5 | `upgrade-community.sh`, `upgrade-enterprise.sh`, `update-custom-modules.sh` |
| 6 | Healthcheck Odoo en compose |
| 7 | `data/` para datos iniciales transversales |
| 8 | 6 módulos custom con estructura Odoo completa |
| 9 | 5 guías + esta revisión |
| 10 | ROLLBACK y restore-prod-to-test corregidos |

---

## Deuda técnica residual (aceptable)

| Item | Prioridad | Cuándo |
|------|-----------|--------|
| pre-commit + Ruff + pylint-odoo | Media | Post-E1, primer módulo real |
| GitHub Actions CI | Media | Post-E1 |
| Cron backups automatizado | Media | Tras E1 estable |
| logrotate en VPS | Baja | Cualquier momento |
| docker-compose PROD futuro | Alta | Migración odoo.hellenia.cloud |
| Resource limits PROD | Media | Con compose PROD |
| Traefik red externa explícita | Baja | Solo si Traefik lo requiere |
| Monitoring/alerting | Baja | Escala operativa |

**Ningún item bloquea E1.**

---

## Checklist pre-E1 (infraestructura)

- [x] Separación capas documentada
- [x] Scripts backup/restore/deploy corregidos
- [x] Custom modules estructura profesional
- [x] Guías desarrollo, DevOps, upgrade
- [x] Sin PAT permanente en diseño GitHub
- [x] Healthchecks compose
- [ ] Enterprise clonado (E1a)
- [ ] `web_enterprise` instalado (E1a)
- [ ] SSH key GitHub en VPS (E1a)

---

## Referencias

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEVOPS_GUIDE.md](DEVOPS_GUIDE.md)
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- [UPGRADE_POLICY.md](UPGRADE_POLICY.md)
- [E1-CHECKLIST.md](E1-CHECKLIST.md)
