# J-11A — Agent Runtime Decision

## Recommendation

**Proceed with J-11A — Agent Runtime Foundation before full J-11 conversational productization.**

### Why not GO DIRECTO PARA J-11

1. No generic runtime (empty `AgentRegistry`).
2. Lottery AI stack is powerful but **hard-wired**; bolting more UX without a runtime freezes coupling.
3. Security gaps (rate limit, secrets, sync path) are unsafe for autonomous tool loops.
4. No Evidence Builder / Response Validator — LLM could invent numbers without deterministic checks.
5. No CI/E2E safety net for conversation UX.

### Recommended runtime flow

```text
User → Conversation API → Agent Runtime → Planner → Task Graph
  → Intent Router → Tool Planner → Tool Registry → Tool Executor
  → Evidence Builder → Provider Gateway → Response Validator → Renderer → User
```

### Multi-agent?

**Not initially.** One Analyst Agent with tools covering historial/compare/audit/explain. Add Historian/Comparator only if single-agent prompts become unmaintainable.

### Prompt architecture (chosen)

**Composed prompts (maintainable):**

`Base Policy + Role + Task + Tool Instructions + Methodology Guard + Output Schema`

Reject monolithic mega-prompts per intent as primary design (Prompt Studio versions can remain as compiled snapshots).

### Evidence Builder placement (chosen)

**Independent adapter service** called by Tool Executor outputs → normalized Evidence objects for Validator + Composer.  
Not inside pure motor (keeps formulas pure); not only inside LLM prompts.

### Product name (chosen)

**Copiloto de Lottery IA** inside Lottery IA Control Center (`/lottery/copilot`, with `/lottery/chat` redirect).  
Avoid a separate app name (“JAIOS Intelligence”) that reintroduces dual identity.
