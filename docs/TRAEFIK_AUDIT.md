# Auditoría Traefik — Fase 13.8

**Fecha:** 2026-06-30  
**Incidente previo:** HTTP 404 en `odoo.hellenia.cloud` (Fase 13.7 RCA)

---

## Resumen

| Aspecto | Estado |
|---------|--------|
| Fuente única de labels | `docker/lib/traefik-odoo.yaml` |
| Paridad DEV / TEST / PROD | Unificada vía `include` |
| Service explícito HTTP | Sí |
| Service explícito WebSocket | Sí |
| TLS explícito | Sí (`tls=true` + `certresolver=letsencrypt`) |
| Middleware explícito | Sí (`{project}-secure@docker`) |
| Riesgo 404 por autodetección | **Mitigado** |

---

## Causa raíz del 404 (referencia)

Traefik no pudo enlazar automáticamente el router `hellenia-prod` cuando coexistían dos servicios (`hellenia-prod` y `hellenia-prod-ws`) sin label `.service` en el router HTTP.

**Error:** `Router hellenia-prod cannot be linked automatically with multiple Services`

---

## Arquitectura estándar

```
Internet → Traefik (websecure:443)
              │
              ├─ Router {project}      → Service {project}     → :8069 (Odoo HTTP)
              │     Host(ODOO_PUBLIC_HOST)
              │     middleware: {project}-secure
              │
              └─ Router {project}-ws   → Service {project}-ws  → :8072 (gevent)
                    Host + Path(/websocket|/longpolling)
                    priority=100
                    middleware: {project}-secure
```

---

## Labels obligatorios (fuente única)

Archivo: `docker/lib/traefik-odoo.yaml`

| Label | Propósito |
|-------|-----------|
| `traefik.enable=true` | Habilitar descubrimiento |
| `routers.{project}.rule` | `Host(\`${ODOO_PUBLIC_HOST}\`)` |
| `routers.{project}.entrypoints` | `websecure` |
| `routers.{project}.tls` | `true` |
| `routers.{project}.tls.certresolver` | `letsencrypt` |
| `routers.{project}.service` | `{project}` — **crítico anti-404** |
| `routers.{project}.middlewares` | `{project}-secure@docker` |
| `services.{project}.loadbalancer.server.port` | `8069` |
| `middlewares.{project}-secure.headers.sslredirect` | `true` |
| `middlewares.{project}-secure.headers.customrequestheaders.X-Forwarded-Proto` | `https` |
| `routers.{project}-ws.*` | Misma estructura para WebSocket |
| `routers.{project}-ws.priority` | `100` (gana sobre router HTTP en paths WS) |
| `services.{project}-ws.loadbalancer.server.port` | `8072` |

---

## Consumo por ambiente

| Ambiente | Compose | `ODOO_PUBLIC_HOST` |
|----------|---------|-------------------|
| DEV | `docker/dev/docker-compose.yml` | `dev.hellenia.cloud` |
| TEST | `docker/test/docker-compose.yml` | `test.hellenia.cloud` |
| PROD | `docker/production/docker-compose.yml` | `odoo.hellenia.cloud` |

Todos usan:

```yaml
include:
  - path: ../lib/traefik-odoo.yaml

services:
  odoo:
    labels: *odoo-traefik-labels
```

---

## Configuraciones eliminadas / unificadas

| Antes | Después |
|-------|---------|
| Labels duplicados inline en cada compose | Un solo archivo `traefik-odoo.yaml` |
| TEST sin `tls=true` | `tls=true` en todos |
| DEV sin router WebSocket | Paridad WS en todos |
| PROD sin middleware | Middleware `secure` en todos |
| `Host(\`test.${TRAEFIK_HOST}\`)` vs `ODOO_PUBLIC_HOST` | Solo `ODOO_PUBLIC_HOST` |

---

## Validación

```bash
# Detectar error Traefik 404
docker logs traefik-traefik-1 2>&1 | grep "cannot be linked automatically"

# Healthcheck completo
bash scripts/healthcheck-full.sh test
```

Criterio: comando grep sin resultados + `websocket_route` PASS + `https_login` HTTP 200.

---

## ¿Puede volver a ocurrir el 404?

**Riesgo residual bajo** si:

1. Se mantiene `docker/lib/traefik-odoo.yaml` como única fuente
2. No se añaden labels Traefik adicionales sin `.service` explícito
3. `audit-deployment-pipeline.sh` pasa antes de cada promoción
4. `healthcheck-full.sh` valida `traefik_router_link` y `websocket_route`

**Riesgo alto** si se modifica Traefik en PROD sin pasar por TEST.
