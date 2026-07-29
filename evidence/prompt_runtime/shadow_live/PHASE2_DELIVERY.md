# Prompt Runtime Validation 1.0 — Phase 2 Delivery

**Status:** PARTIAL  
**Branch:** `feature/lottery-prompt-runtime-integration-1.0`  
**Commits:** `aaa4afe` (integration) · `7769337` (rc2) · + follow-up hotfixes pending commit  
**DEV image:** `jaios-app-backend:prompt-runtime-1.0-shadow-7769337`  
**PROD:** `jaios-app-backend:lottery-routing3-rc1-2bf9c94` — **not touched**

## Content diagnosis

| Item | rc1 seed | Prompt Studio UI draft | rc2 |
|------|----------|------------------------|-----|
| Chars compiled | 2472 | ~49k blocks / ~50k compiled | **50477** |
| Tokens est. | ~618 | — | **12619** |
| Hash | `5141d953…` | — | `e3389d1d…` |
| 10 blocks | yes (summary) | yes (full Maestro v7) | yes + compat |
| Verdict | incomplete vs UI | source of truth | **active on DEV** |

## DEV final mode

- `LOTTERY_ANALYST_PROMPT_RUNTIME_MODE=shadow`
- `LOTTERY_ANALYST_PROMPT_STUDIO_ENABLED=true`
- `LOTTERY_ANALYST_PROMPT_STUDIO_VERSION_ID=45bf3281-a0c9-4792-80c4-9033d48d8f81`
- `LOTTERY_ANALYST_PROMPT_SHADOW_LLM=true` (during tests)
- `LOTTERY_FORENSIC_TRACE_ENABLED=false` (restored after captures)

## Suites

| Suite | Result |
|-------|--------|
| Unit prompt_runtime | 20/20 (pre-hotfix) |
| Prompt50 live | 50 executed; routing OK |
| Shadow200 | **not run** |
| Cert200 / WA40 / Agent50 / Manual30 | **not re-run** this phase |
| Payload proof | **PASS** (legacy visible + studio shadow hash match) |
| Fallback/cache (unit) | PASS |
| Rollback of prompt | activate path validated; full A↔B exercise partial |

## Recommendation

**Mantener shadow en DEV** (no Studio visible). Studio invents extra subjects under guard. Fix content / verbosity, then Shadow200 + full certs.
