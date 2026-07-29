# Current Runtime Map — Analyst Reasoning → Huawei

## Call chain

```
Usuario
→ POST /api/v1/lottery/chat/sessions/{id}/messages
→ LotteryChatService.send_message
→ understand() / ConversationalRouter (social, prediction refuse)
→ HermesDecisionEngine.decide
→ Research / tools / Workspace (deterministic when applicable)
→ EvidencePackageBuilder.build
→ ReasoningModeSelector.select
→ AnalystReasoningLayer.run
→ build_reasoning_messages()          ← INTEGRATION POINT (PromptRuntimeSelector)
     ├─ legacy (default): Analyst Reasoning 2.1 hardcoded system
     └─ studio (flags + active version): Prompt Studio compiled body + architecture contract
→ _reasoning_huawei → _synthesize_via_hermes  (Huawei / DeepSeek-V3.2, stream=false, temp=0.2)
→ RAW text
→ FactualGuard.validate
→ format_analyst_response / guardrails
→ API ChatSendResponse
```

## Routes that never call Huawei (must stay Studio-free)

- `social_chitchat` / greetings / help
- prediction / OOD refuse (deterministic)
- Workspace `asset_action` (filter/sort/export/show)
- `reuse_evidence` / NaturalResponseGenerator
- reasoning modes `skip` / `factual_answer`
- ConversationPolicy force local template

## Exact integration point

**File:** `backend/app/lottery/ai/analyst_reasoning/reasoning_prompt.py`  
**Function:** `build_reasoning_messages` → `PromptRuntimeSelector.select`

System role may be legacy or studio; user role remains Evidence Package JSON (`package.to_llm_payload()`).  
Internal `_prompt_runtime` meta is stripped before Huawei and stored in `ReasoningResult.telemetry`.

**Do not** wire Studio into `_synthesize_via_hermes` globally (also used by legacy V6 synthesizer).

## Prompt Maestro V6 (separate)

`lottery_analyst_system_v6.build_analyst_llm_messages` — fallback synthesizer when reasoning is off/exception. Out of scope for Studio→Reasoning integration unless explicitly extended later.

## Provider params (live Reasoning path)

| Param | Value |
|-------|--------|
| model | `settings.hermes_default_model` (DeepSeek-V3.2) |
| temperature | 0.2 hardcoded |
| stream | false |
| top_p | not sent |
