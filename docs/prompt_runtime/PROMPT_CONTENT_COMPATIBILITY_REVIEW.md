# Prompt Content Compatibility Review — 7.0.0-rc2

**Source UI draft:** `draft-20260729120453` (Prompt Studio — Maestro v7 Enterprise)  
**Target:** `Lottery Analyst Prompt 7.0.0-rc2` (`LOTTERY_ANALYST_REASONING_STUDIO`)  
**Date:** 2026-07-29

## Diagnosis of 7.0.0-rc1 (2472 chars)

| Finding | Detail |
|---------|--------|
| Ten block keys present | Yes |
| Required empty | None |
| Content | **Architecture-aligned summary seed**, not the UI Maestro |
| vs UI draft | UI ≈ **49295** block chars; rc1 ≈ **2296** block chars (+176 compile headers → 2472) |
| Cause | Seed invented a short Reasoning-specific prompt instead of importing Prompt Studio |

**Conclusion:** rc1 is valid as a mini-contract prompt, but **does not** contain the Prompt Studio UI content. rc2 imports the UI blocks.

## Compatibility edits (only architecture)

Each change: original → corrected → motivo.

### 1. `herramientas` — tool invocation order

**Original:** `Siempre utiliza las herramientas en este orden.`  
**Corrected:** `Hermes y el backend utilizan las capacidades en este orden (tú no las invocas):`  
**Motivo:** Huawei no decide ni invoca tools; Hermes/backend sí.

### 2. `herramientas` — Workspace ownership

**Original:** `Si existe un Workspace activo debes utilizarlo antes de iniciar cualquier nueva investigación.`  
**Corrected:** `Si existe un Workspace activo, Hermes/backend lo reutilizan… tú no operas el Workspace — solo interpretas el Evidence Package…`  
**Motivo:** Workspace opera fuera del LLM.

### 3. `herramientas` — no re-query Workspace

**Original:** `No vuelvas a consultar datos que ya existen dentro del Workspace.`  
**Corrected:** `No pidas ni inventes una nueva consulta cuando la evidencia ya está en el Evidence Package…`  
**Motivo:** El modelo no consulta Workspace/SQL.

### 4. `herramientas` — asset / SQL

**Original:** `Si existe un asset válido debes reutilizarlo… No volver a ejecutar SQL…`  
**Corrected:** Interpreta Evidence Package; `No solicites repetir consultas a la base de datos…`  
**Motivo:** SQL lo ejecuta el backend.

### 5. `respuesta` — operaciones sobre resultados

**Original:** `…debes ejecutar únicamente esa operación.`  
**Corrected:** Operaciones (mostrar/filtrar/ordenar/exportar) ocurren en Workspace fuera del LLM…  
**Motivo:** Acciones determinísticas no pasan por Huawei.

### 6. `memoria` — Utilízala (tabla)

**Original:** `No describas la tabla. Utilízala.`  
**Corrected:** No narres la tabla completa si Workspace ya la muestra; interpreta Evidence Package.  
**Motivo:** El modelo no opera tablas.

### 7. `instrucciones_especificas` — addendum

Añadido bloque **CONTRATO DE RUNTIME — ANALYST REASONING** (Hermes decide; Evidence Package; no SQL/Workspace/routing por el modelo).

## Validation

- 10/10 blocks present, none required-empty  
- `PromptStudioValidator` OK  
- Hash / chars / tokens: see `evidence/prompt_runtime/7.0.0-rc2/BLOCK_INVENTORY.json`
