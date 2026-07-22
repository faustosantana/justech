# Microsoft 365 Operativo Premium — JAIOS

## 1. Diagnóstico del estado anterior

| Problema | Causa | Corrección |
|----------|-------|------------|
| Teams error `$top` | `graph_list` siempre enviaba `$top` a `/me/joinedTeams` | `use_top=False` en Teams |
| Outlook limitado | UI sin compose/forward/reply-all/adjuntos | Workspace premium + API mail ampliada |
| Calendario lista plana | Sin `calendarView` ni grid | Vista mes + agenda con Graph `calendarView` |
| OneDrive sin navegación | Solo root children | `folder_id` + breadcrumbs |
| SharePoint superficial | Solo sitios | Sitios → bibliotecas → documentos |
| Búsqueda débil | Fan-out sin `match_reason` | Grupos + razón de coincidencia |
| UI técnica visible | Tenant/Client/read_only en banner | Solo en `/m365?tab=configuracion` (admin) |
| Solo lectura activa | `M365_READ_ONLY=true` en dev | `false` en `.env` local |

## 2. Archivos principales modificados

**Backend**
- `integrations/microsoft365/graph_helpers.py` — `use_top`, `parse_graph_datetime`
- `integrations/microsoft365/teams.py`, `onedrive.py`, `sharepoint.py`, `outlook.py`, `calendar.py`, `schemas.py`
- `backend/app/services/m365_mail_service.py`, `m365_service.py`
- `backend/app/schemas/m365_mail.py`
- `backend/app/api/v1/m365.py`
- `backend/tests/test_m365_teams_graph.py`

**Frontend**
- `frontend/src/components/m365/m365-workspace.tsx` *(nuevo — UI premium)*
- `frontend/src/lib/m365-workspace.ts`, `m365-mail.ts`, `api.ts`
- `frontend/src/app/(platform)/m365/operativo/page.tsx`
- `frontend/src/app/(platform)/m365/page.tsx`, `cuentas/page.tsx`

## 3. Endpoints nuevos/ampliados

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/m365/onedrive/files?folder_id=` | Navegación carpetas |
| GET | `/m365/sharepoint/sites/{id}/drives` | Bibliotecas |
| GET | `/m365/sharepoint/drives/{id}/items?folder_id=` | Documentos SP |
| GET | `/m365/teams/{id}/channels` | Canales |
| GET | `/m365/teams/{id}/channels/{id}/messages` | Mensajes |
| GET | `/m365/calendar/events?start=&end=` | Vista calendario |
| GET | `/m365/mail/messages/{id}/attachments` | Adjuntos |
| POST | `/m365/mail/send` | Enviar con adjuntos/CC/borrador |
| PATCH | `/m365/mail/messages/{id}` | `move_to_folder`, `is_read` |

## 4. Permisos Azure (gestión completa)

| Scope | Admin consent |
|-------|---------------|
| User.Read, offline_access | No |
| Mail.ReadWrite, Mail.Send | No |
| Calendars.ReadWrite | No |
| Contacts.ReadWrite | No |
| Files.ReadWrite | Sí |
| Sites.ReadWrite.All | Sí |
| Team.ReadBasic.All, Channel.ReadBasic.All | No |
| ChannelMessage.Read.All | Sí |
| Chat.ReadWrite | Sí |
| Group.Read.All | Sí |

Tras agregar permisos: **Grant admin consent** + **reconectar** cuenta OAuth.

## 5. Variables `.env` (desarrollo)

```env
M365_READ_ONLY=false
M365_TENANT_ID=...
M365_CLIENT_ID=...
M365_CLIENT_SECRET=...
M365_REDIRECT_URI=http://localhost:8001/api/v1/m365/oauth/callback
FRONTEND_URL=http://localhost:3001
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
```

## 6. Pruebas locales

```bash
cd ~/Projects/jaios
docker compose exec backend pytest tests/test_m365_teams_graph.py tests/test_m365_connection.py -q
docker compose exec frontend npm run build
```

Flujo manual: `http://localhost:3001/m365/operativo`

## 7. Checklist producción (NO ejecutar sin aprobación)

- [ ] `M365_READ_ONLY=false` si se requiere gestión completa
- [ ] Admin consent para scopes marcados
- [ ] Reconectar cuentas OAuth tras nuevos permisos
- [ ] `rsync` sin `docker-compose.override.yml`
- [ ] `alembic upgrade head` si hay migraciones pendientes
- [ ] Rebuild backend + frontend
- [ ] Validar Teams, OneDrive, Outlook en `https://jaios.justech.do/m365/operativo`

## Pendiente siguiente iteración

- Crear/editar eventos desde UI (API lista)
- Adjuntar OneDrive a licitaciones DGCP
- Vista previa PDF/imagen embebida
- Graph Search API (`POST /search/query`) para búsqueda enterprise
- Subida archivos OneDrive desde UI
