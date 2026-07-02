# Plan de Backup y Recuperación

**Fase:** 10 | **Fecha:** 2026-06-30

---

## 1. Política de retención

| Tier | Retención | Marcador |
|------|-----------|----------|
| Diario | 7 días | `backups/<env>/YYYY-MM-DD_HHMM` |
| Semanal | 4 semanas | `*_weekly` symlink |
| Mensual | 6 meses | `*_monthly` symlink |

---

## 2. Scripts por ambiente

| Ambiente | Script | Restore |
|----------|--------|---------|
| DEV | `backup-dev.sh` | `restore-dev.sh` |
| TEST | `backup-test.sh` | `restore-test.sh` |
| odoo-pecv | `backup-production-current.sh` | Manual (ver abajo) |
| hellenia-prod (futuro) | Crear `backup-prod.sh` al Go-Live | `restore-prod.sh` |

---

## 3. Contenido backup estándar

| Archivo | Contenido |
|---------|-----------|
| `postgres_all.sql.gz` | Dump PostgreSQL completo |
| `filestore.tar.gz` | Filestore Odoo |
| `custom.tar.gz` | Módulos custom (DEV/TEST) |
| `docker-compose.yml` | Compose referencia |
| `odoo.conf` | Config referencia |
| `.env` | Variables (proteger) |
| `MANIFEST.txt` | Metadata |

**Producción odoo-pecv adicional:** `addons_volume.tar.gz`, `PRODUCTION-REFERENCE.md`

---

## 4. Backups Fase 10 (verificados)

| Ambiente | Timestamp | Ruta |
|----------|-----------|------|
| DEV | 2026-06-30_1421 | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_1421` |
| TEST | 2026-06-30_1421 | `/opt/odoo-projects/hellenia/backups/test/2026-06-30_1421` |
| odoo-pecv | 2026-06-30_1421 | `/opt/odoo-projects/hellenia/backups/production/2026-06-30_1421` |

**Verificación DEV:** `verify-backup-dev.sh` — PASS

---

## 5. Recuperación DEV/TEST

```bash
./scripts/restore-dev.sh /opt/odoo-projects/hellenia/backups/dev/<TIMESTAMP>
./scripts/restore-test.sh /opt/odoo-projects/hellenia/backups/test/<TIMESTAMP>
```

Cada restore crea backup de seguridad pre-restore.

---

## 6. Recuperación odoo-pecv

1. Detener Odoo: `docker compose -f /docker/odoo-pecv/docker-compose.yml stop odoo`
2. Restaurar PostgreSQL desde `postgres_all.sql.gz`
3. Restaurar volumen `odoo-pecv_odoo-data` desde `filestore.tar.gz`
4. Reiniciar stack
5. Smoke test login

**RTO:** 1–2 h | **RPO:** Último backup (máx. 24h si cron diario)

---

## 7. Backup post-Go-Live (configurar)

| Item | Recomendación |
|------|---------------|
| Frecuencia | Diario 02:00 AST + pre-deploy |
| Destino | Mismo VPS + copia off-site (S3/Backblaze) |
| Prueba restore | Mensual |
| Monitoreo | Alerta si backup falla |

---

## 8. Estado Fase 10

**PASS** — triple backup verificado; procedimiento prod futuro documentado.

**Observación P1:** Configurar `backup-prod.sh` y cron al desplegar hellenia-prod.
