# Clasificación de cambios locales (pre-commit) — Fase 0

**HEAD congelado:** `fe11597c8e5473f8452aecc4efb763728fb9da24`  
**Rama:** `feature/lottery-prompt-runtime-integration-1.0`  
**Regla:** no mezclar auth telemetry, harness, factual guard y prompt en un mismo commit.  
**Estado:** clasificación presentada; commits pendientes de autorización explícita tras RCA.

---

## 1. `backend/app/api/deps.py`

| Campo | Valor |
|-------|--------|
| Diff | +96 / −7 — telemetría en `get_current_user_optional` / `get_current_user` (`classify_access_token`, `record_auth_reject`, `request.state.auth_*`); restaura/añade `RequirePermission` + alias tipados alineados con imagen DEV |
| Motivo | RCA de HTTP 401 (S2062); trazabilidad DEV sin JWT body |
| Clase | **A. telemetría/auth** (+ alineación API con imagen que ya tenía `RequirePermission`) |
| Conservar | Sí (auth cert) |
| Afecta respuestas usuario | No (solo camino 401 / metadata request) |
| Afecta scoring Shadow | No directamente |
| Validado | Directed 401 scenarios (token_missing / malformed / valid 200; storm no reprodujo S2062) |

---

## 2. `backend/app/core/security.py`

| Campo | Valor |
|-------|--------|
| Diff | +22 / −4 — `classify_access_token()`; `verify_access_token` delega |
| Motivo | Razones normalizadas de rechazo JWT |
| Clase | **A. telemetría/auth** |
| Conservar | Sí |
| Afecta respuestas | No (mismas reglas de aceptación) |
| Afecta scoring | No |
| Validado | Conjunto con deps/auth_trace |

---

## 3. `backend/app/core/auth_trace.py` (untracked)

| Campo | Valor |
|-------|--------|
| Diff | Archivo nuevo (~47 líneas) — JSONL `/tmp/jaios_auth_401_trace.jsonl` |
| Motivo | Telemetría segura de 401 |
| Clase | **A. telemetría/auth** |
| Conservar | Sí |
| Afecta respuestas | No |
| Afecta scoring | No |
| Validado | Escritura de razones en escenarios dirigidos |

---

## 4. `backend/app/lottery/ai/analyst_reasoning/factual_guard.py`

| Campo | Valor |
|-------|--------|
| Diff | +38 / −5 — scrub “las N loterías/habilitadas”; drop `la/las` como artículo de bola; allow sample “fechas de ejemplo”; allow echoes de umbral (“más de 40”, “umbral de 40”) |
| Motivo | Falsos positivos de certificación (E0010 `extra_subjects:7`, E0008 `5 fechas`, E0038/40/42 umbral 40) — **no** corrige E0068 |
| Clase | **C. factual guard funcional** (endurecimiento anti-FP; no relaja invención de subtotales) |
| Conservar | Sí, pero **commit separado** del harness/auth y del prompt |
| Afecta respuestas | Indirecto: menos rechazos FP en Studio shadow; no cambia texto Legacy/Studio generado |
| Afecta scoring | Sí (scoring de guard/hallucination) |
| Validado | Repro local E0010/E0008/umbrales; E0068 sigue fallando con invención 94/20 |

**Nota Fase 3:** falta detector `unauthorized_breakdown` (aún no implementado en este diff).

---

## 5. Scripts del harness (`evidence/prompt_runtime/final_cert/*`)

| Archivos | `run_shadow_eligible.py/.sh`, `build_eligible_dataset.py`, `SHADOW200_ELIGIBLE_DATASET.json`, `SHADOW10/25`, `run_routing200.py/.sh`, `ROUTING200.json`, etc. |
| Motivo | Shadow elegible, clasificación de errores, concurrency=1, dataset |
| Clase | **B. harness** + **E. evidencia** |
| Conservar | Sí |
| Afecta respuestas | No |
| Afecta scoring | Solo métricas del runner |
| Validado | Shadow10 PASS; Shadow25 PASS; Shadow200 invalidado mid-run |

---

## 6. Documentación / evidencia

| Archivos | `docs/prompt_runtime/*`, `evidence/prompt_runtime/final_cert/**` (incl. INVALIDATION, E0068_EVIDENCE) |
| Clase | **E. evidencia** / docs |
| Conservar | Sí |
| Afecta producto | No |

---

## 7. Otros untracked a **no** mezclar

| Archivo | Nota |
|---------|------|
| `backend/app/services/persistent_conversation_store.py` | Fuera de alcance de esta fase — no incluir en commits de cert |
| `evidence/lottery-investigation-workspace-mvp-20260728/**` | Evidencia Routing3 previa — no mezclar |
| `docs/prompt_runtime/{CHANGELOG,MIGRATION,RELEASE,ROLLBACK}*` | Docs RC genéricos — commit aparte o diferir |

---

## Propuesta de commits (cuando se autorice)

1. `test(prompt-runtime): harden eligible shadow harness and auth telemetry`  
   → deps.py + security.py + auth_trace.py + harness scripts/docs de harness (sin factual_guard, sin prompt)

2. `fix(prompt-runtime): validate unauthorized factual breakdowns`  
   → factual_guard.py + tests (+ extensión contrato dimensiones si va en código)

3. `prompt(lottery): add Analyst Prompt 7.0.0-rc3.5`  
   → seed/publish artifacts rc3.5 only

**No commit todavía** hasta cierre de autopsia E0068 y autorización.
