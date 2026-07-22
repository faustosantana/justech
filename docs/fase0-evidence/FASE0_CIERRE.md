# Fase 0 — Cierre formal

**Fecha cierre:** 2026-06-25  
**Proceso QA:** `DGII-CCC-PEEX-2026-0005` (`ae07d012-4b67-4622-8507-bff9060c632b`)  
**Veredicto:** **PASS**

---

## 1. Feature flag — implementación confirmada

Archivo: `frontend/src/lib/dgcp-feature-flags.ts`

`dgcpAutofillPrimaryTabEnabled()` **NO** usa `envFlag()` ni `process.env[name]` dinámico.

Usa acceso directo:

```typescript
export const dgcpAutofillPrimaryTabEnabled = () => {
  const raw = process.env.NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB;
  if (raw === undefined || raw === "") return false;
  return raw === "1" || raw.toLowerCase() === "true";
};
```

Next.js puede inlinear este valor en build time (requerido para rollback).

---

## 2. Comando exacto de rollback

### Activar tab Autollenado en barra principal (rollback UX)

Desde `/opt/jaios-app`:

```bash
cd /opt/jaios-app
NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=true docker compose build --no-cache frontend
docker compose up -d frontend
```

Verificar: abrir cualquier proceso DGCP → tab **Autollenado** visible en barra; botón secundario **Formularios** ausente.

### Restaurar Fase 0 (estado productivo aprobado)

```bash
cd /opt/jaios-app
NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=false docker compose build --no-cache frontend
docker compose up -d frontend
```

Verificar: tab **Autollenado** oculto; botón **Formularios** visible; deep link `?tab=autollenado` operativo.

**Notas:**
- Solo afecta contenedor `frontend`. Backend/DB sin cambios.
- `--no-cache` recomendado en rollback para evitar capas Docker con flag anterior.
- El valor default en código es `false` si la variable no está definida en build.

---

## 3. Tabla de pruebas — producción

| Prueba | Esperado | Real | PASS/FAIL |
|--------|----------|------|-----------|
| Flag sin `process.env[name]` dinámico | Acceso directo a `NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB` | Confirmado en fuente (§1) | **PASS** |
| Build Fase 0 (`flag=false`) | Tab Autollenado oculto | Sin botón Autollenado en tabs; botón Formularios presente | **PASS** |
| Botón Formularios visible | Visible en barra secundaria | Botón `Formularios` al final de tabs | **PASS** |
| Botón Formularios abre autollenado | Vista SNCC / autofill | F.033, F.042, F.047, F.034 listados tras Actualizar | **PASS** |
| Deep link `?tab=autollenado` | Abre vista formularios | URL activa vista autollenado con formularios SNCC | **PASS** |
| Borradores existentes visibles | F.047 borrador, F.033/042 generados | Estados visibles en UI | **PASS** |
| PDFs descargables | Archivos intactos y legibles | 4 PDF válidos (`%PDF-`) en expediente; F.042 asociado en checklist | **PASS*** |
| Checklist → Autollenar | Navega a formularios | Click Autollenar (F.033) → vista autollenado | **PASS** |
| Rollback `flag=true` | Tab Autollenado reaparece | Tab `Autollenado` en barra principal; sin botón secundario | **PASS** |
| Restaurar `flag=false` | Tab oculto de nuevo | Tab oculto; botón Formularios reaparece | **PASS** |
| Backend / DB / JSONB | Sin cambios | Solo frontend recreado; `generated_forms` = 8 entradas | **PASS** |

\*Botón UI "Descargar PDF" en panel autofill requiere vista previa (timeout >30s, deuda pre-Fase 0). Los PDF generados existen en filesystem y siguen referenciados en checklist/requisitos.

---

## 4. Evidencia rollback (2026-06-25)

| Paso | Observación |
|------|-------------|
| Build `true` + `--no-cache` | Tab **Autollenado** visible (ref accesibilidad en barra principal) |
| Build `false` + `--no-cache` | Tab **Autollenado** ausente; **Formularios** secundario presente |

---

## 5. Estado final producción

**Fase 0 activa:** `NEXT_PUBLIC_DGCP_AUTOFILL_PRIMARY_TAB=false` (rebuild `--no-cache` aplicado).

**Fase 1:** no iniciada.
