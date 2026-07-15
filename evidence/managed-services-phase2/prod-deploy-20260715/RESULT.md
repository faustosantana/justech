# Despliegue controlado — justech_managed_services

| Campo | Valor |
|---|---|
| Inicio (UTC) | 2026-07-15T22:13:49Z |
| Fin (UTC) | 2026-07-15T22:16:33Z (smoke) |
| Commit | `4e797a1f7ac7cc35e01853d2ac36871e733e5855` |
| Versión instalada | `19.0.2.1.1` |
| Acción | `-i justech_managed_services` únicamente (sin `-u all`) |
| Backup | `/opt/odoo-backups/managed-services-install-20260715_221349/` |
| Rollback | Disponible (`ROLLBACK.md` en el backup) |
| Snapshot VPS | No disponible en esta sesión |

## Backup

- `justech.dump` (50M, TOC 25407, `pg_restore -l` OK)
- `filestore_justech.tar.gz` (371M)
- `custom-addons_pre.tar.gz` (3.5M)

## Smoke test

**Resultado: PASS** (`failed: []`)

Login HTTP 200 · Contactos · CRM · Ventas · Facturas · NCF/e-CF · Helpdesk · Fees · Servicios Administrados · PDF · enlace público HTTP 200 · menú Banco de preguntas.

## Otros módulos

No se ejecutó `-u all`. Dependencias críticas siguen `installed` (CRM, Ventas, Subscriptions, Helpdesk, Account, NCF, e-CF, website, recurring fee).
