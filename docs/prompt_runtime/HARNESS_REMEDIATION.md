# Shadow harness remediation — classification, concurrency, timeouts

**Product frozen:** Prompt `7.0.0-rc3.4` / hash `41c64a0f…`  
**Scope:** harness + DEV auth telemetry only

## Result classes

| Class | Meaning |
|-------|---------|
| `product_pass` | Eligible Huawei+Studio complete; guards green; hash match |
| `product_fail` | Eligible path with factual/subject/hash/fallback failure |
| `timeout_error` | Client phase timeout |
| `auth_error` | HTTP 401/403 |
| `environment_error` | 5xx / network |
| `harness_error` | Unexpected runner exception |
| `not_eligible` | Completed but not Huawei dual-shadow |
| `skipped` | Reserved |

`hallucination=true` **only** when Studio response exists and guard detects invented content / extra subjects. HTTP/timeout/auth never set hallucination.

## Concurrency

**Chosen: concurrency=1** (sequential) against uvicorn `--workers 1`.

Rationale: each eligible turn already dual-calls Huawei (legacy + studio). Parallel harness workers previously caused client timeouts at 420s and starved the single ASGI worker.

## Timeouts

| Phase | Seconds |
|-------|---------|
| connect (implicit urllib) | 15 |
| session create/delete | 90 |
| message (incl. dual Huawei) | 600 |
| guard | in-process |

## Retries

- Max 1 retry for timeout / network / 502 / 503 / 504
- No retry for 400 / 401 / 403
- Same `correlation_id`; `environment_retry=true` if success after retry

## Auth 401 RCA (directed)

| Scenario | HTTP | Trace reason |
|----------|------|--------------|
| Missing Authorization | 401 | `token_missing` |
| Malformed Bearer | 401 | `token_malformed` |
| Valid JWT | 200 | — |
| 24× parallel valid JWT | 24×200 | S2062 **not** reproduced |

**Conclusion:** S2062 was an intermittent auth rejection under prior 4-worker storm; exact payload for that one request is lost. With concurrency=1 + correlation_id + auth_trace, future 401s are diagnosable. Not a Prompt Studio defect.

## Guard false-positive hardening (cert telemetry path)

During Shadow25, FactualGuard rejected valid Studio answers as hallucinations:

| Case | Symptom | Fix |
|------|---------|-----|
| E0010 | `extra_subjects:['7']` from “las 7 loterías” | Drop `la/las` as ball articles; scrub scope “las N loterías/habilitadas” |
| E0008 | `count_mismatch:5!=112` from “5 fechas de ejemplo” | Allow sample wording (`ejemplo`, `solo N fechas`) |
| E0038/40/42 | `count_mismatch:40!=N` from “umbral de 40 / supera … 40 veces” | Allow threshold echoes (`umbral`, `supera`, `claramente`, flexible gap) |

Prompt `7.0.0-rc3.4` / hash unchanged. Real invented counts and explicit extra balls still fail.
