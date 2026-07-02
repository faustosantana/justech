# Guía de Despliegue — Producción Odoo 19

**URL objetivo:** https://odoo.hellenia.cloud  
**URL validación pre-corte:** https://prod.hellenia.cloud  
**Estado:** Script automatizado `deploy-hellenia-prod.sh` — **sin cambiar DNS de odoo.hellenia.cloud**

---

## 1. Prerrequisitos

- [x] Rama `feature/justech-l10n-do-mvp` en VPS
- [x] Enterprise addons en `/opt/odoo-projects/hellenia/enterprise`
- [x] Custom addons en `/opt/odoo-projects/hellenia/custom`
- [ ] Registro DNS **A** `prod.hellenia.cloud` → `2.25.69.179` (Let's Encrypt; no modifica `odoo.hellenia.cloud`)

---

## 2. Archivos

| Archivo | Propósito |
|---------|-----------|
| `docker/production/docker-compose.yml` | Stack `hellenia-prod`, Traefik `prod.hellenia.cloud` |
| `config/production/.env` | Variables (derivar de test, no commitear) |
| `config/production/odoo.conf` | workers=2, proxy_mode, dbfilter |
| `scripts/deploy-hellenia-prod.sh` | Orquestador instalación completa |
| `scripts/sync-prod-credentials.sh` | Hashes admin + it@justech.do desde DEV |
| `scripts/register-enterprise-prod.sh` | Licencia `M260616306091776` |
| `scripts/backup-hellenia-prod.sh` | Backup manual/cron |
| `scripts/restore-hellenia-prod.sh` | Restore desde timestamp |
| `scripts/setup-prod-monitoring-cron.sh` | Cron backup + healthcheck |

---

## 3. Despliegue automatizado

```bash
cd /opt/odoo-projects/hellenia
./scripts/deploy-hellenia-prod.sh feature/justech-l10n-do-mvp
```

El script ejecuta: stack Docker → BD `hellenia_prod` → `web_enterprise` → Fase 8 (Golden Config, sin piloto) → Fase 11 (es_DO + módulos) → Justech MVP → credenciales DEV → licencia EE → validaciones → backup → cron.

---

## 4. Traefik y DNS

| Host | Router | Cuándo |
|------|--------|--------|
| `prod.hellenia.cloud` | Activo en despliegue | Validación HTTPS/LE pre-corte |
| `odoo.hellenia.cloud` | **NO activar** | Solo en Go-Live (cambiar label Traefik) |

`web.base.url` en Odoo = `https://odoo.hellenia.cloud` desde el inicio.

---

## 5. Credenciales

Misma política que DEV/TEST: hashes `admin` e `it@justech.do` copiados desde `hellenia_dev` (sin contraseñas nuevas).

---

## 6. Corte Go-Live (futuro)

1. Backup triple final  
2. Cambiar router Traefik a `Host(\`odoo.hellenia.cloud\`)`  
3. DNS ya apunta a VPS — sin cambio si A record existente  
4. Smoke test  
5. Apagar `odoo-pecv` solo con aprobación explícita

