# POST J-10X / PRE J-11 — Current State Audit

**Branch:** `audit/nr-post-j10x-pre-j11`  
**Base:** `564a8c0`  
**Worktree:** `/Users/faustosantana/Projects/justech-audit-post-j10x`  
**Production:** intact (`jaios-app-*:j10x-20260724`) — not modified by this audit  
**Date (UTC):** 2026-07-25

---

## 1. What is correctly built

1. **Single product identity (J-10X):** AppShell sidebar label `Lottery IA Control Center`; nested Control Center “Inteligencia/Metodología” nav removed ([`control-center/layout.tsx`](../../../frontend/src/app/(platform)/lottery/admin/control-center/layout.tsx)).
2. **FEATURED_SEVEN central policy:** `active_scope.py` + `active_scope_policy.py` (`ANALYSIS_SCOPE_LABEL = "FEATURED_SEVEN"`); historical routes clamp via `_clamp_scope_ids`.
3. **Numeric Relations motor centralized:** formulas only in `table1.py` / `table2.py` / `analysis.py`; frontend has **zero** formula arithmetic.
4. **Methodology version stamped:** `nr-historical-relations-j1.0.0` in `historical/version.py`; emitted by NumberExplorer + historical services.
5. **Ordinary product scope (J-10H):** dashboard/catalog/list default to `is_featured`.
6. **Redirect consolidation:** legacy `/search|/compare|/statistics` + groups-table* + numeric-relations soft redirects.
7. **Provider Gateway reusable:** `LLMRouter` + providers in `backend/app/llm/`.
8. **Lottery Tool Executor:** `LotteryToolExecutor` + typed tools + RBAC (`lottery_tools.py`, `lottery_ai_contracts.py`).
9. **Conversation pipeline (lottery-scoped):** understanding → planner → tools → narrative in `backend/app/lottery/ai/`.
10. **Strong NR/history unit tests:** 34 `test_lottery*.py` files covering T1/T2, history J1–J9, active scope, AI admin.

## 2. Technical debt (summary)

See [`POST_J10X_TECHNICAL_DEBT_REGISTER.md`](POST_J10X_TECHNICAL_DEBT_REGISTER.md).

Highest:

| ID | Issue | Blocks J-11? |
|----|-------|--------------|
| TD-001 | Hardcoded developer laptop SQLite path in sync dry-run / sync services | **Yes (P0)** for any sync-related agent tools |
| TD-002 | `admin/ai` third shell (no AppShell) | Yes for UX coherence (P1) |
| TD-003 | No rate limiting on expensive NR endpoints | Yes for Agent Runtime (P1) |
| TD-004 | No CI for backend/frontend/lottery | Yes for safe J-11 (P1) |
| TD-005 | No lottery Playwright E2E in CI | Yes for conversation UI (P1) |
| TD-006 | Unbounded NR universe load risk | Yes for tool abuse (P1) |

## 3. Reusable for J-11

| Asset | Location | Reuse mode |
|-------|----------|------------|
| LLMRouter / providers | `backend/app/llm/` | Direct |
| LotteryToolExecutor + TOOL_PERMISSIONS | `services/lottery_tools.py`, `lottery_ai_contracts.py` | Generalize |
| ConversationState / understanding / planner | `lottery/ai/` | Domain specialist + wrap |
| NumberExplorer + historical APIs | `numeric_relations/historical/` | Tools via adapters |
| active_scope FEATURED_SEVEN | `active_scope*.py` | Mandatory guard in Tool Guard |
| Prompt Studio / prompt versions DB | lottery AI models | Seed Prompt Registry |
| AppShell + module registry | frontend | Same identity `/lottery/copilot` |
| AgentRegistry skeleton | `agents/registry.py` | Fill (currently empty) |

## 4. Must fix before J-11 (minimum)

1. Remove/config-drive hardcoded SQLite paths (TD-001).
2. Integrate `admin/ai` into AppShell or isolate as admin-only subnav under single shell (TD-002).
3. Add rate limits + mandatory date bounds on heavy NR history tools (TD-003/006).
4. Add CI: pytest lottery subset + FE build (TD-004).
5. Add lottery E2E smoke (home, historial, compare, redirects) (TD-005).

## 5. Architecture J-11 should adopt

**J-11A Agent Runtime Foundation first**, then conversational UX (J-11B). See [`J11_AGENT_RUNTIME_DECISION.md`](J11_AGENT_RUNTIME_DECISION.md).

## 6. J-11 document status

**No dedicated J-11 specification exists** in the repo (only stop-gates in J-10H/J-10X reports). The sequence docs produced by this audit **replace** an absent plan; do not “maintain” a missing doc — create from [`J11_REVISED_IMPLEMENTATION_SEQUENCE.md`](J11_REVISED_IMPLEMENTATION_SEQUENCE.md).

## 7. Verdict (preview)

**GO PARA J-11A ANTES DE J-11** — with P0/P1 corrections listed above before Agent Runtime lands in Production paths.
