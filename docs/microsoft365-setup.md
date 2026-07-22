# Microsoft 365 / Office 365 — Guía de instalación JAIOS

Integración con **Microsoft Entra ID (Azure AD)** y **Microsoft Graph** para buzones corporativos, correo, calendario, Teams, SharePoint y automatizaciones.

> **Regla:** Probar siempre en **desarrollo local** antes de producción. No desplegar sin validar OAuth.

---

## 1. Resumen de arquitectura

| Capa | Ubicación | Estado |
|------|-----------|--------|
| Integración Graph | `integrations/microsoft365/` | OAuth + Graph lectura mail |
| Intelligence Center | `/api/v1/m365/*` | Health, Outlook (Graph), cuentas |
| M365 Operativo | `/api/v1/m365/operative/*` | IMAP, demo, clasificación, n8n |
| Frontend | `/m365`, `/m365/cuentas`, `/m365/operativo` | UI completa |
| BD | `m365_user_accounts`, `m365_processed_emails`, … | Migraciones 007, 025, 026 |

**Dos formas de conectar buzón hoy:**

1. **OAuth Graph (recomendado)** — `/m365/oauth/*` + tokens en PostgreSQL
2. **IMAP** — `/m365/accounts/connect-imap` (app password)

---

## 2. Azure Portal — paso a paso

### 2.1 App Registration

1. [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **New registration**
2. **Name:** `JAIOS Microsoft 365`
3. **Supported account types:** *Accounts in this organizational directory only* (single tenant Justech)
4. **Redirect URI:**
   - Type: **Web**
   - Desarrollo: `http://localhost:8001/api/v1/m365/oauth/callback`
   - Producción (añadir después): `https://jaios.justech.do/api/v1/m365/oauth/callback`

### 2.2 Copiar credenciales

| Valor | Dónde |
|-------|-------|
| **Tenant ID** | Overview → Directory (tenant) ID |
| **Client ID** | Overview → Application (client) ID |
| **Client Secret** | Certificates & secrets → New client secret |

### 2.3 Permisos Microsoft Graph (Delegated)

**API permissions** → Add → Microsoft Graph → **Delegated permissions:**

| Permiso | Uso |
|---------|-----|
| `openid` | OAuth |
| `profile` | Perfil usuario |
| `offline_access` | Refresh token |
| `User.Read` | Identidad |
| `Mail.Read` | Leer correos |
| `Mail.Send` | Enviar correos (si `M365_READ_ONLY=false`) |
| `Mail.ReadWrite` | Gestión correo (si escritura habilitada) |
| `Calendars.Read` | Calendario |
| `Calendars.ReadWrite` | Crear eventos (futuro) |
| `Contacts.Read` | Contactos |
| `Files.Read.All` | OneDrive |
| `Sites.Read.All` | SharePoint |
| `Team.ReadBasic.All` | Teams |
| `ChannelMessage.Read.All` | Mensajes Teams |

**Admin consent:** Grant admin consent for [tenant] (requiere Global Admin).

### 2.4 Application permissions (opcional — buzones compartidos)

Para indexación sin usuario presente:

| Permiso | Uso |
|---------|-----|
| `Mail.Read` | Application |
| `Calendars.Read` | Application |
| `Files.Read.All` | Application |
| `Sites.Read.All` | Application |

Requiere certificado o secret + permiso de admin.

### 2.5 Webhook URL (Graph subscriptions)

| Ambiente | URL |
|----------|-----|
| Desarrollo | `http://localhost:8001/api/v1/m365/webhooks/graph` |
| Producción | `https://jaios.justech.do/api/v1/m365/webhooks/graph` |

> Webhooks requieren HTTPS público en producción. En local usar [ngrok](https://ngrok.com) o validar solo en prod.

**Client State:** valor aleatorio en `M365_WEBHOOK_CLIENT_STATE` (validación de notificaciones).

---

## 3. Variables de entorno

### Desarrollo local (`~/Projects/jaios/.env`)

```env
# URLs locales (docker-compose.override.yml → puerto 8001 gateway)
PUBLIC_APP_URL=http://localhost:3001
FRONTEND_URL=http://localhost:3001
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
BACKEND_PUBLIC_URL=http://localhost:8001/api/v1

# Microsoft 365 — completar tras Azure Portal
M365_READ_ONLY=true
M365_TENANT_ID=
M365_CLIENT_ID=
M365_CLIENT_SECRET=
M365_REDIRECT_URI=http://localhost:8001/api/v1/m365/oauth/callback
M365_WEBHOOK_URL=http://localhost:8001/api/v1/m365/webhooks/graph
M365_WEBHOOK_CLIENT_STATE=genera-un-secreto-aleatorio

# Operativo
M365_OPERATIVE_ENABLED=true
M365_OPERATIVE_DEMO_MODE=true
M365_IMAP_HOST=outlook.office365.com
M365_IMAP_PORT=993
M365_MONITORED_MAILBOXES=ventas@justech.do,cotizaciones@justech.do
M365_N8N_ENABLED=true
M365_N8N_TEAMS_WORKFLOW=m365-teams-notify
```

### Producción (VPS — NO aplicar hasta validar dev)

```env
PUBLIC_APP_URL=https://jaios.justech.do
FRONTEND_URL=https://jaios.justech.do
CORS_ORIGINS=https://jaios.justech.do
NEXT_PUBLIC_API_URL=https://jaios.justech.do/api/v1
BACKEND_PUBLIC_URL=https://jaios.justech.do/api/v1

M365_REDIRECT_URI=https://jaios.justech.do/api/v1/m365/oauth/callback
M365_WEBHOOK_URL=https://jaios.justech.do/api/v1/m365/webhooks/graph
M365_WEBHOOK_CLIENT_STATE=mismo-secreto-que-azure-subscription
```

---

## 4. Arranque desarrollo local

```bash
cd ~/Projects/jaios
cp docker-compose.override.example.yml docker-compose.override.yml
cp .env.example .env
# Editar .env con credenciales Azure

docker compose up -d --build
docker compose exec -T backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

URLs:

- Frontend: http://localhost:3001/m365
- OAuth callback: http://localhost:8001/api/v1/m365/oauth/callback
- Cuentas IMAP: http://localhost:3001/m365/cuentas
- Operativo: http://localhost:3001/m365/operativo

---

## 5. Procedimiento de pruebas (Fase 7)

| # | Prueba | Cómo |
|---|--------|------|
| 1 | Config Azure | `GET /m365/health` → `oauth_ready: true` |
| 2 | OAuth login | `/m365` → Conectar Microsoft 365 → consentimiento Azure |
| 3 | Callback | Redirección a `/m365/cuentas?connected=1` |
| 4 | Tokens en BD | `m365_user_accounts.connection_mode = oauth` |
| 5 | Leer correos | Tab Outlook en `/m365` o `GET /m365/outlook/messages` |
| 6 | Refresh token | `POST /m365/oauth/refresh` |
| 7 | IMAP alternativo | `/m365/cuentas` → conectar con app password |
| 8 | Operativo sync | `POST /m365/operative/sync` |
| 9 | Webhook Graph | `POST /m365/webhooks/graph?validationToken=test` → devuelve `test` |
| 10 | UI | Login demo `admin@justech.do` / tenant `justech` |

---

## 6. Matriz de funcionalidades

| Funcionalidad | Estado | Notas |
|---------------|--------|-------|
| OAuth por usuario | ✅ Implementado | `/m365/oauth/*` |
| Refresh tokens | ✅ Implementado | Auto-refresh en `get_valid_access_token` |
| Leer correos Graph | ✅ Implementado | `/me/messages` |
| Enviar correos | ⚠️ Parcial | Requiere `M365_READ_ONLY=false` + permiso Mail.Send |
| Webhooks Graph | ⚠️ Validación | Endpoint listo; suscripciones pendientes |
| Calendario Graph | 🔲 Stub | Servicio vacío |
| Contactos | 🔲 Stub | |
| Teams Graph | 🔲 Stub | n8n para notificaciones |
| SharePoint Graph | 🔲 Stub | Solo paths metadata en Operativo |
| Búsqueda Graph | 🔲 Stub | |
| Clasificación automática | ✅ Operativo | Reglas + extracción |
| Relación DGCP/Odoo | ✅ Operativo | `m365_email_relation_service` |
| Asociación tareas | ✅ Operativo | Acciones sugeridas |
| IMAP buzones | ✅ Implementado | Sin OAuth Azure |
| Demo inbox | ✅ Default | `M365_OPERATIVE_DEMO_MODE=true` |
| Indexación Qdrant | 🔲 Planificado | |
| Assistant M365 | 🔲 Stub | |

Leyenda: ✅ listo · ⚠️ parcial · 🔲 pendiente

---

## 7. Endpoints API

### OAuth
- `GET /m365/oauth/authorize-url` — URL Microsoft (JWT requerido)
- `GET /m365/oauth/start` — Redirect directo
- `GET /m365/oauth/callback` — Callback Azure
- `POST /m365/oauth/refresh` — Renovar tokens

### Cuentas
- `GET /m365/accounts/me`
- `POST /m365/accounts/connect-imap`
- `POST /m365/accounts/disconnect`

### Intelligence
- `GET /m365/outlook/messages`
- `GET /m365/health`, `/m365/status`

### Operativo
- `POST /m365/operative/sync`
- `GET /m365/operative/emails`
- `POST /m365/operative/webhooks/n8n/inbound-email`

### Webhooks
- `POST /m365/webhooks/graph`

---

## 8. Plan paso a producción (sin deploy automático)

1. ✅ Validar OAuth + lectura mail en local
2. Crear segundo Redirect URI en Azure → `https://jaios.justech.do/...`
3. Copiar `.env` producción con URLs HTTPS
4. **No** usar `docker-compose.override.yml` en VPS
5. Registrar webhook Graph con URL pública HTTPS
6. Desactivar demo: `M365_OPERATIVE_DEMO_MODE=false`
7. Probar con buzón real `@justech.do`
8. Deploy manual cuando Fausto apruebe

---

## 9. ¿JAIOS listo para correos de empleados?

| Método | Listo |
|--------|-------|
| **IMAP + app password** | ✅ Sí — usar `/m365/cuentas` hoy |
| **OAuth Graph** | ✅ Sí — tras configurar Azure + `.env` |
| **Graph completo** (Teams, SP, calendario) | 🔲 Parcial — solo mail implementado |
| **Producción** | 🔲 Pendiente validación dev + deploy |

---

## 10. Troubleshooting

| Problema | Solución |
|----------|----------|
| `oauth_ready: false` | Completar M365_TENANT_ID, CLIENT_ID, CLIENT_SECRET |
| Redirect URI mismatch | URI en Azure = `M365_REDIRECT_URI` exacto |
| Admin consent required | Azure → API permissions → Grant admin consent |
| IMAP auth failed | Usar app password si MFA activo |
| Demo siempre activo | `M365_OPERATIVE_DEMO_MODE=false` + OAuth o IMAP |

---

*Documento generado para JAIOS — Justech AI Operating System*
