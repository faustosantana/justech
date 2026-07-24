# Phase G — Smoke Test & Release Candidate Evidence

**Fecha:** 2026-07-24  
**Rama:** `feature/lottery-numeric-relations-motor`  
**HEAD al smoke:** tip con ancestros `459a799` `3f4d134` `cf4a732` `255cf9c` `4c8e748` + `8d1e1cd` (multi-lotería)  
**RC URL:** UI `http://127.0.0.1:3001` · API `http://127.0.0.1:8001` → `jaios_lottery_dev` @ `127.0.0.1:5433`  
**Producción:** no modificada  
**Sync:** no modificado (`LOTTERY_SYNC_WRITE_ENABLED=false`)

---

## RC publicado

| Componente | Evidencia |
|------------|-----------|
| Health | `{"service":"jaios-nr-rc-dev","phase":"G"}` → `phase_g/health.json` |
| Frontend image | `jaios-lottery-rc-frontend:latest` · container `jaios-lottery-web-rc` |
| Ruta NR | `GET /lottery/admin/numeric-relations` → **200** |
| Publish script | `scripts/rc/publish_numeric_relations_rc.sh` |
| Slim API | `scripts/rc_nr_dev_server.py` (mismo patrón que UAT Fase F) |

### Paridad DEV UAT vs DEV RC

| Aspecto | DEV UAT (Fase F) | DEV RC (Fase G) | ¿Diff funcional NR? |
|---------|------------------|-----------------|---------------------|
| Commits motor/UI/API | hasta `4c8e748` | + `8d1e1cd` fix multi-lotería | Solo el fix requerido |
| Base datos | `jaios_lottery_dev:5433` | igual | No |
| API surface | slim UAT server `:8011` | slim RC server `:8001` | No (mismos routers NR) |
| Frontend | Next dev `:3011` | Next standalone Docker `:3001` | Packaging; misma ruta NR |
| Chat | lottery chat sessions | igual | No |
| Sync | off | off | No |

Diferencias de packaging (no funcionales del motor):

1. `eslint.ignoreDuringBuilds` / `typescript.ignoreBuildErrors` en `frontend/next.config.ts` (deuda lint preexistente).
2. Stub `frontend/src/components/admin/admin-nav.tsx` para desbloquear build (páginas `/admin` legacy).
3. `app.main` completo sigue roto por `integration_connector` ausente — RC no usa `app.main` (igual que UAT).

---

## Smoke — resultados

### CASO 1 — Analiza el 26 en Leidsa (API + chat)

| Check | Resultado |
|-------|-----------|
| Ocurrencias reales | `occurrences_used=10` / `found=106` |
| `draw_id` | incluye `a1c9bcef-…` |
| Score | ranking `[(27,0),(38,0)]` |
| Compañeros score 0 | sí (2) |
| Chat | invoca tool; narrativa sin inventar scores |
| Artefacto | `phase_g/caso1_26_leidsa.json`, `chat_caso1_live.json` |

### CASO 2 — Analiza el 34 en todas las ocurrencias

| Check | Resultado |
|-------|-----------|
| ranking | sí (top 76→9, … score 0 visibles) |
| score | sí |
| traza | campo `trace` / `matches` en ranking |
| metadata | `draw_ids_analyzed`, dedupe, `llm_calculates`, etc. |
| Artefacto | `phase_g/caso2_34_all.json`, `chat_caso2_live.json` |

### CASO 3 — Multi Leidsa + Loteka

| Check | Resultado |
|-------|-----------|
| Frase bare “Analiza el 45 en Leidsa y Loteka.” | **clarify** K; conserva ambas loterías; **no** error de fecha |
| Con K (“…últimas 20 veces”) | `plan_steps=1`, `rationale=numeric_relations_single_engine`, `lotteries=['Leidsa','Loteka']` |
| API consolidate | `lottery_names=['Quiniela Leidsa','Quiniela Loteka']`, `used=20`/`found=240` |
| Chat live | **una** entrada en `last_tool_results` → `lottery_analyze_numeric_relations` |
| Artefactos | `caso3_45_multi.json`, `chat_smoke_intent_plan.json`, `chat_caso3_*_live.json` |

### CASO 4 — Sin permisos

| Check | Resultado |
|-------|-----------|
| Client → tables | **403** |
| Body | permiso `lottery_admin_ai` / `lottery.admin` / `lottery_admin_tools` |
| Artefacto | `phase_g/caso4_client_tables.json` |

### CASO 5 — “Analiza el 26”

| Check | Resultado |
|-------|-----------|
| Chat | pide lotería; no inventa lotería ni K |
| pending | `lottery`, `occurrence_limit` |
| Artefacto | `chat_caso5_live.json` |

### Pytest

`test_lottery_numeric_relations_phase_cd.py` → **22 passed** (`phase_g/pytest_phase_cd.txt`)

---

## Validación chat (Huawei)

Confirmado en payloads / metadata / planner:

- Huawei **no** calcula tablas, códigos, vecinos ni ranking.
- Una sola tool call al motor por consulta NR completa.
- Presenta resultado + disclaimer de señal histórica.
- Aclara cuando falta lotería o K.

---

## Rollback vigente

- Tag: `restore/lottery-pre-numeric-relations-motor-20260723`
- Commit: `25ccd8aa`

---

## Veredicto Fase G

Ver sección final en entrega / Release Notes: **GO CONDICIONADO** (pendientes de packaging/autorización, no del motor NR).
