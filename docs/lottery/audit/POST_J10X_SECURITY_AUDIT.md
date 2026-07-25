# POST J-10X — Security Audit

**Scope:** read-only code review. Production not probed offensively.

## Current controls

| Control | Status | Evidence |
|---------|--------|----------|
| JWT auth | Present | `getAccessToken` FE; FastAPI Depends |
| Role permissions | Present | `role_has_permission`, lottery_client path allowlists |
| NR admin guards | Present | `require_ai_admin` on NR routers |
| Tool RBAC | Present | `TOOL_PERMISSIONS` in lottery_ai_contracts |
| Sync write gates | Present | backup gate / flags in sync services |
| CORS | Config-driven | review per env before Agent Runtime |
| Rate limit | **Missing** on lottery/NR | no limiter middleware found for these routes |
| Secret storage for LLM keys | **Weak** | plain strings in config/DB patterns |
| Hardcoded FS paths | **Critical** | laptop SQLite defaults in sync dry-run |

## Gaps for J-11 (document only — do not implement)

| Requirement | Gap |
|-------------|-----|
| Encrypted API key storage | No vault/SecretStr path for lottery LLM keys |
| Key masking in UI/logs | Partial admin display helpers; not systematic |
| Tool Guard | Exists as executor permissions; no injection/SQL/shell deny layer |
| Policy Engine | Not present as first-class component |
| Prompt Injection Guard | Not present |
| Forbid free SQL / shell from conversation | Tools are typed (good) but Agent Runtime must keep whitelist-only |
| Forbid productive writes via chat | Sync tools must stay out of conversation tool registry or double-gated |
| Conversation isolation | Lottery sessions tenant-scoped; needs explicit cross-user tests |
| Cost / rate limits per user | Missing |
| Credential rotation | Ops process only |

## Findings

| ID | Sev | Title |
|----|-----|-------|
| AUD-SEC-001 | P0 | Hardcoded absolute SQLite path in production code paths |
| AUD-SEC-002 | P1 | No rate limiting on NR history / analyze |
| AUD-SEC-003 | P1 | LLM secrets not treated as SecretStr / encrypted-at-rest |
| AUD-SEC-004 | P2 | Broad `lottery.admin` umbrella |
| AUD-SEC-005 | P2 | AI admin endpoints accepting untyped `dict` bodies |
| AUD-SEC-006 | P2 | Observability leakage risk if permission too broad |

## Recommendation

Block Agent Runtime Production exposure until AUD-SEC-001..003 addressed in a hardening mini-phase (can be J-11A.0).
