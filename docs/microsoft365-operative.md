# Microsoft 365 Operativo — JAIOS (desarrollo)

## Diagnóstico: "conectado" sin datos

| Causa | Síntoma | Corrección |
|-------|---------|------------|
| Token OAuth en BD pero Graph falla | Banner "conectado", inbox vacío | `M365ConnectionService` verifica `/me` en cada `/connection` |
| `connection_status=connected` obsoleto | Cuentas en `/m365/cuentas` vs operativo | Estado real vía `M365GraphSessionService` |
| Errores Graph tragados | Lista vacía sin mensaje | `GraphError` con `permission_hint` en API y UI |
| Solo variables `.env` | Azure OK, sin OAuth | `account_connected` solo si hay cuenta OAuth válida |
| `M365_READ_ONLY=true` | No puede enviar | Lectura debe funcionar; escritura bloqueada con aviso |

## Variables `.env` (desarrollo local)

```env
M365_TENANT_ID=<azure-tenant-id>
M365_CLIENT_ID=<app-client-id>
M365_CLIENT_SECRET=<secret>
M365_REDIRECT_URI=http://localhost:8001/api/v1/m365/oauth/callback
M365_WEBHOOK_URL=http://localhost:8001/api/v1/m365/webhooks/graph
M365_WEBHOOK_CLIENT_STATE=<random-string>
M365_READ_ONLY=false
PUBLIC_APP_URL=http://localhost:3001
FRONTEND_URL=http://localhost:3001
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
```

Para gestión completa en dev: `M365_READ_ONLY=false`.

## Permisos Azure (delegados)

| Scope | Uso | Admin consent |
|-------|-----|---------------|
| User.Read | Perfil | No |
| offline_access | Refresh token | No |
| Mail.Read | Leer correo | No |
| Mail.ReadWrite | Marcar leído, archivar | No |
| Mail.Send | Enviar, responder | No |
| Calendars.Read / ReadWrite | Calendario | No |
| Contacts.Read / ReadWrite | Contactos | No |
| Files.Read / ReadWrite | OneDrive | ReadWrite: sí |
| Sites.Read.All / ReadWrite.All | SharePoint | Sí |
| Team.ReadBasic.All | Teams | No |
| Channel.ReadBasic.All | Canales | No |
| ChannelMessage.Read.All | Mensajes Teams | Sí |
| Chat.Read / ReadWrite | Chats | Sí |
| Group.Read.All | Grupos | Sí |

Tras agregar permisos en Azure: **Grant admin consent** y **reconectar** cada cuenta OAuth.

## Endpoints principales

- `GET /api/v1/m365/connection` — estado verificado con Graph
- `GET /api/v1/m365/oauth/start` — inicia login Microsoft
- `GET /api/v1/m365/oauth/callback` — guarda tokens
- `GET /api/v1/m365/accounts` — cuentas del usuario
- `GET /api/v1/m365/accounts/{id}/mail/inbox`
- `GET /api/v1/m365/accounts/{id}/mail/sent`
- `GET /api/v1/m365/accounts/{id}/calendar/events`
- `GET /api/v1/m365/accounts/{id}/contacts`
- `GET /api/v1/m365/accounts/{id}/onedrive/files`
- `GET /api/v1/m365/accounts/{id}/sharepoint/sites`
- `GET /api/v1/m365/accounts/{id}/teams`
- `GET /api/v1/m365/search?q=...`

## Pruebas locales

```bash
cd ~/Projects/jaios
docker compose up -d backend frontend
docker compose exec backend alembic upgrade head
docker compose exec backend pytest tests/test_m365_connection.py tests/test_m365.py -q
```

Flujo manual:
1. Login JAIOS → `/m365/cuentas` → Conectar Microsoft 365
2. Verificar `/api/v1/m365/connection` → `account_connected: true`
3. `/m365/operativo` → bandeja de entrada con correos reales
4. Probar calendario, contactos, OneDrive, búsqueda
5. Si token expira → botón Reconectar

## Deploy a producción

```bash
rsync -av --delete \
  --exclude '.env' --exclude 'docker-compose.override.yml' \
  --exclude 'node_modules' --exclude '.next' --exclude '.git' \
  ~/Projects/jaios/ /opt/jaios-app/

cd /opt/jaios-app
docker compose build backend frontend
docker compose up -d backend frontend --no-deps
docker compose exec backend alembic upgrade head
docker compose restart gateway
```

**Importante:** no copiar `docker-compose.override.yml` (puertos dev 3001/8001).

## Checklist producción

- [ ] Agregar redirect URI HTTPS en Azure: `https://jaios.justech.do/api/v1/m365/oauth/callback`
- [ ] Admin consent en tenant Justech
- [ ] `M365_READ_ONLY` según política (false = gestión completa)
- [ ] Migración `027_m365_multi_account` en prod
- [ ] Rebuild backend + frontend
- [ ] Reconectar cuentas OAuth tras nuevos scopes
- [ ] Validar webhook Graph en URL pública
- [ ] No copiar `.env` dev a prod sin revisar URLs
