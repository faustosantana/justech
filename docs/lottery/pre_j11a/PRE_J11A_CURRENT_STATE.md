# Pre-J11A — Current State

| Field | Value |
|-------|--------|
| Branch | `feature/nr-pre-j11a-hardening` |
| Base (J-10X approved) | `564a8c0` |
| Audit branch (read-only) | `audit/nr-post-j10x-pre-j11` @ `0435642` |
| Worktree | `/Users/faustosantana/Projects/justech-pre-j11a-hardening` |
| Production | **intacta** — `j10x-20260724` — `production_forbidden=true` |
| Methodology | `nr-historical-relations-j1.0.0` |
| Scope | P0/P1 blockers only — **no** J-11 conversational / Agent Runtime |

## Source of truth (audit — not reinterpreted)

- `docs/lottery/audit/PHASE_POST_J10X_PRE_J11_AUDIT_FINAL_REPORT.md`
- `docs/lottery/audit/POST_J10X_TECHNICAL_DEBT_REGISTER.md`
- `docs/lottery/audit/POST_J10X_SECURITY_AUDIT.md`
- `docs/lottery/audit/POST_J10X_BACKEND_API_AUDIT.md`
- `docs/lottery/audit/POST_J10X_TEST_COVERAGE_AUDIT.md`
- `docs/lottery/audit/J11_AGENT_RUNTIME_DECISION.md`
- `docs/lottery/audit/J11_REVISED_IMPLEMENTATION_SEQUENCE.md`

## Confirmed blockers (exact files)

| ID | Issue | Files |
|----|-------|-------|
| TD-001 P0 | Hardcoded SQLite path | `backend/app/api/v1/lottery.py` (~1272), `backend/app/services/lottery_sync_service.py` (~326), `backend/app/services/lottery_sync_writer.py` (~145); tests `test_lottery_phase6_staging.py`, `test_lottery_phase7_sync_write.py`, `test_lottery_phase8_scheduler.py` |
| TD-002 P1 | Third shell `admin/ai` | `frontend/src/app/(platform)/lottery/admin/ai/layout.tsx` |
| TD-003/006 P1 | No rate limits / unbounded NR loads | `backend/app/api/v1/lottery_nr_historical.py`, related NR routers |
| TD-004/005 P1 | No lottery CI / E2E | `.github/workflows` desktop-only |
| TD-010 P1 | LLM secrets plaintext patterns | config / AI admin models; missing `credential_vault` primitives in tip |

## Out of scope (explicit)

Chat conversacional, Conversation API, Planner, Tool Planner, memoria conversacional, Prompt Registry, Provider Gateway, agentes especializados, UI de copiloto, benchmark conversacional, gestión gráfica completa de proveedores, despliegue a Producción.

## DEV isolation

| Service | Value |
|---------|--------|
| DB | `jaios_lottery_dev` @ `127.0.0.1:5433` |
| API (optional) | `127.0.0.1:8001` |
| FE (optional) | local Next.js |
| production_forbidden | **true** |

## Implementation sequence

1. Audit confirmation + plan (this doc)
2. Remove hardcoded SQLite paths
3. NR API bounds + rate limits
4. Integrate admin/ai into AppShell
5. Backend / frontend / lottery E2E CI
6. Secure LLM secret foundation
7. Regression + final report

## Acceptance pointer

See phase brief §12. Verdict only after all blocks + tests.
