# POST J-10X — Technical Debt Register

| ID | Title | Sev | Area | Evidence | Impact | Effort | Fix before J-11? | Blocks J-11? |
|----|-------|-----|------|----------|--------|--------|------------------|--------------|
| TD-001 | Hardcoded laptop SQLite path in sync | P0 | Backend/Sync | `lottery.py:1272`, `lottery_sync_service.py:326`, `lottery_sync_writer.py:145` | Wrong defaults; Agent system tools unsafe | S | **Yes** | **Yes** |
| TD-002 | `admin/ai` third shell | P1 | Frontend | `admin/ai/layout.tsx` | Dual product UX; copiloto identity risk | M | **Yes** | Soft-yes |
| TD-003 | No rate limits on NR/analyze | P1 | Security/API | routers lack limiter | Abuse / cost / DoS via tools | M | **Yes** | **Yes** |
| TD-004 | No CI for backend/FE lottery | P1 | CI | `.github/workflows` desktop-only | Regressions undetected | M | **Yes** | Soft-yes |
| TD-005 | No lottery Playwright E2E | P1 | Tests | e2e trees | UX regressions (J-10X class) | M | **Yes** | Soft-yes |
| TD-006 | Unbounded NR universe load | P1 | NR/API | historical prepare optional dates | Latency/memory under Agent | M | **Yes** | **Yes** |
| TD-007 | historial-numero god page + form fork | P2 | Frontend | `historial-numero/page.tsx` vs `historical-form.tsx` | Maintainability | M | During J-11 | No |
| TD-008 | Raw dict AI admin bodies | P2 | API | AI admin routers | Invalid configs | M | During J-11A | No |
| TD-009 | Umbrella `lottery.admin` | P2 | Authz | permissions | Over-privilege | M | Before prod Agent | Soft-yes |
| TD-010 | LLM keys plaintext patterns | P1 | Security | config/models | Secret leak | L | **Yes** | Soft-yes |
| TD-011 | Empty `AgentRegistry` vs parallel lottery AI | P2 | Architecture | `agents/registry.py` | Duplicate stacks | L | J-11A | No |
| TD-012 | Legacy redirect page files | P3 | Frontend | search/compare/statistics pages | Noise | S | Later | No |
| TD-013 | Print branding legacy | P3 | Frontend | `print/page.tsx` | Identity inconsistency | S | Later | No |
| TD-014 | N×M analyze queries | P2 | NR | analyze path | Perf | M | During J-11A | No |
| TD-015 | Missing generic Conversation API | P2 | Architecture | lottery chat only | Blocks multi-module agent | L | J-11A | No (lottery-first OK) |

## P0/P1 checklist before Agent Runtime

- [ ] TD-001
- [ ] TD-002
- [ ] TD-003
- [ ] TD-004
- [ ] TD-005
- [ ] TD-006
- [ ] TD-010
