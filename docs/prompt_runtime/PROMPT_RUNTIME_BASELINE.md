# Prompt Runtime Integration 1.0 — Baseline

**Branch:** `feature/lottery-prompt-runtime-integration-1.0`  
**Base tag:** `lottery-conversational-routing-3.0.0-rc1`  
**Base commit:** `2bf9c94154609a15a249d7c1688c004feca57395`  
**Created:** 2026-07-29T19:20:00Z

## Confirmed environment

| Check | Result |
|-------|--------|
| Working tree for tracked files | Clean at branch creation from tag |
| DEV image | `jaios-app-backend:routing3-rc1e` healthy |
| DEV `/api/v1/health` | 200 |
| PROD image | `jaios-app-backend:lottery-routing3-rc1-2bf9c94` healthy |
| PROD touched this phase | **No** |
| Default forensics | `lottery_forensic_trace_enabled=false` |

## Certified baseline (Routing 3.0)

- Cert200 200/200, WA40 40/40, Agent50 50/50, Manual30 30/30
- Release tag: `lottery-conversational-routing-3.0.0-rc1`

## Integration goal

Allow runtime to choose safely between:

- **legacy:** Analyst Reasoning 2.1 hardcoded system prompt
- **studio:** Prompt Studio compiled / active published body

Default: **`legacy`**. Studio never affects deterministic local routes.

## Non-goals this phase

- No PROD deploy / activation
- No Evidence Package schema change
- No Routing 3.0 / Workspace / Motor Matemático changes
- No deletion of Analyst Reasoning 2.1
