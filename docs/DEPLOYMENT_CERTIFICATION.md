# Certificación de despliegue — Fase 13.8

**Fecha:** 2026-06-30  
**Ambientes auditados:** DEV, TEST, PROD (sin modificar PROD)

---

## Resultado global

| Certificación | Estado |
|---------------|--------|
| Paridad arquitectura Traefik | **PASS** |
| Variables .env estandarizadas | **PASS** |
| Pipeline de promoción con gates | **PASS** |
| Healthcheck completo | **PASS** (spec + scripts) |
| Auditoría automatizada | **PASS** |
| Promoción a PROD ejecutada | **NO** (política 13.7) |

---

## Checklist de certificación

### Infraestructura

- [x] `docker/lib/traefik-odoo.yaml` — fuente única labels
- [x] DEV / TEST / PROD usan `include` + anchor `*odoo-traefik-labels`
- [x] `ODOO_PUBLIC_HOST` en los tres `.env.example`
- [x] `gevent_port = 8072` en odoo.conf DEV, TEST, PROD example
- [x] Router HTTP con `.service` explícito
- [x] Router WS con `.service` explícito y `priority=100`
- [x] Middleware `{project}-secure@docker` declarado

### Proceso

- [x] Flujo DEV → TEST → certificación documentado
- [x] `promote-to-production.sh` exige aprobación + commit + backup
- [x] `deploy-hellenia-prod.sh` marcado como bootstrap only
- [x] Healthcheck pre y post promoción integrado
- [x] Smoke test HTTP 200 en URL pública

### Validación automatizada

```bash
bash scripts/audit-deployment-pipeline.sh
# RESULTADO: PASS
```

Evidencia: `evidence/deployment-pipeline-audit-*.json`

---

## Healthcheck — cobertura certificada

Ver `docs/HEALTHCHECK_SPEC.md` — 20 checks en 5 capas:

1. Docker (contenedores)
2. PostgreSQL (ready + BD)
3. Odoo (health + HTTP + gevent)
4. Traefik (container + router link + HTTPS + WS)
5. Fiscal (módulos, NCF, DGII, PDF, contabilidad)

---

## Commit de referencia

Rama: `cursor/phase13-8-deployment-audit-dd85`

Incluye:

- `docker/lib/traefik-odoo.yaml`
- Actualización compose DEV/TEST/PROD
- `scripts/healthcheck-full.sh`
- `scripts/promote-to-production.sh`
- `scripts/validate-rollback-test.sh`
- `scripts/audit-deployment-pipeline.sh`
- Documentación Fase 13.8

---

## Pre-requisitos Go-Live

| # | Requisito | Estado |
|---|-----------|--------|
| 1 | Fase 13.7 TEST PASS | Completado |
| 2 | Fase 13.8 pipeline certificado | Completado |
| 3 | Aprobación explícita promoción | Pendiente usuario |
| 4 | Backup PROD pre-promoción | Pendiente ejecución |
| 5 | `promote-to-production.sh` PASS | Pendiente ejecución |
| 6 | `https://odoo.hellenia.cloud` HTTP 200 | Pendiente (PROD en 404) |

---

## Conclusión

La infraestructura y el proceso de despliegue están **certificados para promoción**. La ejecución en PROD permanece bloqueada hasta aprobación explícita y ejecución de `promote-to-production.sh`.
