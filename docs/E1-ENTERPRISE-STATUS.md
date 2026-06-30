# Estado Fase E1 — Enterprise DEV

**Fecha:** 2026-06-30  
**E1a:** ✅ **Completado** — imagen `hellenia-odoo:19-enterprise` en DEV  
**Estrategia:** Enterprise + custom horneados en imagen Docker (sin volumen)

---

## Resultado E1a (2026-06-30)

| Item | Valor |
|------|-------|
| Archivo fuente | `odoo_19.0+e.20260629.tar.gz` |
| SHA256 | `667ad231f9b9800ed2f06029d9c5c639af53c3255f94cca2e5643ee7502eb924` |
| Imagen DEV | `hellenia-odoo:19-enterprise` (~5.16 GB) |
| Base image | `odoo:19.0-20260619` |
| Extracción | `/opt/odoo-projects/hellenia/enterprise/odoo-19.0+e.20260629/` |
| Addons Enterprise | `/opt/odoo-projects/hellenia/enterprise/addons/` |
| `web_enterprise` | ✅ instalado en BD |
| Backup pre-E1a | `backups/dev/2026-06-30_0222` |
| URL DEV | https://dev.hellenia.cloud — HTTP 200 |
| Versión Odoo DEV | `19.0+e-20260619` (serie 19.0) |

---

## Validaciones ejecutadas

| Check | Resultado |
|-------|-----------|
| Integridad tarball | ✅ |
| Docker DEV | ✅ `hellenia-dev-odoo-1` healthy |
| PostgreSQL DEV | ✅ |
| HTTPS / Traefik | ✅ |
| `web_enterprise` en imagen + BD | ✅ |
| Sin volumen `/mnt/enterprise` | ✅ |
| l10n_do / l10n_do_edi | ✅ no instalados |
| Licencia registrada | ⛔ no (por diseño) |
| Wizard / usuarios | ⛔ no |
| TEST | ✅ Community `odoo:19.0-20260619` sin cambios |
| PROD | ✅ Odoo 18 intacta |

---

## Pendiente (fases posteriores)

| Fase | Estado |
|------|--------|
| E1b — Registrar licencia `M260616306091776` | ⏳ Pendiente aprobación |
| E1c — l10n_do | ⏳ Pendiente |
| Wizard / usuarios | ⛔ Bloqueado |

---

## Rollback

Si se requiere revertir E1a en DEV:

```bash
/opt/odoo-projects/hellenia/scripts/restore-dev.sh \
  /opt/odoo-projects/hellenia/backups/dev/2026-06-30_0222
cp docker/dev/docker-compose.community.yml docker/dev/docker-compose.yml
cp config/dev/odoo.conf.community config/dev/odoo.conf
cd docker/dev && docker compose --env-file ../../config/dev/.env up -d --force-recreate odoo
```

Ver [ROLLBACK.md](ROLLBACK.md).
