# ENTREGA — Hotfix schema DGCP DEV

## Verdict: PARTIAL

### Schema opportunity (objetivo primario)
- PASS: `needs_review` + `jaios_intelligence` presentes
- PASS: GET `/dgcp/opportunities` 200
- PASS: POST `/dgcp/sync` 202 completed
- PASS: GET `/dgcp/bid-copilot/executive-dashboard` 200
- PASS: API health 200
- Commit: `9035c6a`

### E2E Bid Center (flujo completo)
- FAIL / bloqueado por drift adicional de schema (no corregido en silencio):
  1. `jaios.dgcp_historical_awards` missing → historical-similar / analysis-status 500
  2. `jaios.licitador_company_profiles` missing → document-validation / prepare / bid-copilot 500
  3. `dgcp_historical_index_jobs`, `dgcp_process_historical_similar_results` también ausentes
  4. `build_content_disposition()` TypeError en real-expediente/download
  5. `mostrar_interes` 409 esperado (ya estaba en Interesadas)

### RCA drift 049→063
`049_dgcp_funnel_needs_review.py` es un stub `pass` (bridge porque 039–048 no estaban en disco). Alembic avanzó a reconciles/lottery heads sin aplicar columnas reales de funnel/intelligence. DEV runtime llegó a `066_reconcile_dgcp_opp` con columnas opportunity; faltan tablas Bid Center posteriores.

### Evidencias
`evidence/dgcp-schema-hotfix-20260803/`
