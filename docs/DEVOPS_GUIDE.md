# Guía DevOps — Hellenia Odoo

**Principio:** Toda operación repetible se ejecuta mediante **scripts** en `scripts/`.

---

## Mapa de scripts

| Operación | Script | Ambiente |
|-----------|--------|----------|
| Desplegar | `deploy-dev.sh` / `deploy-test.sh` | DEV / TEST |
| Backup | `backup-dev.sh` / `backup-test.sh` | DEV / TEST |
| Restaurar | `restore-dev.sh` / `restore-test.sh` | DEV / TEST |
| Healthcheck | `healthcheck.sh` | Todos |
| Upgrade Community | `upgrade-community.sh` | DEV / TEST |
| Upgrade Enterprise | `upgrade-enterprise.sh` | Global |
| Actualizar módulos custom | `update-custom-modules.sh` | DEV / TEST |
| Clone / extract Enterprise | `fetch-enterprise.sh` / `extract-enterprise-portal.sh` / `clone-enterprise.sh` | Global |
| Validar tarball portal | `validate-enterprise-archive.sh` | Pre-E1 |
| Instalar Enterprise | `install-enterprise-dev.sh` | DEV (E1) |
| Validar Enterprise | `validate-enterprise-dev.sh` | DEV |
| Validar suscripción | `validate-subscription-env.sh` | Global |
| Backup producción actual | `backup-production-current.sh` | odoo-pecv |
| Prod → TEST | `restore-production-to-test.sh` | TEST |

Funciones compartidas: `scripts/lib/common.sh`

---

## Despliegues

### DEV

```bash
/opt/odoo-projects/hellenia/scripts/deploy-dev.sh [rama-o-commit]
```

**Sincroniza desde `repository/`:**
- `custom/`, `docker/`, `config/` (excluye `.env` y `credentials/`), `scripts/`, `data/`
- `docker compose up -d`

### TEST

```bash
/opt/odoo-projects/hellenia/scripts/deploy-test.sh [rama-o-commit]
```

### Rollback deploy

```bash
cd /opt/odoo-projects/hellenia/repository
git checkout <commit-anterior>
/opt/odoo-projects/hellenia/scripts/deploy-test.sh <commit-anterior>
```

---

## Backups

### Manual

```bash
/opt/odoo-projects/hellenia/scripts/backup-dev.sh
/opt/odoo-projects/hellenia/scripts/backup-test.sh
```

### Contenido de cada backup

| Archivo | Contenido |
|---------|-----------|
| `postgres_all.sql.gz` | Dump completo PostgreSQL |
| `filestore.tar.gz` | Adjuntos Odoo |
| `custom.tar.gz` | Módulos custom |
| `docker-compose.yml` | Snapshot compose |
| `odoo.conf` | Snapshot config |
| `.env` | Variables ambiente (sensible) |
| `MANIFEST.txt` | Metadatos backup |

### Retención

- Diarios: 7 días
- Semanales: 4 (symlink `*_weekly` los domingos)
- Mensuales: 6 (symlink `*_monthly` día 1)

### Automatización futura (cron)

```cron
# /etc/cron.d/hellenia-odoo-backups (NO instalar hasta aprobación)
0 2 * * * root /opt/odoo-projects/hellenia/scripts/backup-dev.sh
30 2 * * * root /opt/odoo-projects/hellenia/scripts/backup-test.sh
```

Documentar en servidor; no incluir cron en repo hasta VPS aprobado.

---

## Restauraciones

### DEV

```bash
/opt/odoo-projects/hellenia/scripts/restore-dev.sh \
  /opt/odoo-projects/hellenia/backups/dev/2026-06-30_0200
```

Crea backup de seguridad automático antes de restaurar.

### TEST

```bash
/opt/odoo-projects/hellenia/scripts/restore-test.sh \
  /opt/odoo-projects/hellenia/backups/test/2026-06-30_0200
```

---

## Actualizaciones

### Community (imagen Docker)

```bash
# 1. Actualizar tag en docker/dev/docker-compose.yml (commit Git)
# 2. Ejecutar:
/opt/odoo-projects/hellenia/scripts/upgrade-community.sh dev
```

Ver [UPGRADE_POLICY.md](UPGRADE_POLICY.md) para gobernanza.

### Enterprise (Git)

```bash
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise.sh 19.0
# Reiniciar contenedores
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env restart odoo
```

### Módulos custom

```bash
# Tras deploy de código:
/opt/odoo-projects/hellenia/scripts/update-custom-modules.sh dev hellenia_inventory hellenia_base
```

---

## Docker / Traefik / PostgreSQL

### Docker Compose

| Componente | DEV | TEST |
|------------|-----|------|
| Odoo | `odoo:19.0-20260619` | Igual |
| PostgreSQL | `postgres:17-alpine` | Igual |
| Healthcheck Odoo | `/web/login` | Igual |
| Healthcheck DB | `pg_isready` | Igual |

### Traefik

- Labels en servicio `odoo` del compose
- Instancia compartida: `traefik-traefik-1`
- Certificados: Let's Encrypt vía `letsencrypt` resolver
- **No hay config Traefik en este repo** — stack externo en VPS

### PostgreSQL

- Una instancia DB por stack (DEV/TEST aislados)
- Backups vía `pg_dumpall` desde contenedor `db`
- **No exponer** puerto 5432 públicamente

---

## Logs

| Tipo | Ubicación |
|------|-----------|
| Odoo stdout | `docker logs hellenia-dev-odoo-1` |
| Scripts deploy/backup | `logs/deploy/*.log` |
| PostgreSQL | `docker logs hellenia-dev-db-1` |

`logfile = False` en `odoo.conf` — logs van a Docker (correcto para contenedores).

### Rotación futura

```bash
# logrotate en VPS para logs/deploy/ (NO en repo aún)
/opt/odoo-projects/hellenia/logs/deploy/*.log {
    weekly
    rotate 12
    compress
    missingok
}
```

---

## Monitoreo

```bash
/opt/odoo-projects/hellenia/scripts/healthcheck.sh
```

Verifica: producción `odoo-pecv`, DEV, TEST, Traefik, versiones Odoo 19.

### Automatización futura

- Cron cada 5 min + alerta si falla
- Integración Datadog/Prometheus (fuera de alcance actual)

---

## Seguridad operativa

| Recurso | Permisos |
|---------|----------|
| `config/*/.env` | chmod 600 |
| `config/credentials/` | chmod 700 |
| Backups con `.env` | chmod 600 directorio padre |

---

## Referencias

- [ROLLBACK.md](ROLLBACK.md)
- [UPGRADE_POLICY.md](UPGRADE_POLICY.md)
- [UPGRADE-PATH.md](UPGRADE-PATH.md)
- [INFRASTRUCTURE_REVIEW.md](INFRASTRUCTURE_REVIEW.md)
