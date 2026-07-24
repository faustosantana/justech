# E2E results — Phase I-6.5

**Ambiente:** DEV oficial (`jaios_lottery_dev` @ `:5433`, API `:8001`, FE `:3011`)  
**Fecha:** 2026-07-24  
**Versión activa (UUID):** `ba2940bf-698f-4bea-8a39-31536f1bcc22` — **intacta** tras borradores/playground/secret scan.

Leyenda de validación:

| Marca | Significado |
|-------|-------------|
| API | Validado por request/response HTTP |
| UI | Validado por captura / interacción visual |
| AMBOS | API + UI |

---

## A. E2E API — 34/34 PASS

Detalle crudo: `e2e_api_results.txt`.

### Caso 1 — Tablas

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| Tabla 1 = 100 | 100 filas | PASS | API |
| N=1 fórmula | `1 ÷ 1220` | PASS | API |
| Visible | `0.0008196721` | PASS | API |
| Dígitos | `00008196721` | PASS | API |
| Código | `34` | PASS | API |
| Tabla 2 N=1 | `1220 ÷ 1`, dígitos `122000000000`, código `5` | PASS | API |
| Grupo 34 T1 / 53 T2 | presentes | PASS | API |

Evidencia API: `api_responses/tables.json`

### Caso 2 — Relaciones N=26 Leidsa K=10

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| Compañeros | 27 y 38 | PASS | API |
| Score 0 visibles | ranking incluye score 0 | PASS | API |
| LLM calcula | `false` | PASS | API |
| draw_id | sin inventar matches | PASS (sample vacío en ranking score0) | API |

Evidencia API: `api_responses/analyze_26_leidsa_k10.json`

### Caso 3 — Predicción N=34 (todas ocurrencias)

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| HTTP | 200 | PASS | API |
| Motor NR | ranking del motor | PASS | API |
| No garantía | `guarantees_outcome=false` + disclaimer | PASS | API |
| Stub frequencies | NO_IMPLEMENTADO; PATCH enable → 400 | PASS | API |

Evidencia API: `api_responses/prediction_34_all.json`, `api_responses/motors.json`

### Caso 4 — Multi-lotería N=45 Leidsa+Loteka K=10

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| 2 loterías | ids/nombres consolidados | PASS | API |

Evidencia API: `api_responses/analyze_45_multi_k10.json`  
**Nota visual:** no hay captura dedicada del formulario multi-select ejecutado; **solo API**.

### Caso 5 — Prompt compilado

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| Schema bloques | identidad…reglas | PASS | API |
| Compiled body | presente, sin secreto de prueba | PASS | API |

Evidencia API: `api_responses/prompt_schema.json`, `api_responses/compiled_draft.json` (body redactado en repo)

### Caso 6 — Borrador

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| Crear desde activo | status=draft | PASS | API |
| Guardar Aclaraciones | 200 | PASS | API |
| Compare | 200 | PASS | API |
| Playground draft | `active_unchanged=true` | PASS | API |
| Activo intacto | mismo UUID | PASS | API |

### Caso 7 — Secret scan

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| PUT con `api_key=sk-…` | 400 `secreto_detectado` | PASS | API |
| Valor no persistido | no en compiled | PASS | API |

Evidencia: `secret_scan/secret_block_response.json`

### Caso 8 — Benchmark

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| P0 | 0 | PASS | API |
| P1 | 0 | PASS | API |
| can_approve | true con gates limpios | PASS | API |

Evidencia: `benchmark/benchmark_run.json`

### Caso 9 — Permisos

| Check | Esperado | Resultado | Vía |
|-------|----------|-----------|-----|
| Usuario sin permiso | HTTP **403** backend | PASS | API |

Evidencia: `permissions/noperm_tables.json`, `screenshots/permissions/28_noperm_api.json`

**Resumen API:** 34/34 PASS

---

## B. E2E VISUAL — capturas

Total PNG: **29** bajo `screenshots/`.

### Caso 1 — Tablas

| Artefacto | Contenido | Validación |
|-----------|-----------|------------|
| `screenshots/motor/01_table1.png` | Tabla 1 | UI |
| `screenshots/motor/14_table1_loaded.png` | Tabla 1 cargada | UI |
| `screenshots/motor/15_table1_number1_detail.png` | Detalle N=1 (intento click) | UI |
| `screenshots/motor/02_table2.png` | Tabla 2 | UI |
| `screenshots/motor/16_table2_number1_detail.png` | Detalle T2 N=1 | UI |
| `screenshots/motor/03_groups_t1.png` / `17_group_code_34.png` | Grupo código 34 | UI |
| `screenshots/motor/04_groups_t2.png` / `18_group_code_53.png` | Grupo código 53 | UI |

Fórmulas exactas del Caso 1: **API** (AMBOS solo si la captura muestra la fila; el detalle click no garantiza modal).

### Caso 2 — Relaciones N=26

| Artefacto | Validación |
|-----------|------------|
| `screenshots/motor/05_relaciones.png` | UI (formulario) |
| `screenshots/motor/19_relaciones_n26_leidsa_k10.png` | UI (post-intento analyze) |
| `api_responses/analyze_26_leidsa_k10.json` | API (criterios 27/38/score0) → **AMBOS** a nivel de caso |

### Caso 3 — Predicción N=34

| Artefacto | Validación |
|-----------|------------|
| `screenshots/predicciones/07_motors.png` | UI registry |
| `screenshots/predicciones/08_run.png` | UI ejecutar |
| `screenshots/predicciones/21_prediction_n34.png` | UI post-run |
| `screenshots/predicciones/22_stub_activate_attempt.png` | UI intento stub |
| Ranking/disclaimer exactos | **API** → caso **AMBOS** |

### Caso 4 — Multi-lotería

| Artefacto | Validación |
|-----------|------------|
| Solo API `analyze_45_multi_k10.json` | **API únicamente** (sin captura multi dedicada) |

### Caso 5 — Prompt compilado

| Artefacto | Validación |
|-----------|------------|
| `screenshots/prompt_studio/10_compilado.png` | UI |
| `screenshots/prompt_studio/09_bloques.png` / `23_bloques_help.png` | UI ayuda bloques |
| `screenshots/prompt_studio/11_versiones.png` | UI versiones |
| Origen/tokens/secretos | **API** → **AMBOS** |

### Caso 6 — Borrador / Playground

| Artefacto | Validación |
|-----------|------------|
| `screenshots/playground/12_playground.png` | UI |
| `screenshots/playground/25_playground_run.png` | UI run |
| Activo intacto | **API** → **AMBOS** |

### Caso 7 — Secret scan

| Artefacto | Validación |
|-----------|------------|
| `screenshots/secret_scan/24_secret_blocked.png` | UI |
| Response 400 | **API** → **AMBOS** |

### Caso 8 — Benchmark

| Artefacto | Validación |
|-----------|------------|
| `screenshots/benchmark/13_benchmark.png` | UI |
| `screenshots/benchmark/26_benchmark_gates.png` | UI post-run |
| P0/P1=0 | **API** → **AMBOS** |

### Caso 9 — Permisos

| Artefacto | Validación |
|-----------|------------|
| `screenshots/permissions/27_noperm_frontend.png` | UI (gate frontend) |
| `28_noperm_api.json` status 403 | **API** → **AMBOS** |

### Hub / Auditoría

| Artefacto | Validación |
|-----------|------------|
| `screenshots/hub/00_control_center.png` (+ browser) | UI hub secciones |
| `screenshots/motor/06_auditoria.png` / `20_auditoria_trace.png` | UI auditoría/traza |

---

## C. Limitaciones honestas

1. Caso 4 multi-lotería: **sin captura UI** del multi-select; evidencia fuerte es API.
2. Algunas interacciones Playwright (click fila N=1, analyze form) son best-effort; los asserts numéricos duros viven en API.
3. Bodies de prompts en JSON versionados fueron **redactados** (no publicar prompts).
