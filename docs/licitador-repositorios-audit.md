# Auditoría — Licitador / Repositorios / OneDrive / Inteligencia de Precios

**Entorno:** desarrollo local (`/root/Projects/jaios`)  
**Fecha:** 2026-06-10  
**Producción:** NO desplegado (por instrucción explícita)

## 1. Diagnóstico

| Área | Antes | Después |
|------|-------|---------|
| Sync OneDrive | Full-drive, borraba todo | Sync por `binding` + Graph delta |
| Repositorios UI | Rutas manuales básicas | Dashboard con auto-sync, jobs, errores |
| Datos empresas | Solo FS / JSON estático | `licitador_company_profiles` desde OneDrive JSON |
| Documentos legales | Knowledge FS | Clasificación desde M365 binding |
| Precios ENTRADAS | Solo `knowledge_source_path` | Descarga OneDrive → `PriceListIndexer` lógica |
| Scheduler | No existía para repos | Cada 15 min (`repository_scheduler`) |
| Validación expediente | Solo paquete DGCP | + empresa, legales, datos faltantes |
| Correo faltantes | No | Borrador API por empresa |

## 2. Archivos creados

- `backend/alembic/versions/035_repository_sync_engine.py`
- `backend/app/models/repository_sync.py`
- `backend/app/models/licitador_company_profile.py`
- `backend/app/services/repository_sync_service.py`
- `backend/app/services/company_profile_sync_service.py`
- `backend/app/services/supplier_price_file_service.py`
- `backend/app/services/company_missing_info_email_service.py`
- `backend/app/services/dgcp_expediente_validation_service.py`
- `backend/app/services/price_search_service.py`
- `backend/app/services/legal_document_sync_service.py`
- `backend/app/services/repository_scheduler.py`
- `backend/tests/test_repository_sync.py`

## 3. Archivos modificados

- `integrations/microsoft365/onedrive.py` — `resolve_folder_by_path`, `collect_delta`
- `backend/app/services/m365_repository_service.py` — `sync_binding`
- `backend/app/services/integration_repository_service.py` — delega a `RepositorySyncService`
- `backend/app/models/integration_settings.py`, `m365_repository.py`, `price_list.py`
- `backend/app/api/v1/settings.py` — endpoints ampliados
- `backend/app/schemas/settings.py`
- `backend/app/main.py` — scheduler repositorios
- `frontend/.../repositorios/page.tsx`, `lib/api.ts`, `lib/settings.ts`

## 4. Migración 035

Extiende `integration_repository_bindings`, `m365_repository_files`, crea `repository_sync_jobs`, `licitador_company_profiles`, columnas en `price_list_files`.

```bash
cd backend && alembic upgrade head
```

## 5. Endpoints nuevos

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/settings/repositories/sync-all` | Sync todos los bindings |
| GET | `/settings/repositories/sync-jobs` | Historial |
| GET | `/settings/company-profiles` | Perfiles JSON sincronizados |
| POST | `/settings/company-profiles/{key}/missing-email` | Borrador correo |
| GET | `/settings/price-inbox/pending` | Listas pendientes |

## 6. Permisos Graph requeridos

Delegados (ya en `DEFAULT_READ_SCOPES`): `User.Read`, `offline_access`, `Files.ReadWrite`, `Sites.ReadWrite.All`, `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, Teams scopes.

Admin consent: `Files.ReadWrite.All`, `Sites.ReadWrite.All`.

## 7. Variables .env

Sin cambios obligatorios. Requiere M365 conectado (`M365_TENANT_ID`, `M365_CLIENT_ID`, `M365_CLIENT_SECRET`) y usuario OAuth con acceso a carpeta `Justech-AI`.

## 8. Pruebas locales recomendadas

1. `alembic upgrade head`
2. Configurar rutas en `/configuracion/repositorios`
3. Conectar M365 → Sincronizar `00_DATOS_EMPRESAS`
4. Verificar `GET /settings/company-profiles`
5. Sincronizar `03_PROVEEDORES_ENTRADAS` → indexar precios
6. Buscar producto vía asistente / `/api/v1/prices`
7. Generar borrador correo faltantes

## 8b. Pantallas premium (UI)

| Ruta | Descripción |
|------|-------------|
| `/licitador/empresas` | Datos empresas desde JSON OneDrive |
| `/licitador/documentos-legales` | Dashboard legal por empresa + correo solicitud |
| `/licitador/plantillas` | Plantillas DGCP + vista previa autollenado |
| `/licitador/precios` | Centro inteligencia de precios (pendientes/procesados) |

API: `GET /api/v1/licitador/documentos-legales`, `/plantillas`, `/precios`

## 9. Pendiente antes de producción

- Probar con OneDrive real `Justech-AI` (requiere cuenta M365 conectada en dev)
- Webhooks Graph (opcional; delta + scheduler es el camino estable actual)
- Mover archivos procesados físicamente a PROCESADOS en OneDrive (hoy: tag `price_processed`)
- UI dedicadas: documentos legales, plantillas DGCP, centro precios (parcialmente existentes en `/prices`)
- Integrar `DGCPExpedienteValidationService` en flujo UI licitador
- Plantillas: indexación de campos rellenables (existe `dgcp_form_autofill_service`)

## 10. Riesgos

- Delta Graph puede expirar → re-sync full en carpeta
- Límite 500 archivos por binding en crawl
- Descarga de listas de precios depende de `@microsoft.graph.downloadUrl` (TTL corto)
- Sin M365 conectado, sync devuelve error controlado
