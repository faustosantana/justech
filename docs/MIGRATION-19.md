# Migración Odoo 18 → 19 — Hellenia DEV/TEST

**Fecha inicio:** 2026-06-30  
**Imagen destino:** `odoo:19.0-20260619`  
**Producción:** NO migrada (permanece `odoo:18` en `/docker/odoo-pecv`)

---

## Alcance

| Ambiente | Acción | BD |
|----------|--------|-----|
| DEV | ✅ Migrar a Odoo 19 | `hellenia_dev` |
| TEST | ✅ Replicar tras DEV estable | `hellenia_test` |
| PROD (`odoo-pecv`) | ⛔ Sin cambios | — |

**Excluido de esta fase:** wizard de configuración, usuarios, instalación `l10n_do`, módulos de negocio.

---

## Pre-requisitos

- [x] Análisis técnico completado → `docs/VERSION-19-ANALYSIS.md`
- [x] DNS y SSL operativos (dev/test)
- [x] Backups DEV y TEST antes del cambio
- [x] Tag fijo `19.0-20260619` (no `latest`)

---

## Procedimiento automatizado

```bash
# En el VPS (como root)
cd /opt/odoo-projects/hellenia

# 1. Sincronizar repo
git -C repository fetch origin hellenia-odoo-infra
git -C repository checkout hellenia-odoo-infra
git -C repository pull origin hellenia-odoo-infra
rsync -av repository/docker/ docker/
rsync -av repository/scripts/ scripts/
rsync -av repository/docs/ docs/

# 2. Migrar DEV
./scripts/upgrade-odoo19.sh dev

# 3. Validar DEV
./scripts/validate-odoo19.sh dev

# 4. Si DEV OK → migrar TEST (misma versión exacta)
./scripts/upgrade-odoo19.sh test
./scripts/validate-odoo19.sh test

# 5. Healthcheck completo
./scripts/healthcheck.sh
```

---

## Procedimiento manual (paso a paso)

### Fase A — Backup

```bash
/opt/odoo-projects/hellenia/scripts/backup-dev.sh
/opt/odoo-projects/hellenia/scripts/backup-test.sh
/opt/odoo-projects/hellenia/scripts/backup-production-current.sh  # referencia, prod intacta
```

### Fase B — DEV

> **Nota:** Si la BD proviene de Odoo 18, el upgrade in-place puede fallar
> (`invalid input syntax for type json`). En ese caso usar recreación limpia:

```bash
/opt/odoo-projects/hellenia/scripts/recreate-db-odoo19.sh dev
```

```bash
cd /opt/odoo-projects/hellenia/docker/dev

# Editar compose: image: odoo:19.0-20260619
docker compose --env-file ../../config/dev/.env pull odoo
docker compose --env-file ../../config/dev/.env up -d odoo

# Esperar arranque (~60s) — Odoo migra BD automáticamente
sleep 60

# Verificar logs
docker logs hellenia-dev-odoo-1 --tail 50

# Forzar upgrade módulo base si necesario
source ../../config/dev/.env
docker exec hellenia-dev-odoo-1 odoo \
  -d hellenia_dev --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -u base --stop-after-init
docker compose --env-file ../../config/dev/.env restart odoo
```

### Fase C — Validación DEV

```bash
# Versión vía API
curl -sS -X POST 'https://dev.hellenia.cloud/web/webclient/version_info' \
  -H 'Content-Type: application/json' -d '{}' | jq .result.server_version
# Esperado: "19.0-20260619"

# Login page
curl -sS -o /dev/null -w '%{http_code}\n' https://dev.hellenia.cloud/web/login
# Esperado: 200

# Sin tracebacks
docker logs hellenia-dev-odoo-1 2>&1 | grep -i traceback && echo FAIL || echo OK
```

### Fase D — TEST (solo si DEV estable)

Repetir Fase B/C con:
- `docker/test/`
- `hellenia-test-odoo-1`
- `hellenia_test`
- `https://test.hellenia.cloud`

---

## Validaciones ejecutadas

| # | Validación | DEV | TEST | PROD |
|---|------------|-----|------|------|
| 1 | Contenedor Odoo running | | | N/A |
| 2 | Contenedor DB running | | | N/A |
| 3 | `version_info` = 19.0-20260619 | | | 18.x |
| 4 | `/web/login` HTTP 200 | | | 303 |
| 5 | SSL Let's Encrypt válido | | | — |
| 6 | Traefik routing OK | | | — |
| 7 | Sin tracebacks en logs | | | — |
| 8 | `l10n_do` presente en imagen | | | — |
| 9 | Producción intacta | — | — | ✅ |
| 10 | healthcheck.sh OK | | | |

*(Completar timestamps en sección Resultados tras ejecución)*

---

## Rollback

Ver `docs/ROLLBACK.md`. Resumen:

```bash
# Restaurar imagen Odoo 18 en compose
image: odoo:18.0-20260619

cd /opt/odoo-projects/hellenia/docker/dev  # o test
docker compose --env-file ../../config/dev/.env up -d odoo

# Si BD corrupta: restaurar backup pre-migración
```

Backups pre-migración en:
- `/opt/odoo-projects/hellenia/backups/dev/`
- `/opt/odoo-projects/hellenia/backups/test/`

---

## Post-migración (NO ejecutar aún)

Bloqueado hasta aprobación explícita:

- [ ] Wizard configuración empresa Hellenia
- [ ] Instalación `l10n_do`
- [ ] Creación usuarios (incl. `it@justech.do`)
- [ ] Migración producción a Odoo 19
- [ ] Evaluación Odoo Enterprise para eNCF

---

## Resultados de migración

| Campo | Valor |
|-------|-------|
| Commit Git | `5ba7daf` / `cursor/odoo19-migration-dev-test-dd85` |
| Tag Odoo | `19.0-20260619` |
| DEV migrado | ✅ 2026-06-30 01:07 UTC |
| TEST migrado | ✅ 2026-06-30 01:08 UTC |
| PROD | Sin cambios (`odoo:18`) |
| Wizard ejecutado | No |
| Estrategia BD | Recreación limpia (`-i base`) — upgrade in-place 18→19 falló por incompatibilidad JSON |

### Validaciones finales (2026-06-30)

| # | Validación | DEV | TEST | PROD |
|---|------------|-----|------|------|
| 1 | Contenedor Odoo running | ✅ | ✅ | ✅ |
| 2 | Contenedor DB running | ✅ | ✅ | ✅ |
| 3 | `version_info` = 19.0-20260619 | ✅ | ✅ | 18.x |
| 4 | `/web/login` HTTP 200 | ✅ | ✅ | 303 |
| 5 | SSL Let's Encrypt válido | ✅ | ✅ | — |
| 6 | Traefik routing OK | ✅ | ✅ | ✅ |
| 7 | Sin tracebacks recientes | ✅ | ✅ | — |
| 8 | `l10n_do` v2.0 en imagen | ✅ | ✅ | — |
| 9 | Producción intacta | — | — | ✅ |
| 10 | healthcheck.sh OK | ✅ | ✅ | ✅ |
