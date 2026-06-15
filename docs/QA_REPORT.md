# QA Report — JAIOS Capa Inteligente (Fases 1–5)

**Proyecto:** JAIOS — Justech AI Operating System  
**Fecha validación:** 2026-06-14  
**Entorno:** Docker (`jaios-app`), tenant `justech`, Odoo `https://justgroup.app`  
**Script QA:** `backend/scripts/validate_functional.py`

---

## Resumen ejecutivo

| Métrica | Resultado |
|---------|-----------|
| Checks automatizados | **13/13 PASS** |
| Índice comercial | **2.232 ítems** indexados |
| Sync incremental Odoo | **1.000 registros/ciclo**, sin errores |
| Plantillas documentales | **8** activas |
| Centro Hermes | **10 tarjetas** proactivas |
| Odoo | **Conectado** (solo lectura en indexación) |
| Frontend (`:3000`) | Rutas clave **HTTP 200** |
| Gateway (`:8000`) | **Operativo** (requiere reinicio si keepalive obsoleto) |
| Migración Alembic | **046** (`document_templates`) |

**Conclusión:** Las fases 1–5 están entregadas y validadas en entorno real con datos Odoo.

---

## Microsoft 365 / OneDrive Business (2026-06-10)

Auditoría integral: [`docs/JAIOS_FULL_AUDIT_REPORT.md`](JAIOS_FULL_AUDIT_REPORT.md)  
Checklists: [`QA_CHECKLIST.md`](QA_CHECKLIST.md) · [`PRODUCTION_READINESS_CHECKLIST.md`](PRODUCTION_READINESS_CHECKLIST.md) · [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)

| Check | Estado | Detalle |
|-------|--------|---------|
| Referencias `onedrive.live.com` en código | PASS | Eliminadas — solo documentación |
| OAuth Entra ID | PASS | `login.microsoftonline.com/{tenant}` |
| Graph OneDrive/SharePoint | PASS | `/me/drive`, `/sites`, `/drives` |
| Picker in-app (`M365DocumentSearchPicker`) | PASS | Graph + repositorio indexado |
| `DocumentQuestionService` + M365 | PASS | Busca repositorio + Graph en vivo |
| `search_index` fuente `m365` | PASS | Archivos `m365_repository_files` |

**QA manual pendiente:** conectar cuenta M365, ejecutar sync repositorio, probar búsquedas «Busca contrato Banco Ademi», «Busca propuesta Midas».

---

## Validación funcional (2026-06-14)

Ejecutado con `docker exec jaios-app-backend-1 python scripts/validate_functional.py`:

| Check | Estado | Detalle |
|-------|--------|---------|
| `GET /api/v1/health` | PASS | `jaios-api` v0.1.0 |
| `POST /api/v1/auth/login` | PASS | admin@justech.do / tenant justech |
| `GET /commercial-search/sync/status` | PASS | 2.232 ítems en índice |
| `GET /commercial-search?q=laptop+dell` | PASS | 50 resultados, índice disponible |
| `POST /commercial-search/sync` | PASS | status=completed, indexed=1000 |
| Búsqueda post-sync | PASS | 50 resultados |
| `GET /dgcp/opportunities` | PASS | Listado OK |
| `POST /dgcp/opportunities` (manual) | PASS | QA-MANUAL-TEST-001 (409 si ya existe) |
| `GET /document-templates` | PASS | 8 plantillas |
| `GET /document-templates/sncc-f042/missing-fields` | PASS | Autollenado Hermes OK |
| `GET /hermes/intelligence-center` | PASS | 10 tarjetas |
| `GET /odoo/health` | PASS | connected=True |
| `GET /search` (legacy) | PASS | Sin regresión |

### Búsquedas comerciales verificadas (gateway)

Consulta: `laptop dell i7` → **50 resultados** con datos reales, por ejemplo:

- PORTÁTIL DELL PRO 14 PLUS (PB14250) I7, 16GB, 512GB SSD
- Laptop Dell 15.6" AMD Ryzen 3 7320u, 512GB, 8GB RAM

### Rutas frontend verificadas

| Ruta | HTTP |
|------|------|
| `/` | 200 |
| `/inteligencia/busqueda-comercial` | 200 |
| `/inteligencia/centro-hermes` | 200 |
| `/apps/licitaciones/procesos` | 200 |

---

## Correcciones aplicadas durante QA

| Problema | Causa | Solución |
|----------|-------|----------|
| Sync Odoo falla con watermark | Odoo espera datetime naive; comparación naive vs aware | `_odoo_write_date_filter()`, `_normalize_watermark()`, `_parse_odoo_datetime()` en `commercial_index_sync_service.py` |
| `document-templates` ValidationError | Pydantic sin `from_attributes` | `model_config = {"from_attributes": True}` en `DocumentTemplateResponse` |
| Centro Hermes crash | Atributo inexistente `raw_body` | Uso de `raw_body_preview` en `hermes_intelligence_center_service.py` |
| `commercial-context` KeyError | `recommendations` como dict vs list | Normalización en `integrated_commercial_flow_service.py` |
| Frontend HTTP 500 | `.next` corrupto (build con dev en marcha) | Reinicio contenedor frontend (`rm -rf .next && npm run dev`) |
| Gateway `/api/*` → 404 | Conexiones keepalive nginx obsoletas | `docker compose restart gateway` |
| Duplicado `LicitacionesAnalisisSection` | Función declarada dos veces | Eliminado bloque duplicado en `licitaciones-sections.tsx` |

---

## Fase 1 — Búsqueda Comercial + Índice Odoo

**Estado:** Completada y validada  
**Migración:** `045_commercial_search_index`  
**Tests unitarios:** 4+ passed (`test_commercial_index_search.py`)

### Entregables

- Tablas: `commercial_search_items`, `commercial_search_documents`, `commercial_price_history`, `customer_purchase_history`, `product_sales_history`, `commercial_search_sync_state`
- Sync incremental read-only desde Odoo: `sale.order.line`, `account.move.line`, `purchase.order.line`, `crm.lead`
- API: `/api/v1/commercial-search` (+ sync, history, price/customer/product history)
- Hermes tool: `commercial_history`
- UI: `/inteligencia/busqueda-comercial`, sección en módulo Agentes IA

### Archivos clave

- `backend/app/models/commercial_search.py`
- `backend/app/services/commercial_index_sync_service.py`
- `backend/app/services/commercial_index_search_service.py`
- `backend/app/api/v1/commercial_search.py`
- `frontend/src/components/modules/agentes-ia/commercial-search-section.tsx`

---

## Fase 2 — Licitaciones Profesional

**Estado:** Completada y validada

### Entregables

- Estados pipeline ampliados (12 + legacy) en backend y frontend
- `POST /api/v1/dgcp/opportunities` — creación manual
- Kanban profesional con `PIPELINE_STATUSES` y `STATUS_LABELS`
- UI: `CreateLicitationDialog`, expedientes ampliados
- Secciones: `licitaciones:analisis`, `licitaciones:competidores`
- Tab **Comercial Odoo** en detalle DGCP

### QA

- Listado y creación manual: OK
- Acciones legacy preservadas (expediente/checklist no roto)

---

## Fase 3 — Autollenado Documentos

**Estado:** Completada y validada  
**Migración:** `046_document_templates`

### Entregables

- Tabla `document_templates`
- `DocumentTemplateService` — repo `/backend/templates/{dgcp,legal,commercial,internal}`
- API: `GET /document-templates`, `GET /document-templates/{slug}/missing-fields`
- Hermes tool: `form_autofill`
- 8 plantillas default (SNCC F.042, cartas, ofertas, checklist)

### QA

- 8 plantillas listadas correctamente
- Missing-fields SNCC F.042: mensaje Hermes de autollenado OK

---

## Fase 4 — Centro Inteligencia Hermes

**Estado:** Completada y validada

### Entregables

- `HermesIntelligenceCenterService` — detectores:
  - Licitaciones recomendadas / plazos
  - Cotizaciones sin seguimiento (índice Odoo)
  - Clientes esperando respuesta (observaciones Hermes)
  - Documentos faltantes
- API: `GET /hermes/intelligence-center`
- UI: `/inteligencia/centro-hermes`

### Reglas de seguridad

- No ejecuta envíos ni creaciones automáticas
- Acciones sugeridas con `requires_approval: true` donde aplica

---

## Fase 5 — Integración Profunda

**Estado:** Completada y validada

### Entregables

- `IntegratedCommercialFlowService`
- API: `GET /dgcp/opportunities/{id}/commercial-context`
- Combina: búsqueda comercial + price history + inteligencia DGCP + autofill preview
- Panel integrado en tab Comercial Odoo del detalle licitación

### Flujos cubiertos

| Escenario | Implementación |
|-----------|----------------|
| Licitación → historial Odoo | Tab comercial + commercial-context |
| Cotización sin seguimiento | Centro Hermes detector |
| Cliente RFQ | Observaciones + inteligencia comercial |
| Autollenado | missing-fields + Hermes form_autofill |

---

## Restricciones respetadas

| Restricción | Cumplimiento |
|-------------|--------------|
| No escribir en Odoo sin autorización | Sync e indexación son **read-only** |
| No romper integraciones existentes | Endpoints legacy (`/search`) OK |
| ERP nativo pausado | Odoo sigue como fuente de datos |
| QA obligatorio por fase | Script + pruebas manuales ejecutadas |

---

## Operaciones y troubleshooting

### Ejecutar validación QA

```bash
docker exec jaios-app-backend-1 python scripts/validate_functional.py
```

### Regenerar PDF del reporte

```bash
docker compose run --rm --no-deps \
  -v "$(pwd)/docs:/docs" \
  -v "$(pwd)/backend/scripts:/scripts" \
  backend sh -c "pip install fpdf2 -q && python /scripts/generate_qa_pdf.py /docs/QA_REPORT.md /docs/QA_REPORT.pdf"
```

Salida: `docs/QA_REPORT.pdf`

### Sync manual del índice comercial

```bash
curl -X POST http://localhost:8000/api/v1/commercial-search/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"full_reindex": false}'
```

### Frontend dev — no corromper `.next`

- No ejecutar `npm run build` con `next dev` en marcha
- Si hay HTTP 500: `docker compose restart frontend`

### Gateway devuelve 404 en `/api/*`

- Reiniciar: `docker compose restart gateway`
- Causa: conexiones keepalive nginx obsoletas hacia backend

---

## QA Hermes — Calidad búsqueda comercial (2026-06-10)

Script: `backend/scripts/validate_hermes_commercial_qa.py`  
Documentación técnica: `docs/HERMES_SEARCH_QUALITY.md`

| Pregunta | Estado | Herramienta |
|----------|--------|-------------|
| cuántas laptops hay de menos de 800 dólares | **PASS** | `commercial_index` |
| laptops dell i7 menos de 1000 dolares | **PASS** | `commercial_index` |
| dime de las listas de precios mejor | **PASS** | `price_list_status` |
| qué proveedores tienen laptops | **PASS** | `price_list_status` |
| busca switches cisco vendidos anteriormente | **PASS** | `commercial_history` |
| cuál fue el último precio vendido de laptop hp | **PASS** | `commercial_history` |
| qué productos hay indexados hoy | **PASS** | `price_list_status` |
| por qué no hay listas hoy | **PASS** | `price_list_status` |

**Resultado:** **8/8 PASS** (~1,2 s por consulta, ruta determinística sin LLM)

### Correcciones aplicadas

| Problema | Solución |
|----------|----------|
| Laptops mezcladas con RAM, CD-ROM, accesorios | `commercial_product_filter.py` + filtro en `count_under_price` |
| DOP comparado como USD | `commercial_currency.py` con tasa configurable |
| Respuestas largas e irrelevantes | `hermes_commercial_formatter.py` (Resumen / Top 5 / Fuentes) |
| “Listas de precios” pide aclaración | Ruta `price_list_status` + `format_price_list_overview` |
| 424 productos indexados no usados | `PriceListSummaryService` integrado en `commercial_index` |
| Error genérico 500 | Mensajes útiles en `assistant.py` + fallback de herramientas |

### QA Hermes copilot general (regresión)

Script: `backend/scripts/validate_hermes_qa.py` — **8/8 PASS** (sin regresión)

---

## QA Arquitectura de módulos (2026-06-10)

Documentación: `docs/QA_MODULE_ARCHITECTURE.md` · `docs/MODULE_ARCHITECTURE_AUDIT.md`  
Script: `backend/scripts/validate_module_registry.py`

| Fase | Entregable |
|------|------------|
| 0 | Auditoría dominios y contentKeys mal cableados |
| 1 | Módulo Empresas del Grupo + suppliers:directory |
| 2 | Expediente `/apps/empresas-grupo/perfil/[id]` + VigencyBadge |
| 3 | Proveedor `/apps/proveedores/perfil/[id]` + clientes Odoo |
| 4 | Precios KPIs reales + alertas |
| 5 | Documentos por entidad + redirects legacy |
| 6 | QA checklist + script registry |

---

## Pendientes evolutivos (post-entrega)

- Plantillas `.docx` físicas en `/backend/templates/*`
- Batch sync >500 registros por job en background
- E2E Playwright flujos completos UI
- Lint frontend preexistente (`no-assign-module-variable` en módulos apps)

---

## M365 documental (2026-06-14)

| # | Prueba | Resultado |
|---|--------|-----------|
| 1 | Diagnóstico sync: endpoint `POST /documents/companies/{id}/onedrive/sync` | Documentado |
| 2 | Causa raíz: `UniqueViolation` en `uq_knowledge_assets_tenant_path` (archivos sin nombre) | Corregido |
| 3 | Fix indentación `m365_repository_service.py` (backend no arrancaba) | Corregido |
| 4 | Picker M365: selección, vincular, importar, metadatos | Implementado |
| 5 | Endpoints `/m365/documents/search|recent|folders|sync|link|import` | Implementado |
| 6 | Sync OneDrive UI sin error genérico | Requiere prueba manual con M365 |

Ver `docs/M365_INTEGRATION.md` y `docs/M365_ONEDRIVE_AUDIT.md`.

### Migración global M365 — estado QA funcional (2026-06-15, Prioridad 1 — E2E UI)

| Módulo | Estado funcional | Informe |
|--------|------------------|---------|
| Empresas del Grupo | **PARCIAL** | Import MIPYME UI (clic real) 14%→17%; fix `onImported`; TSS `onedrive_url` OK |
| Licitaciones / DGCP | **PARCIAL** | Vincular SNCC F.042 UI OK; 88% prep; Ver documento; falta Import UI |
| Comunicaciones | **BLOQUEADO** | WA disconnected — checklist QA preparado en §3 |
| Documentos hub | **PARCIAL** | Contador legal **13 archivos**; búsqueda `Ademi contrato` → 1; falta picker UI E2E |

**Correcciones Prioridad 1 (2026-06-15, sesión E2E):**

| Área | Cambio |
|------|--------|
| `m365_documents_service` | Resolver `web_url` Graph si null; búsqueda repo multi-término AND |
| `m365_repository_service` | Recalcular `binding.indexed_files` en `upsert_m365_item` |
| `company_profile_field_service` | Lookup asset por `relative_path` + `document_type` |
| `company-profile-form.tsx` | `onImported` refresca UI tras Importar |
| DGCP checklist | (previo) `compute_risk` + sanitize ítems cumplidos |

**Evidencia Empresas (sesión E2E UI):**

| Métrica | Antes | Después |
|---------|-------|---------|
| Completitud perfil | 4/28 (14 %) | 5/28 (17 %) |
| `mipyme` | Falta | Documento cargado (import UI + API) |
| `tss` `onedrive_url` | null | URL SharePoint + botón Abrir en OneDrive |

**Evidencia DGCP:** SNCC F.042 vinculado desde picker (F042 → `SNCC_F042_Informacion_Oferente.docx`); 0 faltantes, 1 por completar (formulario).

**Evidencia Hub:** `01 — Documentos legales` pasa de 3 → **13** archivos indexados; search `Ademi contrato` devuelve contrato Banco Ademi.

**Ningún módulo marcado CERRADO** hasta completar flujos E2E con clic UI de punta a punta + refresh verificado.

Ver detalle: [`docs/M365_FUNCTIONAL_QA_AUDIT.md`](M365_FUNCTIONAL_QA_AUDIT.md)

---

## Saneamiento documental (2026-06-15)

**Objetivo:** Eliminar porcentajes inflados y documentos mal asociados. Preferir estado real aunque baje el %.

| Componente | Archivo |
|------------|---------|
| Validador estricto | `backend/app/services/document_requirement_validator.py` |
| Script saneamiento | `backend/scripts/document_sanitize.py` |
| Reporte JSON | `docs/sanitize_report.json` |
| Tests | `backend/tests/test_document_requirement_validator.py` — **7/7 PASS** |

### Resultados

| Módulo | Antes | Después |
|--------|-------|---------|
| DGCP preparación | **88%** (7/8; 4 matches incorrectos) | **62.5%** (5/8 reales; registro mercantil vinculado) |
| Empresas completitud | 21% (6/28) | **21%** (sin inflar) |
| Hub assets activos | 19 (ACTA×3, REGISTRO×3) | **14** (deduplicados, archivos OneDrive intactos) |
| SNCC F.042 | Riesgo «completo» | **Pendiente de completar** |

### QA post-saneamiento (API)

| Prueba | Resultado |
|--------|-----------|
| DGCP checklist tras limpiar | **PASS** — 5 cumplidos, 2 faltantes, 1 pendiente completar; Ver documento sin 404 |
| Empresas completion | **PASS** — 21%, 6/28 |
| Hub binding legal 01 | **PASS** — 13/13 sincronizado |
| Persistencia tras restart backend | **PASS** |
| Ver documento (sistema) | **PASS** — `/documents/access` + redirect M365; local si importado; canónico si dedup |

Auditorías actualizadas: `DOCUMENT_REQUIREMENT_AUDIT.md`, `DOCUMENT_DUPLICATION_AUDIT.md`, `M365_FUNCTIONAL_QA_AUDIT.md`, `DOCUMENT_ACCESS_SERVICE.md`.

---

## Integración global DocumentViewButton (2026-06-15)

**Objetivo:** Unificar «Ver documento» en todos los módulos vía `DocumentAccessService`.  
**Documentación técnica:** [`docs/DOCUMENT_ACCESS_SERVICE.md`](DOCUMENT_ACCESS_SERVICE.md)

### Regla oficial

Todo «Ver documento» debe pasar por **`DocumentViewButton`** / **`DocumentViewLink`** (frontend) y **`DocumentAccessService`** (backend). No usar links directos dispersos a SharePoint/OneDrive.

### Módulos actualizados

| Módulo | Componentes integrados | Estado |
|--------|------------------------|--------|
| Empresas del Grupo | `company-profile-form.tsx`, `company-expediente-view.tsx` | **Integrado + QA UI** |
| Representantes | `representative-card.tsx` | **Integrado + QA UI** |
| Licitaciones / DGCP | `opportunity-bid-section.tsx`, `document-preview-modal.tsx` | **Integrado + QA UI** |
| Documentos Hub — legales | `documentos-sections.tsx`, `licitador/documentos-legales/page.tsx` | **Integrado + QA UI** |
| Documentos Hub — plantillas | `documentos-sections.tsx`, `documentos/plantillas/page.tsx` | **Integrado** |
| Repositorios M365 | `m365-repositories-panel.tsx`, `m365-workspace.tsx` | **Integrado + QA UI** (76 botones en tab Repositorios) |
| M365 picker / búsqueda | `m365-document-search-picker.tsx`, `m365/page.tsx` | **Integrado** |
| Precios / Proveedores | `prices/[id]/page.tsx` | **Pendiente no bloqueante** — ver abajo |

### Pruebas UI realizadas (`https://jaios.justech.do`)

| Escenario | Resultado |
|-----------|-----------|
| Empresas — «Ver documento» registro mercantil | **PASS** — abre login SharePoint (M365 vinculado) |
| Documentos Hub — `/licitador/documentos-legales` | **PASS** — botones «Ver documento» visibles y activos |
| Representantes — cédula Fausto en perfil Justech | **PASS** — botón «Ver documento» presente |
| Repositorios M365 — `/m365/operativo` → tab Repositorios | **PASS** — 76 botones «Ver documento» |
| DGCP — tab Checklist (`6b1f81e8-…`) | **PASS** — ya no crashea; carga checklist |
| Empresas — perfil Justech carga sin error | **PASS** — tras fix import `M365DocumentSearchPicker` |

### APIs probadas

| Prueba | Resultado |
|--------|-----------|
| `GET /documents/access?knowledge_asset_id=7d931a71…` (REGISTRO MERCANTIL) | **PASS** — `view_mode: external`, URL SharePoint |
| `GET /documents/access/open?knowledge_asset_id=8335bf03…` (ACTA inactivo dedup) | **PASS** — 302 al canónico SharePoint |
| `GET /documents/access?m365_file_id=a59e87ee…` | **PASS** — `m365_file`, URL SharePoint |
| `GET /documents/access?knowledge_asset_id=00000000-…0099` (inexistente) | **PASS** — `available: false`, `reason: asset_not_found` |
| Tests backend acceso documental | **6/6 PASS** |

### Errores corregidos durante integración

| Error | Fix |
|-------|-----|
| Perfil Empresas — *Application error* al cargar | Import faltante `M365DocumentSearchPicker` en `company-profile-form.tsx` |
| DGCP Checklist — crash al abrir tab | `opportunityId` no destructurado en `ChecklistTab` → pasado a `RequirementActions` |
| Links directos «Ver en M365» / `href={web_url}` | Reemplazados por `DocumentViewLink` en picker, secciones legales, plantillas, modal DGCP |
| `document_id` mezclado como `knowledgeAssetId` | Separados en `company-profile-form.tsx` |

### Pendientes menores (no bloqueantes)

1. **Precios / Proveedores — «Ver archivo origen»:** No usa `DocumentAccessService` porque el índice de precios no guarda `m365_file_id`, `document_link_id` ni `knowledge_asset_id`. Requiere ampliar el modelo de indexación. **No continuar hasta documentar y diseñar la referencia documental.**
2. **Copia local pura en QA:** Todos los `knowledge_assets` activos del tenant resuelven a SharePoint; flujo local implementado vía `local_api_path` pero sin asset de prueba dedicado.
3. **DGCP Documentos Justech:** Botones visibles tras análisis; requiere scroll en vista detalle.
4. **`documentos/repositorios` — `binding.web_url`:** Link a carpeta SharePoint (excepción deliberada, no es un documento).

---

## Representantes y validación de cédula (2026-06-10)

Migración **047** (`company_representatives`, `representative_documents`).

| # | Prueba | Resultado |
|---|--------|-----------|
| 1 | Agregar representante Fausto Ramón Santana Jiménez | **PASS** — `POST /documents/companies/{id}/representatives` → 200 |
| 2 | Asociar documento «Cédula representante» vía M365 link | **PASS** — mensaje incluye nombre del representante |
| 3 | UI/API muestra «Cédula representante — Fausto Ramón Santana Jiménez» | **PASS** — panel representantes + perfil |
| 4 | Presionar «Validar cédula» con confirmación manual | **PASS** — `POST .../documents/cedula/validate` → 200 |
| 5 | Indicador verde «Cédula validada» tras confirmar | **PASS** — `validation_status=validated` |
| 6 | Agregar segundo representante (María Pérez) | **PASS** — documentos independientes por persona |
| 7 | Cada representante tiene sus propios documentos | **PASS** — Fausto: cédula cargada; María: cédula/poder pendientes |
| 8 | Progreso no llega a 100% con validación o docs pendientes | **PASS** — score 33%, `progress_semaphore=red`, nota de pendientes |
| 9 | Campo perfil `cedula_representante` refleja estado por representante | **PASS** — badge «Cédula validada» cuando corresponde |
| 10 | Formulario externo carga y envía representantes (upsert por id/cédula) | **PASS** — GET/POST `/public/profile-form/{token}/representatives` |

**Semáforo:** verde = cargado + vigente + validado; amarillo = pendiente validar / por vencer; rojo = faltante / vencido / rechazado.

**Campos OCR futuros:** `extracted_name`, `extracted_identification_number`, `validation_method`, `validation_score` — en modelo, sin OCR activo.

---

## Fase 1 — Seguridad y navegación (2026-06-15)

### PR-1.2 Launcher por rol + OBS-01 — ✅ CERRADO

**Entorno:** `https://jaios.justech.do`  
**Scripts (histórico):** `qa_pr12_visual_postdeploy.py`, `e2e/qa-pr12-ui.spec.ts` — **eliminados 2026-06-16** (ver [`QA_FICTITIOUS_USERS_REMOVAL.md`](QA_FICTITIOUS_USERS_REMOVAL.md))

| Check | Resultado |
|-------|-----------|
| Admin ve Configuración (header + launcher) | PASS |
| Admin ve acciones DGCP (Sincronizar, Licitar) | PASS |
| Usuario no ve Configuración ni botones mutate DGCP | PASS |
| Usuario lee DGCP / Documentos / M365 | PASS |
| Ventas no mutate DGCP, ve Odoo/ventas | PASS |
| Licitaciones: DGCP + mutate, sin apps Odoo | PASS |
| `/configuracion` como usuario → redirect dashboard | PASS |
| API mutate DGCP/Odoo sin permiso → 403 | PASS |

> **Nota histórica:** Las pruebas de roles ventas/licitaciones usaron usuarios QA temporales (`qa-ventas@`, `qa-licitaciones@`) eliminados el 2026-06-16. Futuras pruebas: cuentas reales según [`QA_DATA_POLICY.md`](QA_DATA_POLICY.md).

Detalle: [`PHASE1_PR-1.2_LAUNCHER_FILTER.md`](PHASE1_PR-1.2_LAUNCHER_FILTER.md)

### PR-1.4 Redirects admin legacy — ✅ IMPLEMENTADO

Redirects 308 `/admin/*` → `/configuracion/*`. Contenido admin migrado a rutas canónicas.

Detalle: [`PHASE1_PR-1.4_ADMIN_REDIRECTS.md`](PHASE1_PR-1.4_ADMIN_REDIRECTS.md)

### PR-1.4 Auditoría rutas `/admin/*` — ✅ COMPLETADA

| Métrica | Valor |
|---------|-------|
| Referencias totales | 201 |
| Corregidas (UI + docs usuario) | 17 |
| Justificadas (API, auth, resolución) | 174 |
| Legacy intencional (redirects) | 10 |

Redirect chains verificados: un solo salto 308 (sin `/admin/usuarios` → `/configuracion` → `/configuracion/usuarios`).

Detalle: [`PHASE1_PR-1.4_ADMIN_ROUTE_AUDIT.md`](PHASE1_PR-1.4_ADMIN_ROUTE_AUDIT.md)

### PR-1.5 Nav cleanup + UX — ✅ APROBADO

| Check | Resultado |
|-------|-----------|
| Placeholders ocultos en sidebar (21 secciones) | PASS |
| Label «Empresa activa (tenant)» | PASS |
| Sidebar admin sin atajos integración duplicados | PASS |
| Componentes muertos eliminados | PASS |
| Hotfix actividad reciente / KPIs / accesos rápidos | PASS (código + validación lógica) |

Detalle: [`PHASE1_PR-1.5_NAV_CLEANUP.md`](PHASE1_PR-1.5_NAV_CLEANUP.md) — incluye auditoría UX (9 hallazgos para Fase 2).

QA visual prod inicial: [`PHASE1_PR-1.5_PROD_QA_VISUAL.md`](PHASE1_PR-1.5_PROD_QA_VISUAL.md) — WARN actividad reciente **resuelto** con hotfix PR-1.5.1 (`filterModuleDashboardData`).

---

## Referencias

- `docs/MODULE_ARCHITECTURE_AUDIT.md` — arquitectura módulos
- `docs/QA_MODULE_ARCHITECTURE.md` — QA módulos fases 0–6
- `docs/COMMERCIAL_SEARCH.md` — búsqueda comercial
- `docs/LICITACIONES.md` — módulo licitaciones
- `docs/HERMES_INTELLIGENCE.md` — centro Hermes
- `docs/CHANGELOG.md` — historial de cambios
- `docs/roadmap.md` — roadmap general
- `docs/DOCUMENT_ACCESS_SERVICE.md` — servicio unificado «Ver documento»

---

**Firma QA:** Validación automatizada + verificación manual en entorno Docker  
**Resultado final:** Fases 1–5 **APROBADAS**
