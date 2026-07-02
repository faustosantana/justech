# Auditoría del pipeline de despliegue — Fase 13.8

**Fecha:** 2026-06-30  
**Alcance:** Infraestructura y proceso — sin cambios funcionales

---

## Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Pipeline seguro? | **Sí**, con gates obligatorios en `promote-to-production.sh` |
| ¿Paridad DEV/TEST/PROD? | **Sí** en Traefik, PostgreSQL, healthchecks; DEV usa imagen enterprise horneada (única diferencia intencional) |
| ¿Promoción reproducible? | **Sí**, commit certificado + evidencia TEST + backup |
| ¿PROD modificado en 13.8? | **No** |

---

## Arquitectura por ambiente

| Componente | DEV | TEST | PROD |
|------------|-----|------|------|
| Imagen Odoo | `hellenia-odoo:19-enterprise` (build) | `odoo:19.0-20260619` | `odoo:19.0-20260619` |
| PostgreSQL | `postgres:17-alpine` | `postgres:17-alpine` | `postgres:17-alpine` |
| Traefik labels | `traefik-odoo.yaml` | `traefik-odoo.yaml` | `traefik-odoo.yaml` |
| HTTP + WS routers | Sí | Sí | Sí |
| `gevent_port` | 8072 | 8072 | 8072 |
| `proxy_mode` | true | true | true |
| Dominio | `dev.hellenia.cloud` | `test.hellenia.cloud` | `odoo.hellenia.cloud` |
| BD | `hellenia_dev` | `hellenia_test` | `hellenia_prod` |

**Diferencia aceptada:** DEV monta custom en `/opt/odoo/custom` (imagen horneada); TEST/PROD montan en `/mnt/custom`. Funcionalmente equivalente.

---

## Variables .env (solo difieren dominio/BD/credenciales)

| Variable | DEV | TEST | PROD |
|----------|-----|------|------|
| `COMPOSE_PROJECT_NAME` | hellenia-dev | hellenia-test | hellenia-prod |
| `ODOO_PUBLIC_HOST` | dev.hellenia.cloud | test.hellenia.cloud | odoo.hellenia.cloud |
| `ODOO_DB_NAME` | hellenia_dev | hellenia_test | hellenia_prod |
| `DB_PASSWORD` | único por ambiente | único | único |

Plantillas: `config/{dev,test,production}/.env.example`

---

## Flujo de promoción certificado

```
DEV ──deploy-dev.sh──► desarrollo local
         │
         ▼
TEST ──deploy-test.sh──► validación funcional + healthcheck-full.sh
         │
         ▼
CERTIFICACIÓN ──evidence/*.json (ok: true)──► commit fijado
         │
         ▼
BACKUP PROD ──backup-hellenia-prod.sh──► artefacto timestamp
         │
         ▼
PROMOCIÓN ──promote-to-production.sh──► APPROVE_PROMOTION=1 + CERTIFIED_COMMIT
         │
         ▼
HEALTHCHECK ──healthcheck-full.sh prod──► PASS/FAIL
         │
         ▼
SMOKE TEST ──curl /web/login HTTP 200──►
         │
         ▼
GO LIVE ──confirmación operativa──►
```

---

## Scripts auditados

| Script | Rol | Estado |
|--------|-----|--------|
| `deploy-dev.sh` | Deploy DEV desde Git | OK |
| `deploy-test.sh` | Deploy TEST desde Git | OK |
| `deploy-hellenia-prod.sh` | Bootstrap inicial solamente | WARN — no usar para updates |
| `promote-to-production.sh` | Promoción controlada | **Nuevo** — gates obligatorios |
| `backup-hellenia-prod.sh` | Backup PROD | OK |
| `restore-hellenia-prod.sh` | Restore PROD | OK |
| `backup-test.sh` / `restore-test.sh` | Backup/restore TEST | OK |
| `healthcheck-full.sh` | Healthcheck completo | **Nuevo** |
| `healthcheck.sh` | Wrapper multi-ambiente | Actualizado |
| `validate-rollback-test.sh` | Simulación rollback TEST | **Nuevo** |
| `audit-deployment-pipeline.sh` | Auditoría automatizada | **Nuevo** |

---

## Hallazgos corregidos en Fase 13.8

| ID | Hallazgo | Corrección |
|----|----------|------------|
| H1 | Labels Traefik divergentes entre ambientes | `docker/lib/traefik-odoo.yaml` |
| H2 | DEV sin router WebSocket | Include compartido |
| H3 | TEST sin `tls=true` explícito | Unificado |
| H4 | Sin middleware explícito | `{project}-secure@docker` |
| H5 | `healthcheck.sh` obsoleto (odoo-pecv, URLs incorrectas) | Delega a `healthcheck-full.sh` |
| H6 | Sin script de promoción con gates | `promote-to-production.sh` |
| H7 | `deploy-hellenia-prod.sh` permitía bypass de política | Documentado como bootstrap only |

---

## Evidencia

```bash
bash scripts/audit-deployment-pipeline.sh
# → evidence/deployment-pipeline-audit-*.json (PASS)
```

---

## Política Fase 13.7+ (reforzada)

Prohibido modificar PROD directamente. Toda actualización post-Go-Live debe usar `promote-to-production.sh` con:

- `APPROVE_PROMOTION=1`
- `CERTIFIED_COMMIT=<sha>`
- Evidencia TEST PASS
- Backup previo obligatorio
