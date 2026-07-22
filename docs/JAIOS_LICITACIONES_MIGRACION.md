# JAIOS Licitaciones — Plan de migración

**Versión:** 1.1  
**Fecha:** 2026-06-24  
**Aprobado por:** Fausto / Justech  
**Estado:** Plan ejecutable — Fase 0 autorizada  

---

## 1. Principios de migración

| Principio | Regla |
|-----------|-------|
| Sin big-bang | Cada fase entrega valor incremental |
| JSONB legacy | **No borrar** — lectura/fallback hasta Fase 4+ |
| Rollback | Cada fase reversible vía feature flags |
| Producción | No romper licitaciones activas |
| Autollenado | Congelar universal; acceso secundario a lo ya generado |
| Fuente de verdad | `process_requirements` coexiste con JSONB durante Fase 1 |

---

## 2. Orden de fases aprobado

| Fase | Nombre | Entregable principal |
|------|--------|----------------------|
| **0** | Estabilización | Flags, autofill secundario, rollback doc |
| **1** | `process_requirements` | Tabla + backfill + API dual-read |
| **2** | Centro Preparación v1 | Checklist único, acciones, reporte faltantes |
| **3** | Repositorio central | `repository_documents` unificado |
| **4** | Generador expediente ZIP | Validación pre-generación, parcial/final |
| **5** | Dashboard operativo | Vista gerente |
| **6** | Autofill opt-in | 3–5 formularios whitelist |

---

## 3. Tablas nuevas

### Fase 1 — `process_requirements`

```sql
CREATE TABLE process_requirements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  opportunity_id UUID NOT NULL REFERENCES dgcp_opportunities(id) ON DELETE CASCADE,
  requirement_key VARCHAR(128) NOT NULL,
  label TEXT NOT NULL,
  category VARCHAR(64) NOT NULL,
  mandatory BOOLEAN NOT NULL DEFAULT true,
  priority VARCHAR(16) NOT NULL DEFAULT 'normal',
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  source VARCHAR(32) NOT NULL DEFAULT 'manual',
  source_evidence JSONB NOT NULL DEFAULT '{}',
  assignee_user_id UUID REFERENCES users(id),
  due_date DATE,
  document_ref_type VARCHAR(32),          -- knowledge | document | m365 | upload | null
  document_ref_id UUID,                 -- FK polimórfica vía ref_type (Fase 3 → repository_documents)
  template_ref JSONB,                   -- {m365_file_id, form_type, web_url, name}
  task_id UUID REFERENCES tasks(id),
  autofill_allowed BOOLEAN NOT NULL DEFAULT false,
  autofill_last_result JSONB,
  notes TEXT,
  history JSONB NOT NULL DEFAULT '[]',
  sort_order INT NOT NULL DEFAULT 0,
  legacy_checklist_item_id UUID,        -- trazabilidad backfill
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, opportunity_id, requirement_key)
);
CREATE INDEX ix_pr_opp ON process_requirements(tenant_id, opportunity_id);
CREATE INDEX ix_pr_assignee ON process_requirements(assignee_user_id, status);
CREATE INDEX ix_pr_due ON process_requirements(due_date) WHERE due_date IS NOT NULL;
```

**Estados aprobados (8):**

`pending` | `detected` | `associated` | `needs_review` | `valid` | `expired` | `not_applicable` | `completed`

### Fase 3 — `repository_documents`

```sql
CREATE TABLE repository_documents (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  company_key VARCHAR(64) NOT NULL,
  title TEXT NOT NULL,
  category VARCHAR(64) NOT NULL,
  tags TEXT[] DEFAULT '{}',
  storage_backend VARCHAR(32) NOT NULL,
  storage_pointer JSONB NOT NULL,
  mime_type VARCHAR(128),
  valid_from DATE,
  valid_until DATE,
  owner_user_id UUID,
  version INT NOT NULL DEFAULT 1,
  parent_document_id UUID REFERENCES repository_documents(id),
  checksum VARCHAR(128),
  metadata JSONB DEFAULT '{}',
  is_template BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Fase 4 — `bid_expedientes`

```sql
CREATE TABLE bid_expedientes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  opportunity_id UUID NOT NULL UNIQUE,
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  preparation_pct INT NOT NULL DEFAULT 0,
  is_partial BOOLEAN NOT NULL DEFAULT false,
  folder_path TEXT,
  zip_path TEXT,
  manifest JSONB NOT NULL DEFAULT '{}',
  validation_report JSONB NOT NULL DEFAULT '{}',
  blockers JSONB NOT NULL DEFAULT '[]',
  generated_at TIMESTAMPTZ,
  generated_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4. Datos que se migran

### Fase 1 backfill: `dgcp_bid_packages.checklist` → `process_requirements`

| Campo JSONB | Campo tabla | Transformación |
|-------------|-------------|----------------|
| `requirement_key` | `requirement_key` | directo |
| `requirement` | `label` | directo |
| `tipo` | `category` | mapa categorías |
| `mandatory` | `mandatory` | directo |
| `status` | `status` | **mapa a 8 estados** (ver §5) |
| `assignee` | `assignee_user_id` | lookup por email si existe |
| `document_id` | `document_ref_id` + `document_ref_type=document` | |
| `knowledge_asset_id` | `document_ref_id` + `document_ref_type=knowledge` | |
| `m365_file_id` | `template_ref` o `document_ref` | según tipo |
| `form_type` | `template_ref.form_type` | |
| `task_id` | `task_id` | directo |
| `id` | `legacy_checklist_item_id` | trazabilidad |
| `notes`, `note_history` | `notes`, `history` | merge |

**No migrar en Fase 1:** `requirements` JSONB (queda legacy; Hermes evidence se lee de ahí hasta Fase 5).

### Fase 3 backfill: knowledge + documents → `repository_documents`

| Origen | Destino |
|--------|---------|
| `knowledge_assets` | `repository_documents` (storage_backend=knowledge_fs) |
| `documents` (JAIOS platform) | `repository_documents` (storage_backend=jaios_blob) |
| `m365_repository_files` (plantillas) | `is_template=true` |

### Fase 4: expediente

| Origen | Destino |
|--------|---------|
| `real_expediente_*` en bid_package | `bid_expedientes` |
| `expediente_*` legacy | **No migrar** — deprecar lectura |

---

## 5. Mapeo de estados legacy → nuevos

| Estado legacy (actual) | Estado nuevo |
|------------------------|--------------|
| `faltante`, `pendiente` | `pending` |
| `detectado`, `encontrado` | `detected` |
| `encontrado_vigente`, `vinculado`, `pdf_final_generado` | `associated` |
| `requiere_revision`, `requiere_completado`, `borrador_pendiente` | `needs_review` |
| `validado`, `completo`, `listo_firma` | `valid` |
| `vencido` | `expired` |
| `no_aplica`, `excluido` | `not_applicable` |
| `completado`, `cerrado` | `completed` |

Durante dual-read: si `process_requirements` vacío → fallback JSONB checklist.

---

## 6. Datos que quedan legacy (no borrar)

| Almacén | Hasta fase | Uso fallback |
|---------|------------|--------------|
| `dgcp_bid_packages.checklist` | Fase 4+ | Dual-read Fase 1–3 |
| `dgcp_bid_packages.requirements` | Fase 5+ | Hermes evidence UI |
| `dgcp_bid_packages.document_matches` | Fase 3+ | Matching audit |
| `dgcp_bid_packages.manifest` | Indefinido | Auditoría Hermes |
| `expediente_path`, `expediente_status` | Fase 4 | Legacy expediente download |
| `generated_forms` en bid_package | Indefinido | Formularios ya generados |
| Autofill outputs en expediente storage | Indefinido | PDFs/DOCX existentes |

---

## 7. Estructura expediente aprobada (Fase 4)

```
01_Documentos_Legales
02_Documentos_Fiscales_y_Seguridad_Social
03_Registro_Proveedor_RPE
04_Oferta_Tecnica
05_Fichas_Tecnicas_y_Catalogos
06_Oferta_Economica
07_Garantias
08_Formularios_SNCC
09_Certificaciones_Especiales
10_Cartas_y_Declaraciones
11_Anexos_del_Proceso
12_Evidencias_Soportes
```

Reemplaza `REAL_EXPEDIENTE_FOLDERS` actual en `real_expediente_classifier.py`.

---

## 8. Endpoints afectados

### Fase 0 (sin cambios API)

Solo UI + feature flags.

### Fase 1

| Acción | Endpoint |
|--------|----------|
| **Nuevo** | `GET /dgcp/opportunities/{id}/preparation/requirements` |
| **Nuevo** | `PATCH /dgcp/opportunities/{id}/preparation/requirements/{rid}` |
| **Nuevo** | `POST /dgcp/opportunities/{id}/preparation/requirements/{rid}/actions/{action}` |
| **Dual-read** | `GET .../checklist` — lee tabla si flag ON, else JSONB |
| **Sin cambio** | `POST .../requirements/analyze` — escribe tabla + JSONB |
| **Deprecar UI** | tabs que no usen nuevo endpoint |

Acciones: `associate`, `upload`, `validate`, `reject`, `not_applicable`, `note`, `replace`, `task`, `download`.

### Fase 2

| **Nuevo** | `GET .../preparation/summary` (%, blockers) |
| **Nuevo** | `GET .../preparation/missing-report` |

### Fase 4

| **Unificar** | `POST .../expediente/generate?mode=partial|final` |
| **Validar** | `POST .../expediente/validate` (pre-check) |
| **Deprecar** | `POST .../bid-package/prepare` |
| **Deprecar** | `POST .../real-expediente/generate` → alias |

---

## 9. UI afectada

### Fase 0

| Componente | Cambio |
|------------|--------|
| `opportunity-detail.tsx` | Autollenado fuera de tabs principales |
| `opportunity-bid-section.tsx` | Acceso "Formularios" secundario; `onGoToAutofill` preservado |
| `dgcp-feature-flags.ts` | `DGCP_AUTOFILL_PRIMARY_TAB=false` |
| Banner informativo | Mensaje rediseño en expediente |

### Fase 1–2

| **Nuevo** | `/dgcp/{id}/preparar` o tab "Preparar" |
| **Ocultar** | tabs Requisitos, Checklist, Documentos Justech (flag) |
| **Mantener** | Expediente, Autollenado secundario, Tareas |
| **Nuevo** | `PreparationCenterPanel` |

### Fase 3

| **Nuevo** | `/apps/licitaciones/repositorio` |
| **Redirect** | documentos justech → filtro repositorio |

### Fase 4

| Botón hero | GENERAR EXPEDIENTE con modal validación |
| Modal | Faltantes / vencidos / parcial vs final |

---

## 10. Feature flags

| Flag | Fase | Default prod | Rollback |
|------|------|--------------|----------|
| `DGCP_AUTOFILL_PRIMARY_TAB` | 0 | `false` | `true` |
| `DGCP_SMART_AUTOFILL` | 0 | `true` (backend) | `false` desactiva acciones |
| `DGCP_PREPARATION_CENTER` | 2 | `false` → `true` | `false` |
| `DGCP_REQUIREMENTS_TABLE_READ` | 1 | `false` → `true` | `false` → JSONB |
| `DGCP_REQUIREMENTS_TABLE_WRITE` | 1 | `false` → `true` | `false` → solo JSONB |
| `DGCP_LEGACY_TABS_HIDDEN` | 2 | `false` → `true` | `false` |
| `DGCP_REPOSITORY_UNIFIED` | 3 | `false` | `false` |
| `DGCP_EXPEDIENTE_V2` | 4 | `false` | `false` → real-expediente actual |
| `DGCP_AUTOFILL_PER_ITEM` | 6 | `false` | `false` |

**Frontend:** prefijo `NEXT_PUBLIC_` en cada flag.

---

## 11. Rollback por fase

Ver documento dedicado: `JAIOS_LICITACIONES_FASE0_RIESGOS_ROLLBACK.md`

Resumen:

| Fase | Rollback | Tiempo estimado |
|------|----------|-----------------|
| 0 | Flags UI → rebuild frontend | < 15 min |
| 1 | `DGCP_REQUIREMENTS_TABLE_*=false` | < 5 min |
| 2 | `DGCP_PREPARATION_CENTER=false` | < 15 min |
| 3 | `DGCP_REPOSITORY_UNIFIED=false` | < 30 min |
| 4 | `DGCP_EXPEDIENTE_V2=false` | < 15 min |

**Nunca rollback destructivo:** tablas nuevas se ignoran, no se drop en rollback.

---

## 12. Criterios de PASS por fase

### Fase 0 — Estabilización

- [ ] Tab Autollenado no visible en barra principal (flag off)
- [ ] Acceso a formularios generados vía "Formularios" / checklist item / URL `?tab=autollenado`
- [ ] PDFs/DOCX existentes descargables sin regresión
- [ ] Licitación DGII-CCC-PEEX-2026-0005 operativa end-to-end
- [ ] `DGCP_SMART_AUTOFILL=true` mantiene autofill por ítem en checklist
- [ ] Rebuild frontend con flags rollback probado

### Fase 1 — process_requirements

- [ ] Migración backfill 100% ítems checklist → tabla
- [ ] Dual-read: mismo conteo estados JSONB vs tabla
- [ ] Escritura dual: analyze actualiza ambos
- [ ] Rollback flag: UI vuelve a JSONB sin error
- [ ] 0 regresiones en API checklist existente

### Fase 2 — Centro Preparación v1

- [ ] Checklist único agrupado por categoría
- [ ] 10 acciones básicas funcionan
- [ ] Reporte faltantes genera PDF/JSON
- [ ] Expediente parcial con confirmación explícita
- [ ] Estados solo usan 8 valores aprobados
- [ ] Requisitos/Checklist/Justech tabs ocultos (flag) pero accesibles rollback

### Fase 3 — Repositorio

- [ ] Documento asociado resuelve desde `repository_documents`
- [ ] Sin copias duplicadas entre módulos
- [ ] Vigencia actualiza estado `expired` automático

### Fase 4 — Expediente ZIP

- [ ] Validación pre-generación bloquea final si faltantes
- [ ] 12 carpetas correctas
- [ ] Parcial marcado `is_partial=true` en manifest
- [ ] Final solo con todos mandatory `valid|completed`

### Fase 5 — Dashboard

- [ ] KPIs operativos por responsable
- [ ] 0 inconsistencias estado entre vistas

### Fase 6 — Autofill opt-in

- [ ] Solo 3–5 forms en whitelist
- [ ] Confianza < 100% no modifica DOCX
- [ ] 0 stubs

---

## 13. Primer entregable funcional (Fase 2 scope, diseño en Fase 1)

**Centro de Preparación v1:**

```
Header: proceso · deadline · 42% · [Generar expediente parcial]
├─ Grupo: Documentos legales (3/5)
├─ Grupo: Oferta técnica (1/2)
├─ Grupo: Formularios SNCC (2/4)
└─ Panel ítem: acciones + documento + notas
Footer: [Descargar reporte faltantes]
```

**No incluye en v1:** dashboard gerente, repositorio unificado, autofill nuevo.

---

## 14. Calendario indicativo

| Fase | Duración | Dependencia |
|------|----------|-------------|
| 0 | 3–5 días | — |
| 1 | 3–4 semanas | Fase 0 |
| 2 | 2–3 semanas | Fase 1 |
| 3 | 3–4 semanas | Fase 1 |
| 4 | 2–3 semanas | Fase 2 + 3 |
| 5 | 2 semanas | Fase 4 |
| 6 | TBD | Fase 4 estable |

---

*Documento vivo — actualizar al cerrar cada fase.*
