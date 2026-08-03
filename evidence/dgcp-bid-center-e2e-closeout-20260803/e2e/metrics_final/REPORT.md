# Metrics + similar search closeout

## Prepare metrics
- preparation_pct: 52.9 (coverage of 9/17)
- copied_documents: 9
- API = manifest = ZIP = dashboard
- Idempotent prepare: PASS

## Similar search
- Local-first: 5 matches in ~0.7s (local_latency_ms≈44)
- remote_status=skipped_local_sufficient
- On remote timeout with refresh: keeps 5 local matches, degraded=true, HTTP 200
- Indexed awards: 224 total / 156 Procuraduría (code 6)
