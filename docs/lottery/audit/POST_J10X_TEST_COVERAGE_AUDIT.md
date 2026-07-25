# POST J-10X — Test Coverage Audit

## Inventory

| Class | Count / location | Notes |
|-------|------------------|-------|
| Backend lottery unit/integration | **34** `backend/tests/test_lottery*.py` | Strong NR + AI admin |
| Frontend Playwright lottery | **0** specs under `frontend/e2e` / `e2e` | Gap |
| Visual evidence scripts | `docs/.../phase_j10x_visual/capture_screenshots.py` | Not CI |
| CI workflows | Desktop only | No pytest/FE CI |

## Coverage vs critical behaviors

| Behavior | Covered? | Where |
|----------|----------|-------|
| Tabla 1 formula | Yes | `test_lottery_numeric_relations_table1.py` |
| Tabla 2 formula | Yes | `test_lottery_numeric_relations_table2.py` |
| Candidate vs confirmer roles | Yes | analysis + historical tests |
| Strengthening candidate only | Yes | analysis/history suites |
| FEATURED_SEVEN / active scope | Yes | `test_lottery_nr_j10l_active_scope.py`, j10h visual scope |
| Archived excluded | Partial | active_scope + j10h tests; need FE E2E |
| Historial UX | No E2E | only manual/visual |
| Comparador UX | No E2E | |
| Redirects | No automated FE | next.config + redirect pages |
| Mobile single nav | Visual only | J-10X screenshots |
| Permissions matrix | Yes | `test_lottery_2_0_admin.py`, AI admin tests |
| Methodology version stamp | Indirect | historical services tests |

## Mandatory tests before J-11 / J-11A

1. Playwright smoke: `/lottery` identity, sidebar single, historial advanced collapsed, compare Spanish labels, redirects.
2. CI job: `pytest backend/tests/test_lottery_numeric_relations*.py backend/tests/test_lottery_nr_*.py backend/tests/test_lottery_j10h*.py`.
3. Contract tests: every tool planned for J-11 maps to an existing endpoint response schema.
4. Negative: tool call with non-featured lottery_id → reject.
5. Security: conversation cannot invoke sync write tools without admin + gate.
