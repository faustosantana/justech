# JAIOS Licitaciones — Rediseño del módulo

**Versión:** 1.0  
**Fecha:** 2026-06-24  
**Estado:** Propuesta de arquitectura (sin implementación)  
**Autor:** Equipo JAIOS / Justech  

---

## 1. Resumen ejecutivo

Tras semanas de inversión en un motor universal de autollenado DOCX/PDF para ~61 plantillas DGCP, la conclusión operativa es clara: **el costo de mantener compatibilidad con decenas de formatos distintos es desproporcionado** frente al valor entregado en un proceso tan crítico como una licitación.

**Nuevo posicionamiento de producto:**

> JAIOS es la plataforma donde el equipo de Justech **prepara, controla y entrega expedientes de licitación perfectos** — con una sola fuente de verdad, un repositorio central y un checklist inteligente. El autollenado de formularios pasa a ser **ayuda opcional**, no el núcleo del producto.

**Pregunta filtro para toda nueva funcionalidad:**

> *¿Esto ayuda al equipo a preparar una licitación real más rápido?*

Si la respuesta es no, no se desarrolla en esta fase.

---

## 2. Diagnóstico del estado actual

### 2.1 Lo que funciona y se conserva

| Activo | Ubicación | Decisión |
|--------|-----------|----------|
| Modelo `DGCPOpportunity` + funnel | `dgcp_opportunity.py`, `dgcp_funnel.py` | Conservar |
| Ingesta de pliegos / process docs | `dgcp_process_storage_service.py` | Conservar |
| Motor de matching documental | `dgcp_smart_matching_engine.py` | Evolucionar → alimenta requisitos |
| Builder expediente real (ZIP) | `real_dgcp_expediente_builder.py` | **Producto principal** — unificar pipelines |
| Hermes / análisis de pliego | `DGCPBidPackageService.analyze()` | Reorientar → detección, no llenado Word |
| Repositorio M365 + knowledge | `m365_repository_*`, `knowledge_assets` | Consolidar en Repositorio Central |
| Autofill conservador (Fase 2) | `document_autofill/*` | Congelar alcance; no expandir a 61 plantillas |

### 2.2 Problemas estructurales (a eliminar)

**Duplicidad de verdad**

Hoy coexisten, para el mismo requisito:

- `dgcp_bid_packages.requirements` (JSONB)
- `dgcp_bid_packages.checklist` (JSONB)
- `dgcp_bid_packages.document_matches` (JSONB)
- Vistas UI separadas: Requisitos, Checklist, Documentos Justech, Autollenado, Expediente

Resultado documentado en producción:

| Módulo | Dice |
|--------|------|
| Requisitos | DETECTADO |
| Checklist | PENDIENTE |
| Documentos Justech | EXISTE |
| Autollenado | NINGUNO |

**Esto queda prohibido en el rediseño.**

**Dos expedientes paralelos**

- Legacy: `expediente_path` + `DGCPExpedienteService` (fuente `.py` ausente)
- Real: `real_expediente_*` + `RealDGCPExpedienteBuilder`

Confunde al usuario y duplica lógica de validación.

**Autollenado como centro de gravedad**

- Tab dedicado siempre visible
- Matriz de compatibilidad 61 plantillas
- Dependencia OAuth/caché para valor percibido
- Riesgo de alterar formato oficial

**Dashboard operativo fragmentado**

- KPIs de tenant sin workload por persona
- Tareas desconectadas del checklist
- `/apps/licitaciones/expedientes` = lista de procesos, no cola de trabajo

**Servicios huérfanos**

Varios servicios importados solo existen como `.pyc` (extractor, expediente legacy, Hermes sync). Riesgo de mantenibilidad antes de cualquier refactor.

---

## 3. Visión de producto

### 3.1 Propuesta de valor

```
Pliego detectado → Requisitos extraídos → Checklist operativo → Documentos del repositorio
       → Validación → GENERAR EXPEDIENTE → ZIP listo para DGCP
```

El usuario **nunca pregunta "¿dónde está ese documento?"** porque:

1. Todo documento vive en el **Repositorio Central**
2. Todo requisito apunta a **una referencia** (`document_ref_id`), nunca a una copia
3. Todo módulo **lee el mismo modelo** `ProcessRequirement`

### 3.2 Personas

| Persona | Necesidad principal |
|---------|---------------------|
| Gerente de licitaciones | Dashboard: qué falta, quién, vencimientos, bloqueos |
| Preparador de oferta | Checklist accionable + expediente |
| Legal / compliance | Validación, vigencia, trazabilidad |
| Comercial | Estado del proceso, fechas, riesgos |
| Admin | Repositorio, plantillas, permisos |

### 3.3 Fuera de alcance (Fase 1)

- Autollenado universal 61 plantillas
- Reconstrucción de PDF/HTML
- Nuevos motores de compatibilidad DOCX
- OAuth M365 como bloqueante operativo del producto
- Tabs duplicados de requisitos/checklist/justech

---

## 4. Arquitectura funcional

### 4.1 Diagrama de dominio

```
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESO DE LICITACIÓN                        │
│  DGCPOpportunity (code, institution, deadline, funnel_status)     │
└────────────────────────────┬────────────────────────────────────┘
                             │ 1:N
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ProcessRequirement  ← ÚNICA FUENTE DE VERDAD        │
│  requirement_key, label, category, priority, due_date            │
│  status, assignee_id, source (pliego|ley|dgcp|ia|manual)        │
│  document_ref_id → RepositoryDocument (nullable)                   │
│  template_ref_id → TemplateCatalogEntry (nullable, SNCC)          │
│  task_id → Task (nullable)                                        │
│  history[], notes[], evidence[]                                   │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│   RepositoryDocument      │    │   BidExpediente               │
│   (versionado, vigencia)    │    │   status, folder_path, zip    │
│   knowledge | m365 | upload │    │   manifest, validation_report │
└──────────────────────────┘    └──────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│   TemplateCatalogEntry   │  ← solo metadatos + enlace oficial
│   (SNCC, cartas, etc.)   │     autofill opcional por ítem
└──────────────────────────┘
```

### 4.2 Principio: referenciar, nunca copiar

| Acción | Permitido | Prohibido |
|--------|-----------|-----------|
| Asociar RPE al requisito | `document_ref_id = uuid` | Copiar PDF a carpeta del proceso |
| Generar expediente | Enlazar/snapshot read-only al ZIP | Duplicar en 3 carpetas del módulo |
| Autollenado exitoso | Nueva versión en repositorio | Sobrescribir plantilla oficial |
| SNCC F.042 completado | Marcar requisito + adjuntar versión | Modificar plantilla M365 origen |

### 4.3 Capas de aplicación

```
┌─────────────────────────────────────────────────────────┐
│  UI: Centro de Preparación (por oportunidad)             │
│  + Bandeja Operativa (gerente) + Repositorio             │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  Application Services                                    │
│  RequirementService | ExpedienteService | TaskService    │
│  RepositoryService | AnalysisService (Hermes)            │
│  AutofillService (opcional, feature-flag por form)       │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  Domain + Persistence                                    │
│  process_requirements | repository_documents | tasks     │
│  bid_expedientes | dgcp_opportunities                    │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Modelo de datos propuesto

### 5.1 Tabla `process_requirements` (nueva — reemplaza JSONB duplicado)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `opportunity_id` | UUID FK → `dgcp_opportunities` | |
| `requirement_key` | string unique(opportunity) | ej. `rpe`, `sncc_f042`, `oferta_tecnica` |
| `label` | string | Nombre legible |
| `category` | enum | legal, financial, technical, administrative, sncc_form, certification, guarantee, other |
| `mandatory` | bool | |
| `priority` | enum | critical, high, normal, low |
| `status` | enum | **ver §5.3** |
| `source` | enum | pliego, ley, dgcp, ia, manual, baseline |
| `source_evidence` | JSONB | fragmento, página, doc_id Hermes |
| `assignee_user_id` | UUID nullable | |
| `due_date` | date nullable | |
| `document_ref_id` | UUID nullable → `repository_documents` | |
| `template_ref` | JSONB nullable | `{m365_file_id, form_type, web_url}` |
| `task_id` | UUID nullable → `tasks` | |
| `autofill_allowed` | bool default false | |
| `autofill_last_result` | JSONB nullable | solo si confianza 100% |
| `notes` | text | |
| `history` | JSONB | [{at, user, action, from_status, to_status}] |
| `sort_order` | int | |
| `created_at`, `updated_at` | timestamp | |

**Índices:** `(tenant_id, opportunity_id)`, `(assignee_user_id, status)`, `(due_date)`, `(status)`.

### 5.2 Tabla `repository_documents` (evolución unificada)

Unifica hoy: `KnowledgeAsset`, `Document`, referencias M365, uploads de proceso.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `company_key` | string | justech, ademi, … |
| `title` | string | |
| `category` | enum | legal, financial, technical, sncc_template, certification, … |
| `tags` | string[] | |
| `storage_backend` | enum | knowledge_fs, m365, jaios_blob, process_upload |
| `storage_pointer` | JSONB | `{path, m365_file_id, graph_item_id, …}` |
| `mime_type` | string | |
| `valid_from`, `valid_until` | date nullable | |
| `owner_user_id` | UUID nullable | |
| `version` | int | incrementa en cada reemplazo |
| `parent_document_id` | UUID nullable | cadena de versiones |
| `checksum` | string | |
| `metadata` | JSONB | RNC, institución, etc. |
| `is_template` | bool | plantilla oficial vs documento instancia |

**Regla:** Un requisito apunta a `repository_documents.id`. Múltiples requisitos pueden compartir el mismo documento (ej. RPE vigente).

### 5.3 Estados unificados (único enum — 7 valores)

Eliminar los 20+ estados actuales (`faltante`, `encontrado_vigente`, `requiere_completado`, …).

| Estado | Significado | UI |
|--------|-------------|-----|
| `pending` | Sin documento asociado | 🔴 Pendiente |
| `detected` | IA/pliego lo identificó; aún sin doc | 🟡 Detectado |
| `available` | Documento en repositorio, vigente | 🟢 Disponible |
| `expiring` | Documento existe pero vence pronto | 🟠 Por vencer |
| `expired` | Documento vencido | 🔴 Vencido |
| `needs_review` | Existe pero requiere validación humana | 🟡 Revisar |
| `completed` | Cumplido y validado para expediente | ✅ Listo |

**Transiciones automáticas:**

- Matching encuentra doc vigente → `available`
- `valid_until` < hoy → `expired`
- `valid_until` < hoy + 30 → `expiring`
- Usuario marca validado → `completed`
- Hermes detecta en pliego sin match → `detected`

### 5.4 Tabla `bid_expedientes` (reemplaza dual tracking)

| Campo | Tipo |
|-------|------|
| `id`, `tenant_id`, `opportunity_id` | UUID |
| `status` | enum: draft, validating, ready, generated, submitted |
| `preparation_pct` | int 0-100 |
| `folder_path` | text |
| `zip_path` | text |
| `manifest` | JSONB |
| `validation_report` | JSONB |
| `generated_at`, `generated_by` | |
| `blockers` | JSONB | lista de requirement_keys pendientes |

**Deprecar:** `expediente_path`, `expediente_status` legacy en `DGCPBidPackage`.

---

## 6. Checklist inteligente

### 6.1 Generación automática al analizar licitación

Pipeline único post-ingesta de pliego:

```
1. Extracción heurística (existente)
2. Enriquecimiento Hermes (requisitos, fechas, garantías, SNCC)
3. Baseline corporativo (RPE, DGII, TSS, Registro Mercantil)
4. Reglas SNCC por tipo de procedimiento
5. Merge → upsert process_requirements (no JSONB paralelo)
6. Matching → actualizar document_ref_id + status
7. Calcular preparation_pct del expediente
```

### 6.2 Campos visibles por ítem (UI)

| Columna | Fuente |
|---------|--------|
| Requisito | `label` |
| Estado | `status` (único enum) |
| Responsable | `assignee_user_id` |
| Prioridad | `priority` |
| Fecha límite | `due_date` |
| Documento | link a repositorio vía `document_ref_id` |
| Plantilla SNCC | link M365 si `template_ref` |
| Fuente | badge: Pliego / Ley / DGCP / IA / Manual |
| Observaciones | `notes` + historial |
| Acciones | Asignar, Subir, Vincular, Validar, Crear tarea, Autollenar (si aplica) |

### 6.3 Agrupación UX

Secciones fijas (orden del expediente):

1. Documentos legales corporativos (RPE, DGII, TSS, RM)
2. Oferta técnica
3. Oferta económica
4. Garantías
5. Formularios SNCC
6. Certificaciones
7. Cartas y poderes
8. Anexos del pliego
9. Otros detectados por IA

---

## 7. Repositorio central

### 7.1 Rol

**Corazón del sistema.** Todo módulo consume `repository_documents`. No hay "Documentos Justech" como silo separado — es una **vista filtrada** del repositorio (`company_key=justech`, categorías legales/financieras).

### 7.2 Capacidades

| Función | Descripción |
|---------|-------------|
| Versionado | Cada reemplazo incrementa `version`; historial navegable |
| Vigencia | Alertas automáticas; estados `expiring`/`expired` en requisitos vinculados |
| Propietario | Responsable de mantener el documento actualizado |
| Validaciones | Registro de quién validó y cuándo |
| Etiquetas + categoría | Búsqueda transversal |
| Relación con procesos | N:M `requirement ↔ document` vía FK |
| Sync M365 / knowledge | Ingesta → `repository_documents`; no duplicar bytes |

### 7.3 Rutas UI

| Ruta | Propósito |
|------|-----------|
| `/apps/licitaciones/repositorio` | Vista maestra (reemplaza silos) |
| `/documentos/*` | Redirige o embede misma vista con filtros |

---

## 8. Formularios SNCC (rol secundario)

### 8.1 Comportamiento

Para cada requisito con `category=sncc_form`:

1. **Detectar** cuáles exige el proceso (desde pliego + baseline)
2. **Asociar** plantilla oficial (`template_ref` → M365 index)
3. **Mostrar** estado del requisito (no del autollenado)
4. **Acciones:**
   - Abrir plantilla oficial (SharePoint/web)
   - Descargar plantilla
   - Subir versión completada (nueva `repository_document`)
   - Reemplazar documento asociado
   - Marcar como completada (→ `completed` tras validación)
5. **Autollenado opcional** — botón secundario "Intentar autocompletar" solo si `autofill_allowed=true` y form en whitelist Fase 2

### 8.2 Whitelist autofill Fase 2 (referencia)

Solo cuando el flujo operativo esté estable:

- SNCC F.033, F.034, F.042 (oferta)
- Cartas estándar con plantilla estable
- Criterio: confianza 100%, formato intacto, opt-in por ítem

---

## 9. Autollenado — nueva política

### 9.1 Reglas obligatorias

```
SI confianza == 100% Y formato verificado intacto:
    → completar campo / generar versión nueva en repositorio
SI cualquier duda:
    → NO modificar documento
    → mostrar campos sugeridos en UI para copia manual
    → usuario sube versión final
```

### 9.2 Prohibiciones permanentes

- Mover tablas
- Romper estilos / tipografías / tamaños
- Reconstruir documentos desde HTML/PDF
- Generar PDF distinto al flujo oficial (DOCX plantilla → LibreOffice)
- Stubs o plantillas simplificadas
- Autollenado masivo batch como requisito operativo

### 9.3 Ubicación en UI

- **Eliminar** tab "Autollenado" como vista principal
- **Mover** a acción contextual dentro del ítem de checklist SNCC
- Feature flag global: `DGCP_SMART_AUTOFILL` default **off** en producción hasta Fase 2

### 9.4 Qué hacer con el código existente

| Componente | Decisión |
|------------|----------|
| `generic_docx_fill_engine.py` | Congelar; no extender |
| `COMPATIBILITY_MATRIX` | Archivar como referencia |
| `dgcp_autofill_batch_service.py` | Deprecar |
| OAuth M365 sync plantillas | Mantener para **acceso a plantillas**, no como KPI del producto |
| `dgcp_form_autofill_service.py` | Reducir a endpoint opt-in por `requirement_id` |

---

## 10. Expediente — producto principal

### 10.1 Acción hero: GENERAR EXPEDIENTE

Un solo botón. Un solo pipeline (basado en `RealDGCPExpedienteBuilder`, deprecar legacy).

### 10.2 Estructura de carpetas (estándar Justech)

```
{CODIGO_PROCESO}_EXPEDIENTE/
├── 01_RPE/
├── 02_DGII/
├── 03_TSS/
├── 04_Registro_Mercantil/
├── 05_Oferta_Tecnica/
├── 06_Oferta_Economica/
├── 07_Garantia/
├── 08_Formularios_SNCC/
├── 09_Certificaciones/
├── 10_Cartas_Poderes/
├── 11_Anexos/
└── _MANIFEST.json
```

Entrega: carpeta en disco + `{CODIGO}_EXPEDIENTE_DGCP.zip`.

### 10.3 Flujo de generación

```
1. Validar todos los requisitos mandatory → status in (available, completed)
2. Si blockers → mostrar lista; no generar (o generar borrador marcado INCOMPLETO)
3. Resolver document_ref_id → copiar/enlazar al árbol (snapshot inmutable con checksum)
4. Incluir manifest + reporte PDF de preparación
5. Actualizar bid_expedientes.status = generated
6. Auditoría completa
```

### 10.4 Vista Expediente (UX)

Reemplaza tab Expediente actual + RealExpedientePanel duplicado:

- **Barra de progreso** (% requisitos listos)
- **Lista de blockers** con acción directa
- **Preview** del árbol de carpetas
- **Botón GENERAR EXPEDIENTE** (primario)
- **Descargar ZIP** (secundario, post-generación)
- **Historial** de generaciones (versiones del expediente)

---

## 11. Dashboard operativo

### 11.1 Vista gerente: `/apps/licitaciones/operaciones`

| Widget | Datos |
|--------|-------|
| Procesos activos | Por funnel stage |
| Requisitos pendientes | COUNT status IN (pending, detected, needs_review) |
| Documentos vencidos / por vencer | JOIN repository_documents.valid_until |
| Tareas vencidas | tasks WHERE due < today |
| Expedientes listos | bid_expedientes.status = ready |
| Procesos bloqueados | preparation_pct < 100 AND deadline < 7d |
| Carga por responsable | GROUP BY assignee_user_id |

### 11.2 Bandeja expedientes: `/apps/licitaciones/expedientes`

Dejar de ser `OpportunitiesTable` con filtro. Convertir en **cola de trabajo**:

| Columna | |
|---------|---|
| Proceso | code + institution |
| Deadline | con semáforo |
| Preparación | preparation_pct bar |
| Blockers | count |
| Responsable lead | |
| Estado expediente | draft / ready / generated |
| Acción | Abrir preparación |

### 11.3 KPIs módulo (actualizar `dashboard-data.ts`)

Reemplazar KPIs genéricos por:

- % procesos con preparation_pct ≥ 90
- Requisitos críticos pendientes (tenant)
- Documentos corporativos vencidos
- Tareas abiertas licitaciones
- Expedientes generados esta semana

---

## 12. Tareas

### 12.1 Modelo

Extender `Task` existente; sincronización bidireccional con `process_requirements`:

| Evento | Acción |
|--------|--------|
| Requisito crítico `pending` > 48h | Auto-crear tarea (configurable) |
| Usuario "Crear tarea" en ítem | task.requirement_id FK |
| Tarea completada | Re-evaluar requisito (si doc adjunto → available) |
| Cambio assignee en requisito | Actualizar tarea |

### 12.2 Campos tarea

- Título = label del requisito
- Descripción = evidence + notes
- Fecha límite = requirement.due_date
- Responsable = requirement.assignee
- Enlace directo → Centro de Preparación del proceso

### 12.3 Notificaciones (Fase 1.5)

- Vencimiento requisito
- Documento por vencer en repositorio
- Tarea asignada
- Expediente listo para generar

---

## 13. IA — nuevo foco

### 13.1 Hermes DEJA de intentar llenar Word

### 13.2 Hermes SÍ hace

| Capacidad | Output → |
|-----------|----------|
| Detectar requisitos en pliego | `process_requirements` upsert |
| Extraer fechas críticas | `due_date`, alertas |
| Detectar garantías, muestras, SNCC | requisitos categorizados |
| Resumir pliego | panel Resumen (existente) |
| Detectar riesgos / inconsistencias | tab Riesgos |
| Recomendar documentos del repositorio | matching + explicación |
| Responder preguntas sobre la licitación | copilot contextual |
| Recomendaciones de precio (Fase 1.5) | panel comercial |

### 13.3 Pipeline analyze (simplificado)

```
process_corpus → Hermes.extract_requirements()
              → RequirementService.merge_and_persist()
              → RepositoryService.match_documents()
              → ExpedienteService.recalculate_preparation()
```

Snapshot Hermes en `bid_packages.manifest` se mantiene como **auditoría**, no como fuente de verdad operativa.

---

## 14. Arquitectura de experiencia (UX)

### 14.1 Navegación propuesta

```
Licitaciones
├── Operaciones          ← NUEVO dashboard gerente
├── Procesos             ← lista + funnel (existente, simplificado)
├── Preparar             ← NUEVO: cola expedientes / oportunidad detail
├── Repositorio          ← NUEVO: fuente única documentos
├── Análisis IA          ← pliegos, riesgos (existente)
└── Configuración        ← integraciones DGCP, Hermes
```

### 14.2 Centro de Preparación (reemplaza 13 tabs)

Una sola página por oportunidad: `/apps/licitaciones/procesos/{id}/preparar`

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│ Header: DGII-CCC-PEEX-2026-0005 · DGII · Deadline · 67%    │
│ [GENERAR EXPEDIENTE]  [Descargar ZIP]  [Asignar equipo]     │
├─────────────────────────────────────────────────────────────┤
│ Sidebar          │  Checklist (única vista)                 │
│ · Resumen        │  ┌──────────────────────────────────┐  │
│ · Checklist ★    │  │ Filtros: estado, cat, responsable │  │
│ · Documentos     │  │ Tabla / kanban por categoría        │  │
│ · Pliego         │  └──────────────────────────────────┘  │
│ · Riesgos (IA)   │  Panel detalle ítem seleccionado:       │
│ · Historial      │  · documento · plantilla · tarea · IA   │
│ · Comercial      │  · acciones contextuales                │
└─────────────────────────────────────────────────────────────┘
```

**Eliminar como tabs independientes:**

- Requisitos (fusionado en Checklist)
- Documentos Justech (fusionado → filtro categoría)
- Checklist duplicado
- Autollenado global

### 14.3 Acciones contextuales por ítem

| Tipo requisito | Acciones |
|----------------|----------|
| Documento corporativo | Vincular del repositorio · Subir · Ver vigencia |
| SNCC | Abrir plantilla · Descargar · Subir completado · Autollenar (opt) |
| Oferta técnica/económica | Vincular · Crear borrador · Odoo (existente) |
| Garantía | Subir · Marcar pendiente banco |

---

## 15. API propuesta (REST)

### 15.1 Nuevos endpoints

```
GET    /dgcp/opportunities/{id}/requirements          ← lista unificada
POST   /dgcp/opportunities/{id}/requirements/analyze  ← pipeline único
PATCH  /dgcp/opportunities/{id}/requirements/{rid}    ← assign, status, notes
POST   /dgcp/opportunities/{id}/requirements/{rid}/link-document
POST   /dgcp/opportunities/{id}/requirements/{rid}/upload
POST   /dgcp/opportunities/{id}/requirements/{rid}/task
POST   /dgcp/opportunities/{id}/requirements/{rid}/autofill  ← opt-in

GET    /repository/documents
POST   /repository/documents
GET    /repository/documents/{id}/versions

GET    /dgcp/opportunities/{id}/expediente
POST   /dgcp/opportunities/{id}/expediente/generate
GET    /dgcp/opportunities/{id}/expediente/download

GET    /dgcp/operations/dashboard                     ← gerente
```

### 15.2 Endpoints a deprecar

```
GET  .../requirements          (vista JSONB separada — reemplazar)
GET  .../checklist             (JSONB — reemplazar)
POST .../bid-package/prepare   (legacy expediente)
GET  .../bid-package/download  (legacy)
POST .../forms/autofill-preview (tab global — mover a requirement scope)
```

---

## 16. Plan de migración

### Fase 0 — Estabilización (2 semanas)

- [ ] Recuperar/reescribir servicios `.pyc` huérfanos críticos
- [ ] Feature-flag OFF autofill global en UI
- [ ] Documentar estado actual (este doc)
- [ ] Congelar trabajo en matriz 61 plantillas

### Fase 1 — Fuente de verdad (4–6 semanas)

- [ ] Migración DB: `process_requirements` + backfill desde `checklist` JSONB
- [ ] `RequirementService` único; lectura dual (JSONB + tabla) temporal
- [ ] API unificada `/requirements`
- [ ] UI: Centro de Preparación v1 (checklist único)
- [ ] Deprecar tabs Requisitos / Documentos Justech / Autollenado

### Fase 2 — Repositorio (3–4 semanas)

- [ ] Tabla `repository_documents`; migrar knowledge + document
- [ ] Vista `/repositorio`
- [ ] Matching escribe `document_ref_id`
- [ ] Estados unificados (7 valores)

### Fase 3 — Expediente producto (3 semanas)

- [ ] Unificar en `RealDGCPExpedienteBuilder`; deprecar legacy
- [ ] Tabla `bid_expedientes`
- [ ] Botón GENERAR EXPEDIENTE en header
- [ ] Bandeja `/expedientes` operativa

### Fase 4 — Operaciones (2–3 semanas)

- [ ] Dashboard gerente
- [ ] Tareas sincronizadas
- [ ] Notificaciones básicas
- [ ] KPIs actualizados

### Fase 5 — IA reorientada (continuo)

- [ ] Hermes → requirements pipeline
- [ ] Copilot contextual por proceso
- [ ] Detección riesgos incremental (on document upload)

### Fase 6 — Autofill opt-in (futuro)

- [ ] Whitelist 3–5 formularios
- [ ] Acción por ítem con confianza 100%
- [ ] Sin tab global

---

## 17. Matriz de decisión: conservar / deprecar / nuevo

| Componente actual | Decisión |
|-------------------|----------|
| `DGCPBidPackage.checklist` JSONB | **Deprecar** → `process_requirements` |
| `DGCPBidPackage.requirements` JSONB | **Deprecar** → misma tabla |
| `document_matches` JSONB | **Deprecar** → campos en requirement |
| `RealDGCPExpedienteBuilder` | **Conservar** → único builder |
| `DGCPExpedienteService` legacy | **Deprecar** |
| Tab Autollenado | **Eliminar** |
| `document_autofill/*` | **Congelar** |
| `dgcp_compliance_engine.py` | **Evolucionar** → status unificado |
| `dgcp_smart_matching_engine.py` | **Conservar** |
| Hermes pliego analysis | **Conservar** → output a requirements |
| M365 template cache | **Conservar** → solo acceso plantillas |
| 13 tabs opportunity-detail | **Reemplazar** → Centro Preparación |
| `/apps/licitaciones/expedientes` | **Rediseñar** → bandeja operativa |

---

## 18. Métricas de éxito

| Métrica | Baseline | Objetivo 90 días |
|---------|----------|------------------|
| Inconsistencias estado entre módulos | Frecuente | **0** |
| Tiempo preparar expediente DGII-type | ? | -30% |
| Clicks para encontrar documento | Alto | ≤ 2 |
| Procesos con expediente ZIP generado | ? | +50% |
| Uso diario equipo licitaciones | ? | DAU ≥ 5 |
| Incidencias autollenado formato roto | Varias | **0** (autofill off) |
| Requisitos con responsable asignado | Bajo | ≥ 80% |

---

## 19. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Migración JSONB → tabla pierde datos | Backfill script + lectura dual 2 sprints |
| Resistencia UI (menos tabs) | Centro Preparación con sidebar familiar |
| Servicios .pyc ausentes | Fase 0 rewrite antes de refactor |
| Equipo espera autofill | Comunicar Fase 6; opt-in por formulario |
| Scope creep | Pregunta filtro en cada PR |

---

## 20. Conclusión

El módulo de Licitaciones debe dejar de ser un **laboratorio de autollenado documental** y convertirse en un **sistema operativo de preparación de expedientes**.

La inversión prioritaria es:

1. **Una fila por requisito** (`process_requirements`)
2. **Un repositorio** (`repository_documents`)
3. **Un botón** (GENERAR EXPEDIENTE)
4. **Un dashboard** (qué falta, quién, cuándo)

Todo lo demás — incluido autollenado — es secundario y opt-in.

---

*Documento listo para revisión Fausto / equipo Justech. Siguiente paso: aprobación de arquitectura → Fase 0.*
