# Fase 0 — Checklist de riesgos y plan de rollback

**Versión:** 1.1  
**Fecha:** 2026-06-24  
**Estado implementación:** Código Fase 0 aplicado (pendiente rebuild frontend en producción)
**Alcance:** Estabilización y congelamiento autollenado universal  
**NO incluye:** reescritura, nuevas tablas, cambios API  

---

## 1. Objetivo Fase 0

| Hacer | No hacer |
|-------|----------|
| Ocultar Autollenado como tab principal | Eliminar código autofill |
| Mover acceso a formularios a flujo secundario | Borrar JSONB legacy |
| Ocultar features experimentales off-by-default | Crear `process_requirements` |
| Mantener licitaciones activas operativas | Cambiar pipeline expediente |
| Documentar rollback | Tocar producción sin flags |

---

## 2. Cambios técnicos Fase 0 (mínimos)

| Archivo | Cambio |
|---------|--------|
| `frontend/src/lib/dgcp-feature-flags.ts` | `dgcpAutofillPrimaryTabEnabled()` default `false`; acceso directo a `process.env` (requerido para rollback build-arg) |
| `frontend/src/components/dgcp/opportunity-detail.tsx` | Tabs dinámicos; botón "Formularios" si tab oculto |
| `docker-compose.yml` | `NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=false` |
| `docs/*` | Plan migración + este doc |

**Sin cambios:** backend API, base de datos, `document_autofill/*`, expediente builder.

---

## 3. Checklist de riesgos

### R1 — Pérdida de acceso a formularios ya generados

| Atributo | Valor |
|----------|-------|
| Probabilidad | Media |
| Impacto | Alto |
| Descripción | Usuario no encuentra PDFs/DOCX generados si se oculta tab |
| Mitigación | Botón "Formularios" en barra; link desde checklist `onGoToAutofill`; URL `?tab=autollenado` |
| Verificación | Abrir proceso con forms generados → descargar PDF sin regresión |
| Estado | Mitigado en diseño |

### R2 — Links guardados / bookmarks a tab Autollenado

| Atributo | Valor |
|----------|-------|
| Probabilidad | Baja |
| Impacto | Medio |
| Descripción | URLs con tab autollenado dejan de funcionar |
| Mitigación | `useSearchParams`: si `?tab=autollenado` → activar tab aunque oculto |
| Verificación | Navegar `.../dgcp/{id}?tab=autollenado` |
| Estado | Mitigado en diseño |

### R3 — Botones "Autollenar" en checklist dejan de navegar

| Atributo | Valor |
|----------|-------|
| Probabilidad | Baja |
| Impacto | Medio |
| Descripción | `onNavigateTab('autollenado')` roto |
| Mitigación | `activeTab` sigue aceptando `autollenado`; solo UI tab bar cambia |
| Verificación | Click autollenar desde ítem SNCC en checklist |
| Estado | Sin cambio de lógica |

### R4 — Feature flag mal configurado en producción

| Atributo | Valor |
|----------|-------|
| Probabilidad | Media |
| Impacto | Medio |
| Descripción | Frontend build sin flag → tab sigue visible |
| Mitigación | Default `false` en código; explicit en docker-compose |
| Verificación | Inspeccionar tabs post-deploy |
| Estado | Requiere rebuild frontend |

### R5 — Confusión del equipo ("¿dónde está autollenado?")

| Atributo | Valor |
|----------|-------|
| Probabilidad | Alta |
| Impacto | Bajo |
| Descripción | Cambio UX sin comunicación |
| Mitigación | Banner informativo en Expediente; este documento |
| Verificación | — |
| Estado | Comunicación pendiente |

### R6 — Hot-copy vs rebuild en producción

| Atributo | Valor |
|----------|-------|
| Probabilidad | Alta |
| Impacto | Alto |
| Descripción | Cambios UI no persisten si solo hot-copy backend |
| Mitigación | **Fase 0 requiere `docker compose build frontend`** |
| Verificación | Confirmar versión en browser (tab oculto) |
| Estado | Acción requerida deploy |

### R7 — `DGCP_SMART_AUTOFILL=false` rompe flujo existente

| Atributo | Valor |
|----------|-------|
| Probabilidad | Baja |
| Impacto | Alto |
| Descripción | Desactivar autofill backend bloquea generación |
| Mitigación | **Fase 0 NO cambia `DGCP_SMART_AUTOFILL`** — solo oculta tab |
| Verificación | Generar formulario desde checklist post-Fase 0 |
| Estado | Mitigado |

### R8 — Regresión en expediente / real-expediente

| Atributo | Valor |
|----------|-------|
| Probabilidad | Muy baja |
| Impacto | Alto |
| Descripción | Cambio accidental en expediente tab |
| Mitigación | Fase 0 no toca `real_dgcp_expediente_builder.py` |
| Verificación | Generar ZIP expediente real en QA |
| Estado | N/A Fase 0 |

### R9 — OAuth M365 / caché plantillas (deuda previa)

| Atributo | Valor |
|----------|-------|
| Probabilidad | Alta |
| Impacto | Bajo (post-pivot) |
| Descripción | 6 plantillas sin caché |
| Mitigación | Ya no es KPI producto; caché DGCP cubre 51/61 |
| Verificación | — |
| Estado | Aceptado como deuda |

### R10 — Servicios backend `.pyc` sin fuente

| Atributo | Valor |
|----------|-------|
| Probabilidad | Media |
| Impacto | Alto (Fase 1+) |
| Descripción | Refactor bloqueado |
| Mitigación | Recuperar fuentes en Fase 1 prep (no Fase 0) |
| Verificación | Inventario imports en `dgcp_bid_package_service.py` |
| Estado | Deuda Fase 1 |

---

## 4. Matriz riesgo × impacto

```
Impacto
  Alto  │ R6          R1, R7, R8
        │
  Medio │ R4, R5      R2, R3, R10
        │
  Bajo  │             R9
        └─────────────────────────
           Baja    Media    Alta
                  Probabilidad
```

**Riesgos críticos pre-deploy:** R1, R6, R7

---

## 5. Plan de rollback Fase 0

### 5.1 Rollback rápido (< 15 minutos)

**Opción A — Variable de entorno (preferida)**

```bash
# En /opt/jaios-app — OBLIGATORIO exportar variable antes del build
cd /opt/jaios-app
NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=true docker compose build --no-cache frontend
docker compose up -d frontend
```

**Restaurar Fase 0:**

```bash
cd /opt/jaios-app
NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=false docker compose build --no-cache frontend
docker compose up -d frontend
```

> Usar `--no-cache` evita capas Docker con el flag anterior. El flag debe leerse con acceso directo `process.env.NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB` (no `process.env[name]`).

**Opción B — Sin rebuild (emergencia)**

Si el flag se compiló como build-arg, no basta cambiar env en runtime.  
Next.js bakea `NEXT_PUBLIC_*` en build time → **siempre requiere rebuild**.

### 5.2 Rollback git

```bash
git revert <commit-fase-0>   # commits de Fase 0 únicamente
docker compose build frontend
docker compose up -d frontend
```

### 5.3 Verificación post-rollback

| # | Check | Esperado |
|---|-------|----------|
| 1 | Tab "Autollenado" visible en barra principal | Sí |
| 2 | Formularios generados descargables | Sí |
| 3 | Checklist → Autollenar navega | Sí |
| 4 | Expediente ZIP genera | Sí |
| 5 | Sin errores consola / API 500 | Sí |

### 5.4 Rollback NO aplica a

- Documentación en `docs/`
- Matriz compatibilidad archivada
- Motor autofill congelado (código sigue, no se borra)

---

## 6. Procedimiento de deploy Fase 0

```
1. Merge cambios Fase 0 a rama deploy
2. docker compose build frontend   # OBLIGATORIO
3. docker compose up -d frontend
4. Smoke test (§7)
5. Comunicar al equipo cambio UX
6. Monitorear 48h
```

**No requiere:** restart backend, migraciones DB, downtime.

---

## 7. Smoke test post-deploy Fase 0

Proceso QA: `DGII-CCC-PEEX-2026-0005` (`ae07d012-4b67-4622-8507-bff9060c632b`)

| # | Paso | PASS |
|---|------|------|
| 1 | Abrir `/dgcp/{id}` — tab Autollenado NO en barra principal | ☐ |
| 2 | Click "Formularios" → panel autollenado visible | ☐ |
| 3 | `?tab=autollenado` abre panel directo | ☐ |
| 4 | Checklist ítem SNCC → "Autollenar" navega a formularios | ☐ |
| 5 | Descargar PDF previamente generado (F.042) | ☐ |
| 6 | Tab Expediente → generar/descargar ZIP sin error | ☐ |
| 7 | Tab Checklist/Requisitos siguen funcionando (legacy) | ☐ |
| 8 | Analizar pliego → checklist se actualiza | ☐ |

---

## 8. Criterio GO / NO-GO Fase 0

| Condición | GO |
|-----------|-----|
| Smoke test 8/8 PASS | ✅ |
| Rollback probado en staging | ✅ |
| Frontend rebuild desplegado | ✅ |
| Sin regresión expediente | ✅ |
| Equipo notificado | ✅ |

**NO-GO si:** cualquier PDF/DOCX existente no descargable, o expediente ZIP falla.

---

## 9. Post Fase 0 — siguiente paso

1. Aprobación smoke test Fausto  
2. Iniciar Fase 1: migración Alembic `process_requirements`  
3. Script backfill checklist JSONB → tabla  
4. API dual-read detrás de `DGCP_REQUIREMENTS_TABLE_READ`  

---

*Fase 0 es reversible, acotada y sin cambios de datos.*
