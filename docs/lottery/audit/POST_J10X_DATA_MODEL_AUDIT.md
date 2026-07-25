# POST J-10X — Data Model Audit

## Core lottery tables (SQLAlchemy)

Source: [`backend/app/models/lottery.py`](../../../backend/app/models/lottery.py)

| Model | Table |
|-------|-------|
| LotteryLottery | lottery_lotteries |
| LotteryDraw | lottery_draws |
| LotteryDrawNumber | lottery_draw_numbers |
| LotteryAlias | lottery_aliases |
| LotteryImportRun / Error | lottery_import_* |
| LotterySavedQuery / SharedQuery / Export | lottery_* |
| LotteryChatSession / Message | lottery_chat_* |
| LotteryAuditLog | lottery_audit_log |
| LotteryUserFavorite / Preferences / RecentQuery | lottery_user_* |
| LotterySyncRun / SchedulerState / SyncAlert | lottery_sync_* / scheduler |
| LotteryDrawRevision | lottery_draw_revisions |
| LotterySource / Attempt / Conflict | lottery_source* |
| LotteryAi* (usage, prompts, config, tools, packs, audit, benchmarks, alerts, tone) | lottery_ai_* |
| LotteryPredictionMotor / Run | lottery_prediction_* |

## Active universe

- Field: `lottery_lotteries.is_featured` (+ `is_aggregate = false` filter in scope).
- Policy label: `FEATURED_SEVEN` (`active_scope_policy.py`).
- Prod validated: **7** featured UUIDs; **91,937** draws (J-10X deploy report).

## Integrity rules for J-11

1. Tools must resolve lotteries by **UUID**, never display name.
2. Active analysis scope = featured only; archive via `featured=false` admin surfaces.
3. New J-11 tables (conversations generic, tool runs, provider usage, prompt compositions) must be **additive** — no alters to draw/number formulas.

## Proposed additive models (do not implement yet)

- `agent_conversations` / `agent_messages` (or generalize lottery_chat_*)
- `agent_tool_invocations` (trace_id, tool, latency, ok/deny)
- `agent_prompt_compositions` (base+role+task hashes)
- `provider_credential_refs` (encrypted secret refs, not plaintext)

## Risks

- Chat context JSONB in `lottery_chat_sessions` — fine for lottery, insufficient as global Agent Runtime store without redesign.
