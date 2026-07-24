# Numeric Relations — Production Release

**Versión:** `lottery-numeric-relations-v1.0.0`  
**Estado final:** OPERATIVO EN PRODUCCIÓN (DEPLOY CON OBSERVACIONES — cerrado)  
**Fecha de despliegue:** 2026-07-24  

---

## Commit exacto (runtime desplegado)

| Campo | Valor |
|-------|-------|
| Tag | `lottery-numeric-relations-v1.0.0` |
| Commit (bake / código en imágenes) | `3d0b8309d549e8e20f72e1f2f4f0bfe992c59e0c` |
| Mensaje | `build(lottery): publish numeric relations DEV RC and Phase G docs` |
| Rama | `feature/lottery-numeric-relations-motor` |

Ancestros de release incluidos en el tag:

| Commit | Descripción |
|--------|-------------|
| `459a799` | Motor (tablas + análisis histórico) |
| `12e5542` | UI admin, API, tool/chat |
| `3f4d134` | Validación agrupación por `draw_id` |
| `cf4a732` | Fase E metadata |
| `255cf9c` | Hardening UAT Fase F |
| `4c8e748` | Cierre reporte Fase F |
| `8d1e1cd` | Fix multi-lotería intent/planner |
| `e9ebaa9` | Packaging RC + checklist |
| `3d0b830` | Smoke/docs Phase G / tip de bake |

Documentación de cierre posterior al bake (no altera runtime):

- `3b6a38a` — reporte Phase H  
- commits documentales posteriores en la misma rama (este archivo)

---

## Imágenes Docker (Producción)

| Servicio | Imagen |
|----------|--------|
| Backend | `jaios-app-backend:numeric-relations-20260724` |
| Worker sync | `jaios-app-backend:numeric-relations-20260724` |
| Frontend | `jaios-app-frontend:numeric-relations-20260724` |

**Entrypoint:** `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`

---

## URLs

| Recurso | URL |
|---------|-----|
| App | https://jaios.justech.do |
| Health | https://jaios.justech.do/api/v1/health |
| Panel NR | https://jaios.justech.do/lottery/admin/numeric-relations |
| API analyze | `POST /api/v1/lottery/admin/numeric-relations/analyze` |

---

## Backup

| Campo | Valor |
|-------|-------|
| Dump | `/var/jaios/backups/pre_numeric_relations_20260724_031625/jaios.dump` |
| SHA256 | `dc5e16be3cdb4a542dbd4351f1fbd2469bdab593dd8cfb5349101d39cc63aaea` |
| Host app | `/opt/jaios-app` |
| Harden backup | `docker-compose.harden.yml.bak-pre-numeric-relations-20260724` |

---

## Rollback

| Recurso | Valor |
|---------|-------|
| Backend | `jaios-app-backend:rollback-pre-numeric-relations-20260724` |
| Frontend | `jaios-app-frontend:rollback-pre-numeric-relations-20260724` |
| (= pre-deploy) | `lottery-position-multi-20260723b` / `lottery-position-multi-20260723` |
| Dev tag histórico | `restore/lottery-pre-numeric-relations-motor-20260723` → `25ccd8aa` (no sustituye backup prod) |

Procedimiento: restaurar pins en `docker-compose.harden.yml` a las imágenes `rollback-pre-numeric-relations-20260724`, `compose up -d backend frontend lottery-sync-worker`, reiniciar `gateway` si hay 502 por DNS, smoke health. Restaurar dump BD solo si hubiera corrupción.

---

## Pruebas

| Prueba | Resultado |
|--------|-----------|
| Suite `test_lottery_numeric_relations_*.py` | **47 passed** |
| Smoke Producción (Gate 6) | **PASS** |
| Monitoreo post-deploy (Gate 7) | **PASS** (sin errores críticos) |
| Histórico (draws) | Intactos (91937 pre = post) |
| Sync | No modificado; `LOTTERY_SYNC_WRITE_ENABLED=true` sin cambio |
| Metodología / rango 1..100 | Intacta |

Evidencia detallada:  
`docs/lottery/numeric_relations_artifacts/phase_h/PHASE_H_PRODUCTION_DEPLOY_REPORT.md`

---

## Riesgos aceptados (cierre)

1. **502 breve post-recreate** por caché de IP del backend en nginx gateway — resuelto con restart de gateway; documentado para runbooks.
2. **Snapshot Contabo** no automatizado — aceptado temporalmente por dump verificado + imágenes rollback + procedimiento.
3. **`ignoreDuringBuilds` / `ignoreBuildErrors`** preexistentes en el host de build de Producción — no introducidos por Numeric Relations.

---

## Estado final

**Numeric Relations v1.0.0 está oficialmente cerrado e operativo en Producción.**

Cualquier mejora futura (p. ej. snapshot Contabo automatizado, limpieza de deuda ESLint del host, UX del panel) debe abrirse como **nueva fase o ticket independiente**. No se autorizan más cambios en este alcance.
