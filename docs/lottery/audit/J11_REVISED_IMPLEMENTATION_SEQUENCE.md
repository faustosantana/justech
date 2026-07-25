# J-11 — Revised Implementation Sequence

## Phase 0 — Preflight corrections (before runtime code)

1. TD-001 config-drive SQLite paths  
2. TD-003 rate limits + TD-006 date bounds on NR history  
3. TD-002 AppShell integration for admin/ai (or explicit admin-only exception documented)  
4. TD-004/005 CI + lottery E2E smoke  
5. TD-010 secret handling plan  

**Gate:** GO to J-11A only when P0 done and P1 security items accepted.

## J-11A — Agent Runtime Foundation

1. Conversation API (lottery-scoped OK initially)  
2. Agent Runtime loop + tracing  
3. Tool Registry schemas from [`J11_TOOL_MAPPING.md`](J11_TOOL_MAPPING.md)  
4. Tool Executor deny-list (no sync write)  
5. Evidence Builder adapter  
6. Response Validator (deterministic first)  
7. Composed Prompt Registry  
8. Provider Gateway cost/usage hooks (reuse LLMRouter)  
9. Golden methodology tests via tools (35/50/86)

**No new multi-agent mesh.**

## J-11B — Copiloto UX in Control Center

1. `/lottery/copilot` under AppShell  
2. Redirect `/lottery/chat` → copiloto  
3. Contextual cards (evidence, charts)  
4. Modes: rápido / analítico / auditoría  
5. Mobile single-nav compliance  

## J-11C — Hardening & ops

1. Benchmark suite for agent answers  
2. Prompt injection tests  
3. Cost limits / kill switch  
4. Admin configuration UI (provider/model) inside Administración  

## Explicit non-goals early

- Separate “Intelligence” product shell  
- Free-form SQL tools  
- Writing sync from chat  
- Changing FEATURED_SEVEN / formulas  
