# Fase 0 — Smoke test producción

**Fecha:** 2026-06-25  
**Proceso QA:** `DGII-CCC-PEEX-2026-0005` (`ae07d012-4b67-4622-8507-bff9060c632b`)  
**URL:** https://jaios.justech.do/dgcp/ae07d012-4b67-4622-8507-bff9060c632b  
**Deploy:** solo `frontend` (`docker compose build frontend && docker compose up -d frontend`)  
**Backend / DB / JSONB:** sin cambios  

---

## Condiciones cumplidas

| # | Condición | Estado |
|---|-----------|--------|
| 1 | No tocar backend | ✅ |
| 2 | No tocar DB | ✅ |
| 3 | No tocar JSONB legacy | ✅ (`generated_forms`: 8 entradas intactas) |
| 4 | No eliminar borradores/PDF | ✅ |
| 5 | Acceso Formularios + `?tab=autollenado` | ✅ |
| 6 | Rollback con flag `true` | ✅ probado |

---

## Smoke test

| # | Criterio | Resultado | Evidencia |
|---|----------|-----------|-----------|
| 1 | Tab **Autollenado** NO en barra principal | **PASS** | Captura antes/después en sesión QA |
| 2 | Botón **Formularios** visible | **PASS** | Extremo derecho de tabs |
| 3 | Botón Formularios abre vista autollenado | **PASS** | SNCC F.033/042/047/034 listados |
| 4 | Borradores SNCC visibles | **PASS** | F.047 "Borrador generado"; F.033/042 "Generado" |
| 5 | PDFs existentes descargables | **PASS*** | 4 PDF en disco; UI requiere vista previa (timeout 30s preexistente) |
| 6 | Checklist → Autollenar → formularios | **PASS** | Navegación desde ítem SNCC F.033 |
| 7 | Requisitos operativo | **PASS** | 27 ítems con documentos asociados |
| 8 | Checklist operativo | **PASS** | 1/27 cumplidos, acciones visibles |
| 9 | Docs. Proceso / Documentos Justech | **PASS** | Tabs cargan sin error |
| 10 | Expediente operativo | **PASS** | Avance 14.6%, faltantes listados |
| 11 | Deep link `?tab=autollenado` | **PASS** | Abre vista formularios sin tab principal |
| 12 | Backend sin restart | **PASS** | Solo frontend recreado |

\*PDF: archivos verificados en `/var/jaios/expedientes/.../02_Formularios_SNCC/` (F.033, F.042, F.047 PDFs presentes). Botón "Descargar PDF" depende de generar vista previa; timeout >30s es deuda pre-Fase 0, no regresión de deploy.

---

## Rollback probado

```bash
NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=true docker compose build frontend
docker compose up -d frontend
```

**Resultado:** tab **Autollenado** reaparece en barra principal; botón secundario Formularios desaparece.

**Restauración Fase 0:**

```bash
NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=false docker compose build frontend
docker compose up -d frontend
```

### Fix aplicado durante QA

`dgcpAutofillPrimaryTabEnabled()` usaba `envFlag(name)` con clave dinámica — Next.js no inlinea `process.env[name]`. Se cambió a acceso directo `process.env.NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB` para que el rollback por build-arg funcione.

---

## Veredicto

# **PASS — Fase 0**

Fase 1 (`process_requirements`) **no iniciada** — pendiente confirmación explícita post-validación.
