# Certificación de rollback — Fase 13.8

**Fecha:** 2026-06-30  
**Ambiente de prueba:** TEST únicamente (PROD no tocado)

---

## Resumen

| Capacidad | Estado | Script |
|-----------|--------|--------|
| Backup BD + filestore + custom | Certificado | `backup-test.sh`, `backup-hellenia-prod.sh` |
| Restore BD + filestore + custom | Certificado | `restore-test.sh`, `restore-hellenia-prod.sh` |
| Rollback Docker Compose | Certificado | Backup incluye `docker-compose.yml` |
| Rollback módulos | Vía restore BD + filestore | Incluido en pg_dumpall |
| Simulación automatizada | Certificado | `validate-rollback-test.sh` |
| Backup pre-restore automático | Sí | Todos los restore-* |

---

## Artefactos de backup

Cada backup timestamp contiene:

| Archivo | Contenido | Rollback |
|---------|-----------|----------|
| `postgres_all.sql.gz` | Dump completo PostgreSQL | BD |
| `filestore.tar.gz` | `/var/lib/odoo` (adjuntos, sesiones) | Filestore |
| `custom.tar.gz` | Módulos custom | Módulos |
| `docker-compose.yml` | Compose del momento | Docker/Traefik |
| `odoo.conf` | Configuración Odoo | Config |
| `.env` | Variables ambiente | Credenciales/rutas |
| `MANIFEST.txt` | Metadatos | Auditoría |

---

## Procedimientos

### Rollback PROD (solo tras fallo en promoción)

```bash
# 1. Identificar backup pre-promoción
ls -1dt /opt/odoo-projects/hellenia/backups/hellenia-prod/20* | head -1

# 2. Restaurar (crea backup de seguridad automático antes)
bash scripts/restore-hellenia-prod.sh /opt/odoo-projects/hellenia/backups/hellenia-prod/YYYY-MM-DD_HHMM

# 3. Validar
bash scripts/healthcheck-full.sh prod
```

### Rollback TEST (simulación / regresión)

```bash
# Dry-run (verifica artefactos, sin restore destructivo)
bash scripts/validate-rollback-test.sh

# Simulación completa
FULL_SIMULATION=1 bash scripts/validate-rollback-test.sh
```

---

## Tiempos de recuperación estimados (RTO)

Basado en procedimiento documentado (valores orientativos según tamaño BD):

| Fase | Operación | Tiempo estimado |
|------|-----------|-----------------|
| T1 | Backup seguridad pre-rollback | 2–5 min |
| T2 | Stop Odoo | < 30 s |
| T3 | Restore PostgreSQL (gunzip + psql) | 3–15 min |
| T4 | Restore filestore (tar) | 1–10 min |
| T5 | Restore custom (tar) | < 1 min |
| T6 | Start Odoo + healthcheck | 2–5 min |
| **RTO total** | | **10–35 min** |

Evidencia de corrida: `evidence/rollback-certification-test-*.json`

---

## Validaciones de integridad

`validate-rollback-test.sh` (dry-run) verifica:

1. Scripts `backup-test.sh`, `restore-test.sh`, `healthcheck-full.sh` existen
2. Backup reciente creado
3. `gunzip -t` sobre dump PostgreSQL
4. `tar -t` sobre filestore y custom
5. `docker-compose.yml` presente en backup para rollback Traefik

Con `FULL_SIMULATION=1` además:

6. Ejecuta `restore-test.sh` completo
7. Ejecuta `healthcheck-full.sh test` post-rollback

---

## Rollback por capa

| Capa | Método | Reversible |
|------|--------|------------|
| Módulos Odoo | Restore `postgres_all.sql.gz` (tabla `ir_module_module`) | Sí |
| Docker / Traefik | Restaurar `docker-compose.yml` del backup + `docker compose up -d --force-recreate` | Sí |
| Base de datos | `restore-*-prod.sh` / `restore-test.sh` | Sí |
| Filestore | `filestore.tar.gz` en restore | Sí |
| Git / código | `git checkout <commit-anterior>` + redeploy | Sí |

---

## Criterios PASS

- [x] Backup incluye todos los artefactos requeridos
- [x] Restore crea backup de seguridad antes de actuar
- [x] Procedimiento documentado para PROD y TEST
- [x] Script de simulación automatizada en TEST
- [ ] FULL_SIMULATION ejecutado en servidor (requiere Docker en VPS)

---

## Conclusión

El rollback está **certificado a nivel de proceso y scripts**. La simulación completa (`FULL_SIMULATION=1`) debe ejecutarse en el VPS TEST antes del Go-Live para registrar RTO real en `evidence/rollback-certification-test-*.json`.

**PROD no fue modificado ni restaurado durante Fase 13.8.**
