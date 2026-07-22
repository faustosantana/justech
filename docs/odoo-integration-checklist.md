# Integración Odoo — Checklist producción

## Variables `.env` requeridas

```env
ODOO_URL=https://odoo.ejemplo.com
ODOO_DB=justech
ODOO_USERNAME=integracion@justech.do
ODOO_API_KEY=<api-key-odoo>
ODOO_READ_ONLY=false   # true = bloquea escrituras aunque Odoo permita
```

## Migración

```bash
docker compose exec backend alembic upgrade head
# Aplica 030_odoo_permission_cache
```

## Validación pre-deploy

- [ ] `GET /api/v1/odoo/config` — mensaje real (no genérico)
- [ ] `GET /api/v1/odoo/health` — conexión OK
- [ ] `GET /api/v1/odoo/me` — permisos en respuesta
- [ ] Vincular usuario: `POST /api/v1/odoo/link-user`
- [ ] Sync permisos: `POST /api/v1/odoo/permissions/sync`
- [ ] Listar clientes/productos con empresa activa
- [ ] Crear cotización de prueba (si `ODOO_READ_ONLY=false` y permiso Odoo)
- [ ] Crear tarea de prueba
- [ ] `POST /api/v1/odoo/actions` desde assistant/DGCP
- [ ] UI `/odoo/settings` sin error genérico
- [ ] Multiempresa: solo empresas de `allowed_company_ids`

## Seguridad

- No exponer `ODOO_API_KEY` en frontend
- Permisos = caché de `ir.model.access` + grupos Odoo del usuario vinculado
- Re-sync: login (vía `/me`), cada 12h, manual en settings
- Auditoría: `odoo.quotation_created`, `odoo.task_created`, `odoo.permissions_synced`

## Pendiente opcional post-MVP

- PDF nativo Odoo en cotizaciones (hoy fallback JAIOS)
- UI búsqueda cliente por nombre en crear cotización
- Re-auth periódica si Odoo revoca grupos (webhook interno)
