# J-11 Gap Analysis

## Existing J-11 document

**None.** Only stop-gates in J-10H/J-10X reports. This audit defines the gap baseline.

## Component matrix

| Component | Exists? | Reuse | Gap |
|-----------|---------|-------|-----|
| Conversation API (generic) | Partial (lottery chat) | Wrap/extend | Domain-agnostic API |
| Conversation Engine | Yes (lottery/ai) | Domain specialist | Planner streaming/cancel |
| Intent Router | Partial (understanding) | Extend | Explicit intent taxonomy for tools |
| Tool Registry | Partial (static enum) | Generalize | Dynamic registry + schemas |
| Tool Executor | Yes | Generalize | Deny-lists, budgets |
| Memory | Yes (conversation context) | Extend | Isolation tests |
| Prompt Registry | Partial (DB versions + studio) | Compose | Base+Role+Task composition |
| Provider Gateway | Yes (`LLMRouter`) | Direct | Cost accounting |
| Response Composer | Partial (narrative) | Extend | Evidence-first composer |
| Response Validator | Minimal | **New** | Deterministic validators |
| Evidence Builder | Scattered in explorer | **New adapter** | Normalize tool outputs |
| Security Tool/Policy Guard | Partial RBAC | **New** | Injection + write bans |
| Benchmark / metrics | AI admin benchmarks | Extend | Agent golden set |
| UI conversational | `/lottery/chat` + home CTA | Unify as Copiloto | Same AppShell |
| Agent Runtime | Skeleton empty | Build in J-11A | Run loop, graph, tracing |

## Analyst agents recommendation

Specialized agents (Historian/Comparator/Auditor/Explainer) add value **only after** a single runtime + tool layer works. Start with **one Analyst agent** + tools; split later if prompts/tools diverge.

## Decision

See [`J11_AGENT_RUNTIME_DECISION.md`](J11_AGENT_RUNTIME_DECISION.md).
