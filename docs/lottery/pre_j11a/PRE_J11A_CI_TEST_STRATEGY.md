# Pre-J11A — CI / Test Strategy (TD-004 / TD-005)

## Workflow

`docs/lottery/pre_j11a/ci/lottery-pre-j11a.yml` (install to `.github/workflows/` with a token that has `workflow` scope)

### A. Backend (obligatorio)

- Install reproducible (`pip install -e ".[dev]"`)
- pytest Pre-J11A: sqlite config, API guards, LLM secrets
- Scan: no laptop SQLite paths in runtime sync callers
- Methodology marker `nr-historical-relations-j1.0.0`
- Heurística: no fórmulas NR en frontend

### B. Frontend (obligatorio)

- `npm ci` / install
- lint
- `tsc --noEmit`
- `next build`

### C. E2E Lottery

- Spec: `e2e/tests/lottery-pre-j11a.spec.ts`
- Job CI activable con `vars.LOTTERY_E2E_ENABLED=true` + secrets de URL DEV/test
- **Nunca** apunta a Producción
- Local: stack DEV + `npx playwright test tests/lottery-pre-j11a.spec.ts` desde `e2e/`

### D. Seguridad / metodología

- Heurística anti-secretos en código
- FEATURED_SEVEN / is_featured presente

## Artefactos

- pytest JUnit XML
- Playwright HTML/report on failure

## Datos

- Unitarios: tmp / fixtures sintéticos
- Sin credenciales de Producción
- Secretos LLM de prueba: falsos únicamente
