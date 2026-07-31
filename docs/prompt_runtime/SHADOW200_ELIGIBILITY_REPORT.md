# Shadow200 Eligibility Report

**Dataset:** `evidence/prompt_runtime/final_cert/SHADOW200_ELIGIBLE_DATASET.json`  
**Frozen prompt:** 7.0.0-rc3.4 / `41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9`  
**Cases:** 200  
**Static preflight invoke:** 200/200  
**Preflight fails:** 0 

## Category distribution

| Category | N |
|----------|---|
| compare_numbers | 20 |
| complex | 10 |
| followup_interp | 15 |
| freq_analysis | 25 |
| insufficient_evidence | 15 |
| interp_coincidence | 30 |
| multi_lottery | 15 |
| position_interp | 20 |
| recent_interp | 20 |
| tabla1_semantics | 10 |
| tabla2_semantics | 10 |
| topic_switch_reasoning | 10 |

## Eligibility definition (runtime)

A case counts toward Shadow200 only when:

1. Route uses Huawei reasoning (not local_template / workspace / social).
2. Legacy + Studio shadow both call the provider.
3. Same Evidence Package.
4. Complete responses + guards.
5. Studio prompt hash matches frozen hash.
6. No unexpected fallback.

Workspace / local_template / deterministic routes are tracked in **Routing200**, not in Shadow200 denominator.

## Concurrency policy

`concurrency=1` (sequential) against DEV uvicorn `--workers 1`, because dual Huawei shadow calls already serialize provider load per turn.

## Notes

- Tabla1/Tabla2 categories use **semantic** wording without export/pagination commands to avoid Investigation Workspace capture.
- Follow-ups keep a Huawei-eligible setup turn then an interpretative user turn.
