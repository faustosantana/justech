# Huawei End-to-End Trace Report — Forensic Audit

**Date:** 2026-07-29  
**Environment:** DEV (`jaios-workspace-dev-api`, port 8022)  
**Production modified:** **NO**  
**Behavioral fixes applied:** **NO** (instrumentation only)

---

## Executive answers (evidence-backed)

### 1. ¿Prompt Studio está conectado al runtime real?
**No.** Live chat uses `reasoning_prompt.py` / Analyst Reasoning Layer system text and Evidence Package JSON. Prompt Studio `compile_prompt_from_blocks` is admin-only.

Evidence: `04_prompt_compiled.txt` begins with «Eres el Analyst Reasoning Layer de Lottery Analyst 2.1…» and `prompt_source_note` in events states it is **not** Prompt Studio blocks.  
Artifact: `artifacts/forensics/lottery-chat-79141985a6414f669ce93271b1582dc5/`

### 2. ¿Todos los bloques actualizados aparecen en el payload final?
**No** — Prompt Studio UI blocks are not the runtime system prompt. Updating Prompt Studio does not change `_synthesize_via_hermes` messages.

### 3. ¿Existe un prompt hardcoded adicional?
**Yes** — Analyst Reasoning system prompt (hardcoded builder) + Evidence Package as user message.

### 4–5. ¿Caché de prompt / invalidación?
No Prompt Studio cache on the chat path. Runtime builds messages per turn.

### 6–8. ¿Qué se envió a Huawei / contexto / investigación anterior?
See **PIEZA 1**. On research turns, Evidence Package includes subjects, counts, sample dates. On contaminated chitchat turn, **Huawei was not called**.

### 9–10. ¿Qué respondió Huawei / Hallazgos?
On research turn, Huawei returned markdown with **Respuesta directa** / **Explicación / Interpretación** (not the Python Hallazgos trio).  
On contaminated «Todo bien, ¿y tú?», Huawei was **not** invoked.

### 11. Si no fue Huawei, ¿quién agregó Hallazgos/Detalle/Interpretación?
**`format_analyst_response` → `format_professional_response`**  
File: `backend/app/lottery/ai/analyst/response_formatter.py`  
Proven by transform on contaminated turn.

### 12. ¿Quién insertó 50 y 90?
Sticky `ConversationState` / active investigation (`subjects=["50","90"]`) + factual template / formatter using those facts — **before** formatter headings were added.

### 13. ¿Por qué «Todo bien, ¿y tú?» fue tratado como consulta histórica?
1. Intent = `clarification_response` (not `greeting` / `general_chat`) → greeting early exit skipped.  
2. Hermes = `contextual_follow_up` / `default_research` with `inherited_subjects=["50","90"]`.  
3. Pipeline re-ran research/template path with sticky same-day investigation.  
4. Formatter wrapped template into Hallazgos/Detalle/Interpretación.

### 14. Clasificación del fallo
**Clasificación incorrecta + memoria/investigación sticky contaminada + formatter** (no Huawei, no Prompt Studio, no frontend invention).

### 15. Backend vs frontend
Final backend `content` matches rendered text artifact (`11_frontend_rendered_text.txt`). Frontend only displays API `message.content`.

### 16. Primer punto de desviación
**Intent classification / Hermes route** for «Todo bien, ¿y tú?» — first wrong fork is treating chitchat as `contextual_follow_up` with inherited 50/90 instead of conversational early exit.

---

## PIEZA 1 — Payload real enviado a Huawei

| Field | Value |
|-------|-------|
| Resultado | **CAPTurado** en turno de investigación |
| Correlation ID | `lottery-chat-79141985a6414f669ce93271b1582dc5` |
| Archivo | `artifacts/forensics/lottery-chat-79141985a6414f669ce93271b1582dc5/05_llm_payload_sanitized.json` |
| Model | `DeepSeek-V3.2` |
| Messages | system (reasoning layer) + user (Evidence Package JSON, ~21k chars) |
| Hallazgo | Payload = Reasoning prompt + Evidence Package — **not** Prompt Studio compiled blocks |

On contaminated chitchat: **no LLM request** (`05`/`06`/`07` absent).

---

## PIEZA 2 — Respuesta RAW de Huawei

| Field | Value |
|-------|-------|
| Resultado | **CAPTurado** |
| Archivo | `.../06_huawei_raw_response_sanitized.json` + `07_huawei_extracted_content.txt` |
| HTTP | 200 |
| Latency | ~24–34s typical |
| Content style | `**Respuesta directa**` / `**Explicación / Interpretación**` |
| Hallazgo | Huawei did **not** emit Python headings `Hallazgos` / `Detalle` / `Interpretación` |

Contaminated chitchat: Huawei **not called**.

---

## PIEZA 3 — Transformación hasta respuesta final

| Field | Value |
|-------|-------|
| Correlation ID (bug) | `lottery-chat-fadc2ab2fcec4e948e3306925bd4e2b6` |
| Archivo | `.../08_transformations.json` + `12_trace_summary.md` |
| Primer componente que modificó | `format_analyst_response` (`response_formatter.py`) |
| Change | Added headings `Hallazgos`, `Detalle`, `Interpretación`, `Observación` |
| provider_used | `local_template` |
| synthesis_fallback | `true` |

---

## Controlled cases

### Case A — clean greeting
- T1 `Hola` → conversational OK  
- T2 `Todo bien, ¿y tú?` → conversational OK (clean session)  
CIDs: `lottery-chat-1f4ebca8105348519195ffddc5b079ec`, `lottery-chat-7e112e309ee5408f933f0f76725aedcb`

### Case A — contaminated (reproduces production symptom)
1. Research 50+90  
2. `Hola` → greeting OK  
3. `Todo bien, ¿y tú?` → **returns 50/90 + Hallazgos**  
CIDs: `e1b029af…`, `42ac232a…`, **`fadc2ab2…`** (failure turn)

### Case B — ops
- T1 research OK (Huawei)  
- T2 `Muéstrame las fechas.` → **still narrative research** (`hermes_turn_type=contextual_follow_up`, not workspace) — documented bug, not fixed  
- T3–T5 workspace table ops OK  

### Case C — topic switch
- T1 research OK  
- T2 `Ahora analiza el 35.` → soft failure / incomplete (documented, not fixed)

---

## Root cause (demonstrated)

**Confirmado.**

For the observed «Hola / Todo bien» bug after a prior investigation in the **same session**:

1. Sticky active investigation keeps subjects `50`/`90`.  
2. Chitchat is **not** classified as `greeting`/`general_chat`.  
3. Hermes routes to `contextual_follow_up` + `default_research`.  
4. Local factual template rebuilds the coincidence answer.  
5. `format_professional_response` injects **Hallazgos / Detalle / Interpretación**.  
6. Huawei is **not** involved on that turn.  
7. Prompt Studio updates are irrelevant to this path.

---

## Recommendation (do not implement yet)

1. Extend conversational early-exit to cover chitchat / social follow-ups (`Todo bien`, `¿y tú?`, etc.) even when an investigation is sticky.  
2. Or: clear / ignore sticky investigation when intent is non-analytic social talk.  
3. Separately: ensure «Muéstrame las fechas» maps to workspace `show_results` when an asset exists (Case B T2).  
4. Do not expect Prompt Studio UI saves to change runtime until Prompt Studio is wired into `_synthesize_via_hermes` / reasoning builders (if that is a product goal).

---

## Production confirmation

- No production deploy.  
- No production config change.  
- Repo default: `lottery_forensic_trace_enabled=False`.  
- DEV container temporarily enabled for capture only.
