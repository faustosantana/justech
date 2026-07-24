# Phase H — Pre-Deploy Gate & Controlled Production Deploy

**Fecha:** 2026-07-24  
**URL:** https://jaios.justech.do  
**Veredicto:** **DEPLOY CON OBSERVACIONES**

---

## 1. Auditoría stack real (Gate 0) — PASS

| Ítem | Valor |
|------|-------|
| Host | `vmi3364393` · `/opt/jaios-app` |
| Backend image (antes) | `jaios-app-backend:lottery-position-multi-20260723b` |
| Frontend image (antes) | `jaios-app-frontend:lottery-position-multi-20260723` |
| ASGI / arranque | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| Slim server | **No** (Producción no usa `rc_nr_dev_server`) |
| `integration_connector` | Presente **dentro de la imagen** (no en el tree host incompleto) |
| Python | 3.12.13 |
| Alembic | `060_lottery_ai_alerting_closeout` |
| DB | `postgres:5432/jaios` (compose) |
| `LOTTERY_SYNC_WRITE_ENABLED` | `true` (se dejó sin cambiar) |
| Sync worker | `python -m app.lottery.sync.worker` (imagen backend) |
| Proxy | compose `gateway` nginx + NPM 80/443 |
| Git host | dirty/`feat/pr-1.5…` — **runtime = imágenes**, no checkout |

---

## 2. Paridad RC (Gate 1) — PASS

- Bake overlay: `FROM jaios-app-backend:lottery-position-multi-20260723b` + NR files.
- Sanity: `from app.main import app` + OpenAPI incluye NR.
- Frontend: build oficial host `/opt/jaios-app/frontend` → `jaios-app-frontend:numeric-relations-20260724`.
- **Sin stub `admin-nav`** (prod host no lo necesita).
- `eslint.ignoreDuringBuilds` / `typescript.ignoreBuildErrors`: **preexistentes en host prod**, no introducidos por NR.
- Checkout local incompleto vs imagen: documentado; no se usó slim como sustituto de Producción.

## 3. `app.main` / `integration_connector`

- Local git branch: falta schemas (p.ej. `integration_connector`) → `app.main` falla en laptop.
- Producción/imagen: OK.
- Resolución deploy: **overlay bake** (patrón oficial lottery), no slim.

## 4. Build FE sin stubs del feature

- Evidencia: ruta compilada en imagen  
  `/app/.next/server/app/(platform)/lottery/admin/numeric-relations/...`
- Panel público: `https://jaios.justech.do/lottery/admin/numeric-relations` → **200**

## 5. Pruebas

| Suite | Resultado |
|-------|-----------|
| `test_lottery_numeric_relations_*.py` (local) | **47 passed** |
| Smoke parity (contenedor temp, BD prod) | PASS (API+chat) |
| Smoke Producción (Gate 6) | PASS |

## 6. Backup / snapshot (Gate 3)

| Artefacto | Valor |
|-----------|-------|
| Dump | `/var/jaios/backups/pre_numeric_relations_20260724_031625/jaios.dump` (~36MB) |
| SHA256 | `dc5e16be3cdb4a542dbd4351f1fbd2469bdab593dd8cfb5349101d39cc63aaea` |
| `pg_restore -l` | OK (876 TOC lines) |
| Env/compose | copiados en el mismo directorio |
| Rollback images | `*:rollback-pre-numeric-relations-20260724` |
| Snapshot Contabo | **no automatizado** (equivalente: dump+tags) |

## 7–8. Versión anterior / desplegada

| | Imagen |
|--|--------|
| Anterior backend | `lottery-position-multi-20260723b` |
| Anterior frontend | `lottery-position-multi-20260723` |
| **Desplegado backend** | `jaios-app-backend:numeric-relations-20260724` |
| **Desplegado frontend** | `jaios-app-frontend:numeric-relations-20260724` |
| Worker | misma imagen backend NR |

Código fuente validado (laptop): tip `3d0b830` con ancestros NR requeridos.

## 9. Comandos ejecutados (resumen)

1. Overlay `docker build` backend/frontend tags `numeric-relations-20260724`
2. `pg_dump` + tag rollback images
3. Actualizar `docker-compose.harden.yml` → imágenes NR
4. `docker compose … up -d backend frontend lottery-sync-worker`
5. `docker compose … restart gateway` (DNS stale → 502 breve)
6. Smoke Gate 6 vía `https://jaios.justech.do`

## 10. Servicios reiniciados

- backend, frontend, lottery-sync-worker (recreate)
- gateway (restart DNS)

## 11–12. Smoke Producción + chat

| Caso | Resultado |
|------|-----------|
| Tablas 1/2 + grupos separados + rango 1..100 | PASS |
| N=26 Leidsa last 10 | PASS (`draw_id`×10, scores 0) |
| N=34 todas | PASS (ranking/score/metadata, `llm_calculates=false`) |
| N=45 Leidsa+Loteka | PASS consolidado |
| Usuario `usuario` → 403 | PASS |
| Chat 26 last 10 Leidsa | 1× `lottery_analyze_numeric_relations` |
| Chat 45 Leidsa y Loteka (bare) | clarify K |
| Chat 45 + 20 | 1 tool call |
| Chat “Analiza el 26” | pide lotería; no inventa |

## 13. Logs / métricas (Gate 7)

- Errores backend últimos 15m (excl. warning OpenAPI duplicado): **0**
- Conteos draws **91937** pre=post (histórico no alterado)
- Sync flag sigue `true`
- CPU/mem normales en `docker stats`

## 14–15. Sync / histórico

- Overlay **sin** archivos `lottery_sync*`
- `LOTTERY_SYNC_WRITE_ENABLED=true` sin cambio
- Draws/numbers sin disminución

## 16. Nuevo punto de rollback

- Images: `jaios-app-backend|frontend:rollback-pre-numeric-relations-20260724`
- Dump: ruta Gate 3 arriba
- Harden backup: `docker-compose.harden.yml.bak-pre-numeric-relations-20260724`

## 17. Veredicto

### DEPLOY CON OBSERVACIONES

**Listo y operativo en Producción**, con observaciones:

1. **502 ~2 min** post-recreate por IP cacheada en nginx gateway; corregido con `restart gateway`. Incluir restart de gateway en runbooks futuros tras recreate de backend.
2. **Snapshot de proveedor VPS** no tomado automáticamente; backup Fc + tags de rollback verificados.
3. Deuda FE preexistente (`ignoreDuringBuilds` / `ignoreBuildErrors`) permanece en el host de build; no oculta errores del feature NR.

No se ejecutó rollback automático: app.main arrancó, panel 200, motor/chat/permisos OK.
