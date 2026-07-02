# Especificación de healthcheck — Fase 13.8

**Script:** `scripts/healthcheck-full.sh`  
**Wrapper:** `scripts/healthcheck.sh`  
**Odoo interno:** `scripts/lib/healthcheck-odoo.py`  
**Resultado:** `PASS` / `FAIL`

---

## Uso

```bash
# Un ambiente
bash scripts/healthcheck-full.sh test

# Todos los ambientes desplegados
bash scripts/healthcheck.sh all
```

Salida JSON: `evidence/healthcheck-{env}-{timestamp}.json`

---

## Checks implementados

| # | Categoría | Check | Criterio PASS |
|---|-----------|-------|---------------|
| 1 | Docker | `docker_odoo` | Contenedor `{project}-odoo-1` running |
| 2 | Docker | `docker_postgres` | Contenedor `{project}-db-1` running |
| 3 | PostgreSQL | `postgresql_ready` | `pg_isready` OK |
| 4 | PostgreSQL | `postgresql_database` | BD `ODOO_DB_NAME` existe |
| 5 | Odoo | `odoo_healthcheck` | Docker health = `healthy` |
| 6 | Odoo | `odoo_internal_http` | `curl :8069/web/login` OK |
| 7 | Odoo | `odoo_websocket_port` | Puerto `8072` (gevent) accesible |
| 8 | Traefik | `traefik_container` | `traefik-traefik-1` running |
| 9 | Traefik | `traefik_router_link` | Sin error "cannot be linked automatically" |
| 10 | Traefik | `traefik_router_registered` | Router mencionado en logs |
| 11 | HTTPS | `https_login` | `GET /web/login` → HTTP 200 |
| 12 | HTTPS | `https_tls` | TLS handshake OK |
| 13 | Assets | `assets_static` | FontAwesome estático → HTTP 200 |
| 14 | WebSocket | `websocket_route` | `/websocket` no devuelve 404 Traefik |
| 15 | Fiscal | `odoo_fiscal_modules` | Módulos Justech/Hellenia instalados |
| 16 | NCF | (en odoo) | Secuencia NCF configurada |
| 17 | DGII | (en odoo) | Acciones 606/607/608 resolvibles |
| 18 | PDF | (en odoo) | Layout `external_layout_hellenia` |
| 19 | Assets PDF | (en odoo) | Bundle `web.report_assets_common` cargable |
| 20 | Contabilidad | (en odoo) | Plan contable accesible |

---

## Variables requeridas (.env)

| Variable | Ejemplo DEV | Ejemplo TEST | Ejemplo PROD |
|----------|-------------|--------------|--------------|
| `COMPOSE_PROJECT_NAME` | hellenia-dev | hellenia-test | hellenia-prod |
| `ODOO_PUBLIC_HOST` | dev.hellenia.cloud | test.hellenia.cloud | odoo.hellenia.cloud |
| `ODOO_DB_NAME` | hellenia_dev | hellenia_test | hellenia_prod |

---

## Integración en pipeline

| Etapa | Healthcheck |
|-------|-------------|
| Post-deploy TEST | `healthcheck-full.sh test` |
| Pre-promoción PROD | `healthcheck-full.sh test` (gate en `promote-to-production.sh`) |
| Post-promoción PROD | `healthcheck-full.sh prod` |
| Post-rollback TEST | `validate-rollback-test.sh` (FULL_SIMULATION=1) |
| Cron monitoreo | `healthcheck.sh prod` (vía `setup-prod-monitoring-cron.sh`) |

---

## Códigos de fallo comunes

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `https_login` HTTP 404 | Router Traefik sin `.service` explícito | Verificar `docker/lib/traefik-odoo.yaml` |
| `websocket_route` HTTP 404 | Falta router `-ws` o `gevent_port` | Verificar compose + `odoo.conf` |
| `traefik_router_link` FAIL | Múltiples services sin enlace | Añadir labels `.service` |
| `odoo_fiscal_modules` FAIL | Módulo no instalado | Corregir en TEST, no en PROD directo |
| `assets_static` FAIL | Filestore/adjuntos huérfanos | Regenerar bundles QWeb |

---

## Formato JSON de salida

```json
{
  "phase": "13.8",
  "environment": "test",
  "url": "https://test.hellenia.cloud",
  "result": "PASS",
  "checks": [
    {"name": "https_login", "status": "PASS", "detail": "HTTP 200"}
  ]
}
```

Odoo interno adicional: `evidence/healthcheck-{env}-{ts}-odoo.json`
