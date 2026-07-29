# Chat Pipeline Map — Lottery IA (Forensic Phase 0)

**Date:** 2026-07-29  
**Scope:** DEV forensic inventory — no behavioral changes.  
**Entry:** `POST /api/v1/lottery/chat/sessions/{session_id}/messages`

---

## End-to-end path

```
User message
  → lottery.py:send_chat_message
  → LotteryChatService.send_message
  → ConversationState.from_store
  → understand() + IntentResolver + ConversationBrain
  → HermesDecisionEngine.decide  (+ ConversationalRouter Path A/B)
  → [early exits: workspace | evidence reuse | greeting/general_chat]
  → ResearchPlanner + tools → factual template
  → AnalystReasoningLayer  OR  _synthesize
       → _synthesize_via_hermes  (Huawei ModelArts HTTP)
       → FactualGuard (reasoning path)
  → format_analyst_response / format_professional_response
  → NaturalResponseGenerator (optional enhance)
  → sanitize / disclaimer
  → ChatSendResponse
  → frontend chat/page.tsx (SimpleMarkdown + LotteryStructuredRenderer)
```

---

## Stage catalog

| # | Stage | File | Function | Lines (approx) | Input | Output | Can alter answer? |
|---|--------|------|----------|----------------|-------|--------|-------------------|
| 1 | HTTP | `backend/app/api/v1/lottery.py` | `send_chat_message` | 579–591 | `ChatMessageCreate` | `ChatSendResponse` | Soft-fail 596–609 |
| 2 | Orchestrator | `backend/app/services/lottery_chat_service.py` | `send_message` | 179+ | session + text | final dict | Yes (owns pipeline) |
| 3 | State load | `conversation_state.py` | `ConversationState.from_store` | — | `session.context` | sticky numbers/relation/asset | Contaminates follow-ups |
| 4 | Understanding | `understanding.py` | `understand` | 140+ | text + state | `UnderstandingResult` | Intent / clarify |
| 5 | IntentResolver | `intent_resolver.py` | `resolve` | 13+ | text + state | resolution | Deictic inherit |
| 6 | ConversationBrain | `conversation_brain.py` | `apply_resolution` | — | understanding | mutated state | Memory |
| 7 | Hermes decide | `hermes_decision_engine.py` | `decide` / `_decide_core` | 77 / 123 | msg + state + inv | `HermesDecision` | Routes research vs asset |
| 8 | ConversationalRouter | `conversational_router/router.py` | `route` | 52+ | msg + state | Path A/B | Blocks narrative on Path B |
| 9 | Workspace | `investigation_workspace/handler.py` | `execute_workspace_action` | 66 | decision | table/export | **No Huawei** |
| 10 | Greeting exit | `lottery_chat_service.py` | early return | 546–585 | intent greeting/chat | short reply | Skips tools/LLM |
| 11 | Research | `ResearchPlanner` / tools | — | — | plan | template + structured | Factual body |
| 12 | EvidencePackage | `analyst_reasoning/evidence_package.py` | `EvidencePackageBuilder.build` | — | facts + state | package | Context to Huawei |
| 13 | Reasoning | `reasoning_layer.py` | `AnalystReasoningLayer.run` | 67+ | package | text + telemetry | Huawei prose |
| 14 | Huawei HTTP | `lottery_chat_service.py` | `_synthesize_via_hermes` | 3326–3371 | `messages[]` | content string | Provider answer |
| 15 | FactualGuard | `factual_guard.py` | `validate` | 47 | Huawei text | accept/reject | Fallback to template |
| 16 | Formatter | `response_formatter.py` | `format_analyst_response` → `format_professional_response` | 46 / 373 / **416–418** | text + facts | sectioned markdown | **Injects Hallazgos/Detalle/Interpretación** |
| 17 | Natural enhance | `natural_response.py` | `enhance_factual_template` | 179 | text | polished text | Next-step lines |
| 18 | API serialize | `schemas/lottery_chat.py` | `ChatSendResponse` | 52 | dict | JSON | Wire |
| 19 | Frontend | `frontend/.../lottery/chat/page.tsx` | render | 602–607 | `message.content` | UI | Bold only |

---

## Prompt Studio vs runtime

| Component | Location | On live chat path? |
|-----------|----------|--------------------|
| Prompt Studio compile | `prompt_studio.py:compile_prompt_from_blocks` | **No** (admin / Control Center) |
| Live system prompt (legacy synthesize) | `lottery_analyst_system_v6.py:build_analyst_llm_messages` | Yes |
| Live reasoning prompt | `reasoning_prompt.py:build_reasoning_messages` | Yes (Analyst 2.1) |

**Finding (inventory):** Updating Prompt Studio blocks in the UI does **not** automatically mean those blocks are the system prompt of `_synthesize_via_hermes` / reasoning. Forensic capture must prove what was actually in `messages[]`.

---

## Exact Huawei call site

```3326:3367:backend/app/services/lottery_chat_service.py
async def _synthesize_via_hermes(...):
    ...
    resp = await client.post(
        url,  # settings.hermes_model_api_url
        headers={"Authorization": f"Bearer {key}", ...},
        json={"model": model, "messages": [...], "temperature": 0.2, "max_tokens": ...},
    )
    content = choices[0].message.content
    content = self._sanitize_user_facing(content)  # first transform after RAW
```

Provider label in telemetry: `huawei_modelarts`.

**Naming trap:** `HermesDecisionEngine` ≠ Huawei HTTP. Huawei is reached via `_synthesize_via_hermes` / `hermes_model_api_*` settings.

---

## Origin of «Hallazgos / Detalle / Interpretación»

**Confirmed: Python presentation layer**, not Huawei schema, not frontend.

```416:418:backend/app/lottery/ai/analyst/response_formatter.py
("Hallazgos", hallazgos),
("Detalle", _hechos_block(...)),
("Interpretación", analisis),
```

Joined as `**Title**\nbody` in `_join_sections`.

**Bypass:** when `research_meta["analyst_reasoning_preserve"] = True` after successful reasoning, the Python sectioner is skipped and Huawei (or rich fallback) prose is kept.

Frontend `SimpleMarkdown` only renders existing `**…**`; it does not invent those headings.

---

## Mutation points (ordered)

1. Soft-fail HTTP handler  
2. Sticky `ConversationState` (prior 50/90, assets)  
3. Intent misclassification (greeting vs research)  
4. Hermes / ConversationalRouter route  
5. Workspace / evidence-reuse early exits  
6. Tool factual template  
7. EvidencePackage (what Huawei is told)  
8. Huawei RAW → `_sanitize_user_facing`  
9. FactualGuard reject → template fallback  
10. `format_professional_response` (Hallazgos trio)  
11. `enhance_factual_template`  
12. Disclaimer / phrasing replace  
13. Frontend display of `content`

---

## Hypothesis for observed bug (to verify with traces — not a fix)

**Symptom:** After «Hola» → greeting, «Todo bien, ¿y tú?» returns a prior 50/90 investigation with Hallazgos/Detalle/Interpretación.

**Likely chain to prove:**

1. Turn 2 not classified as `greeting` / `general_chat` → skips L546 early exit.  
2. Sticky state still holds `active_numbers=["50","90"]` / investigation.  
3. Pipeline runs research or formatter with those subjects.  
4. `format_professional_response` adds Hallazgos/Detalle/Interpretación from **facts**, not necessarily from Huawei.

Forensic cases must show whether Huawei was even called on Turn 2.

---

## Config already present (LLM / Huawei)

| Setting | Role |
|---------|------|
| `lottery_analyst_reasoning_enabled` | Analyst 2.1 path |
| `assistant_synthesis_enabled` | Legacy synthesize gate |
| `hermes_enabled` / `hermes_model_api_url` / `hermes_model_api_key` | Huawei HTTP |
| `hermes_default_model` | Model id in payload |

**New (this audit):** `LOTTERY_FORENSIC_TRACE_*` — see ForensicTraceService; default **off** in production.
