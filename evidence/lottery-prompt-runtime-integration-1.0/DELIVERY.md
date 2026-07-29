# Prompt Runtime Integration 1.0 — Delivery

**Status:** PARTIAL  
**Branch:** `feature/lottery-prompt-runtime-integration-1.0`  
**Base:** `lottery-conversational-routing-3.0.0-rc1` (`2bf9c94154609a15a249d7c1688c004feca57395`)  
**Date:** 2026-07-29

## Verdict

Core integration is implemented and unit-tested with **default legacy** behavior preserved. Studio is selectable only via feature flags + active Reasoning Studio version. PROD not touched. Full live Cert200/WA40/Agent50/Manual30/Prompt50 shadow (200) not executed in this delivery window → **PARTIAL**.

## Feature flags (defaults)

| Flag | Default |
|------|---------|
| `LOTTERY_ANALYST_PROMPT_RUNTIME_MODE` | `legacy` |
| `LOTTERY_ANALYST_PROMPT_STUDIO_ENABLED` | `false` |
| `LOTTERY_ANALYST_PROMPT_STUDIO_VERSION_ID` | empty |
| `LOTTERY_ANALYST_PROMPT_AB_PERCENT` | `0` |
| `LOTTERY_PROMPT_CACHE_TTL_SECONDS` | `300` |
| `LOTTERY_ANALYST_PROMPT_SHADOW_LLM` | `false` |
| `LOTTERY_FORENSIC_TRACE_ENABLED` | `false` |

## Integration point

`backend/app/lottery/ai/analyst_reasoning/reasoning_prompt.py` → `build_reasoning_messages`  
Wired from `AnalystReasoningLayer.run` / `LotteryChatService` (DB load only when studio enabled).

## Initial candidate (not activated)

See `evidence/lottery-prompt-runtime-integration-1.0/CANDIDATE_7.0.0-rc1.json`

- Version: **7.0.0-rc1**
- Hash: `5141d95385a9e5ef1b8ac8d28f41aa0f81966e2fbb2065e2b560d3d0b2ee5de3`
- Chars: **2472** · Tokens est.: **618**
- Validation: **OK**
- Status: **draft candidate** (must Publicar → Activar DEV + flags to enter runtime)

## Unit tests

`backend/tests/lottery/prompt_runtime/test_prompt_runtime_integration.py` — **15 passed**

Covers: deterministic compile, required blocks, architecture false claims, draft/published exclusion, active inclusion, hash/cache/invalidation, fallback, flags, shadow prep, ab_test, skip mode no Huawei.

## Prompt50

`evidence/lottery-prompt-runtime-integration-1.0/PROMPT50.json` — 50 cases defined. Live legacy vs studio compare + Certs: **pending DEV shadow**.

## Shadow / Certs / Latency / Tokens

| Item | Result |
|------|--------|
| Shadow 200 DEV | Not run this delivery |
| Cert200 / WA40 / Agent50 / Manual30 | Baseline RC1 green; re-run with flags default legacy pending on this branch image |
| Latency legacy vs studio | N/A (studio not live) |
| Token consumption compare | N/A |

## Recommendation

**Mantener legacy** as default. Next: seed draft on DEV → validate → publish-immutable → activate-dev catalog only → `MODE=shadow` + `STUDIO_ENABLED=true` → Prompt50 + shadow 200 → then consider `MODE=studio` on DEV. **No Production activation.**

## Maps

- `docs/prompt_runtime/PROMPT_RUNTIME_BASELINE.md`
- `docs/prompt_runtime/PROMPT_STUDIO_MAP.md`
- `docs/prompt_runtime/CURRENT_RUNTIME_MAP.md`
