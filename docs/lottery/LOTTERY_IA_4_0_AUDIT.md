# Lottery IA Conversational 4.0 — architecture & audit notes

## Real query flow

```
User → frontend /lottery/chat
  → POST /api/v1/lottery/chat/sessions/{id}/messages
  → LotteryChatService.send_message
  → ConversationState (session.context.conversation_v4)
  → understand() hybrid (rules + slot fill + follow-ups)
  → build_plan() bounded multi-tool
  → LotteryToolExecutor (typed SQLAlchemy queries)
  → Spanish template (+ optional LLM synthesis)
  → LLMRouter and/or HERMES_MODEL_API_* (Huawei ModelArts-style)
  → response + runtime_trace
```

## Huawei MaaS

- Lottery synthesis may call `HERMES_MODEL_API_URL` + `HERMES_MODEL_API_KEY` (shared JAIOS ModelArts credentials).
- Settings `huawei_modelarts_*` exist; lottery chat primarily uses Hermes Model API env vars.
- **Role:** optional natural-language synthesis after tools — **not** planning, not SQL, not memory.
- Admin: `GET /api/v1/lottery/admin/ai/runtime` (no secrets).

## Hermes

| Meaning | In Lottery path? |
|---------|------------------|
| `hermes-service` microservice | **No** |
| `HERMES_MODEL_API_*` HTTP synthesis | Optional fallback only |
| Hermes as planner/memory/tools | **No** — Conversation Manager + typed tools |

Do not claim Hermes orchestration for Lottery IA.

## Prompt

- Registry: `lottery_assistant_system_v1` / version `v1`
- Path: `backend/app/lottery/ai/prompts/lottery_assistant_system_v1.py`
- Admin list: `GET /api/v1/lottery/admin/ai/prompts`

## Constraints honored

- Stage C not started
- Nacional Día not modified
- No lottery catalog expansion / sync expansion in this change
