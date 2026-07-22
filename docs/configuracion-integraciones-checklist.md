# Centro de Configuración — Checklist producción

## Variables opcionales nuevas

```env
JAIOS_CREDENTIAL_ENCRYPTION_KEY=<clave-dedicada-32+chars>
APP_ENV=production
```

Si no se define `JAIOS_CREDENTIAL_ENCRYPTION_KEY`, se usa `APP_SECRET_KEY`.

## Migración

```bash
docker compose exec backend alembic upgrade head
# 031_integration_settings
```

## Permisos

Los endpoints `/api/v1/settings/*` requieren rol **admin viewer** (lectura) o **admin mutator** (escritura).

## Validación pre-deploy

- [ ] `/configuracion` — hub con ambiente y accesos
- [ ] `/configuracion/integraciones` — tarjetas de estado
- [ ] `/configuracion/m365` — guardar + probar + OAuth usuario
- [ ] `/configuracion/odoo` — guardar URL/DB/user/API key + probar
- [ ] `/configuracion/apis` — LLM keys enmascaradas
- [ ] `/configuracion/repositorios` — bindings + sync
- [ ] `/configuracion/estado` — health servicios
- [ ] `/configuracion/auditoria` — eventos settings.*

## Seguridad

- Secretos cifrados con Fernet en `tenant_integration_settings.secrets_encrypted`
- Frontend nunca recibe valores completos de secretos (solo `masked`)
- Auditoría sin valores secretos en `details`

## Pendiente post-MVP

- WhatsApp Web QR en UI (sesión bridge)
- Picker visual de carpetas OneDrive/SharePoint (hoy ruta manual)
- Rotación automática de secretos con historial
- Separación dev/prod en BD (hoy solo `APP_ENV` visual)
