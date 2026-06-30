# Producción actual — referencia (NO migrada)

> **Estado:** Operativa. **No modificar** hasta aprobación explícita y backup completo.

## Stack existente

| Campo | Valor |
|-------|-------|
| Ruta Compose | `/docker/odoo-pecv/docker-compose.yml` |
| Variables | `/docker/odoo-pecv/.env` |
| Proyecto Compose | `odoo-pecv` |
| Contenedor Odoo | `odoo-pecv-odoo-1` |
| Contenedor DB | `odoo-pecv-db-1` |
| Imagen Odoo | `odoo:18` |
| Imagen PostgreSQL | `postgres:17-alpine` |
| Proxy | Traefik (`traefik-traefik-1`) |
| Dominio actual | `odoo-pecv.srv1784296.hstgr.cloud` |
| Dominio futuro | `odoo.hellenia.cloud` |

## Volúmenes

| Volumen | Propósito |
|---------|-----------|
| `odoo-pecv_db` | PostgreSQL |
| `odoo-pecv_odoo-data` | Filestore |
| `odoo-pecv_odoo-addons` | Addons (vacío) |

## Regla

No detener, no borrar, no modificar sin backup + aprobación.
Usar `scripts/backup-production-current.sh` antes de cualquier cambio.
