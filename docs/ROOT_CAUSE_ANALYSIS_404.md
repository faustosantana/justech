# Root Cause Analysis — 404 en odoo.hellenia.cloud

**Fase:** 13.7  
**Incidente:** `https://odoo.hellenia.cloud` responde `404 page not found`  
**Fecha análisis:** 2026-06-30  
**Estado PROD al analizar:** 404 (sin reparar en este análisis)  
**Estado TEST:** Operativo (200)

---

## 1. Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué falló? | Router Traefik `hellenia-prod` no se registró → ninguna ruta HTTP para `odoo.hellenia.cloud` |
| ¿Commit causante? | **`4da84c3`** — Fase 13.4 hardening websocket Traefik |
| ¿Por qué TEST no lo detectó? | TEST no tenía router websocket ni segundo servicio Traefik en el mismo contenedor |
| ¿Odoo estaba caído? | **No** — contenedor `hellenia-prod-odoo-1` healthy, responde en :8069 internamente |
| ¿Fix propuesto? | Añadir label `traefik.http.routers.hellenia-prod.service=hellenia-prod` |

---

## 2. Síntoma

```http
HTTP/2 404
content-type: text/plain; charset=utf-8
```

Respuesta típica de **Traefik** cuando no existe router que coincida con el `Host` solicitado.

| URL | Código | Servidor |
|-----|--------|----------|
| `https://odoo.hellenia.cloud` | **404** | Traefik |
| `https://test.hellenia.cloud` | **303** → `/odoo` | Odoo/Werkzeug |

---

## 3. Línea de tiempo

| Timestamp (UTC) | Evento |
|-----------------|--------|
| Fase 13.4 | Commit `4da84c3` añade labels websocket `-ws` en `docker/production/docker-compose.yml` |
| Fase 13.4 | Cambio de host `prod.hellenia.cloud` → `odoo.hellenia.cloud` (`ODOO_PUBLIC_HOST`) |
| 2026-06-30 ~16:27 | Fase 13.6 instala `hellenia_reports` en PROD → `docker compose stop/up` recrea contenedor |
| 2026-06-30 ~16:38+ | Traefik registra error repetido al enlazar router `hellenia-prod` |
| 2026-06-30 16:49 | Confirmado 404 externo en `odoo.hellenia.cloud` |

**Disparador inmediato:** Reinicio del contenedor Odoo PROD durante instalación directa en producción (Fase 13.6), lo que hizo que Traefik re-evaluara labels y **rechazara** el router principal.

**Causa raíz estructural:** Configuración Traefik incompleta desde Fase 13.4.

---

## 4. Commit causante

```
commit 4da84c3944be0f3eb9b43908f2949bdf98e5b89c
Author: Cursor Agent
Date:   2026-06-30 16:18:37 2026 +0000

feat(prod): Fase 13.4 hardening — menús, limpieza, websocket Traefik
```

### Archivo modificado

`docker/production/docker-compose.yml`

### Cambios relevantes

| Antes | Después |
|-------|---------|
| Un solo servicio Traefik (`hellenia-prod` → :8069) | Dos servicios: `hellenia-prod` (:8069) + `hellenia-prod-ws` (:8072) |
| Host `prod.${TRAEFIK_HOST}` | Host `${ODOO_PUBLIC_HOST}` (`odoo.hellenia.cloud`) |
| Router WS: **no existía** | Router `hellenia-prod-ws` con `.service` explícito |
| Router HTTP: `.service` **no definido** | Router HTTP: `.service` **sigue sin definir** ← bug |

### Labels Traefik en contenedor PROD (estado incidente)

```yaml
traefik.http.routers.hellenia-prod.rule: Host(`odoo.hellenia.cloud`)
traefik.http.routers.hellenia-prod.entrypoints: websecure
traefik.http.services.hellenia-prod.loadbalancer.server.port: 8069
traefik.http.routers.hellenia-prod-ws.service: hellenia-prod-ws   # ← explícito
traefik.http.services.hellenia-prod-ws.loadbalancer.server.port: 8072
# FALTA: traefik.http.routers.hellenia-prod.service=hellenia-prod
```

---

## 5. Error Traefik (evidencia)

```
ERR Router hellenia-prod cannot be linked automatically with multiple Services: 
    ["hellenia-prod-ws" "hellenia-prod"]
providerName=docker routerName=hellenia-prod
```

**Explicación:** Cuando un contenedor Docker define **más de un servicio** Traefik, el router principal debe especificar explícitamente cuál servicio usar. El router `-ws` lo tiene; el router HTTP principal no.

**Resultado:** Traefik **descarta** el router `hellenia-prod` → 404 para todo el tráfico HTTP/HTTPS principal.

---

## 6. Qué NO causó el 404

| Descartado | Evidencia |
|------------|-----------|
| Odoo caído | `hellenia-prod-odoo-1` healthy, healthcheck :8069 OK |
| Base de datos | `hellenia-prod-db-1` healthy |
| Certificado TLS | 404 ocurre tras TLS; problema es routing, no cert |
| DNS | Resuelve correctamente al VPS |
| Cambio en `hellenia_reports` | Módulo Odoo no afecta Traefik; solo reinició contenedor |

---

## 7. Por qué TEST no detectó el problema

| Factor | TEST | PROD |
|--------|------|------|
| Router websocket `-ws` | No existía hasta Fase 13.7 | Desde 13.4 |
| Servicios Traefik por contenedor | 1 (sin ambigüedad) | 2 (ambiguo) |
| Validación Traefik en CI | No automatizada | No automatizada |
| Despliegue directo PROD | — | Fases 13.4, 13.6 sin pasar por TEST |

TEST funcionaba porque Traefik podía auto-enlazar el único servicio. PROD falló al añadir el segundo servicio sin `.service` en el router principal.

**Lección:** Cualquier cambio en labels Traefik debe probarse en TEST con la **misma topología** (HTTP + WS) antes de promover.

---

## 8. Corrección (certificada en TEST, NO aplicada en PROD)

Añadir en `docker/production/docker-compose.yml`:

```yaml
- traefik.http.routers.${COMPOSE_PROJECT_NAME}.service=${COMPOSE_PROJECT_NAME}
```

**Commit certificado en TEST:** `f918576` (rama `cursor/phase13-7-test-validation-dd85`)

**Validación TEST post-fix:**
- `https://test.hellenia.cloud/web/login` → **HTTP 200**
- Labels websocket añadidos a TEST con misma topología
- Sin errores Traefik en logs al recrear contenedor

---

## 9. Violación de política detectada

| Violación | Fase |
|-----------|------|
| Cambio Traefik desplegado directo en PROD | 13.4 |
| Instalación `hellenia_reports` directo en PROD | 13.6 |
| Sin validación funcional previa en TEST | 13.4, 13.6 |

**Nueva política (Fase 13.7):** DEV → TEST → validación → aprobación → backup → PROD.

---

## 10. Acciones requeridas para restaurar PROD

> **Pendiente de aprobación explícita** — no ejecutado en Fase 13.7.

1. Backup PROD (`scripts/backup-hellenia-prod.sh`)
2. Promover commit `f918576` (mismo validado en TEST)
3. `docker compose up -d --force-recreate odoo` en producción
4. Verificar logs Traefik: sin error `cannot be linked automatically`
5. Confirmar `curl -I https://odoo.hellenia.cloud` → 200/303

Ver [PRODUCTION_PROMOTION_PLAN.md](PRODUCTION_PROMOTION_PLAN.md).
