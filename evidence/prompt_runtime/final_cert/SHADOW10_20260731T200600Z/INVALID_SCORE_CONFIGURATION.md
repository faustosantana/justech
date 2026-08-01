# INVALID_SCORE_CONFIGURATION — SHADOW10_20260731T200600Z

**Classification:** invalid score configuration (not a product failure).

## Verdict

The prior Shadow10 run is **not** a product regression. Runtime executed **Lottery Analyst Prompt 7.0.0-rc3.5** correctly; the harness scorer expected the obsolete rc3.4 hash.

## Facts

| Item | Value |
|------|--------|
| Run control dir | `evidence/prompt_runtime/final_cert/SHADOW10_20260731T200600Z` |
| Suite out | `evidence/prompt_runtime/final_cert/SHADOW10_20260731T200601Z` |
| Container checkpoint | `/tmp/shadow_eligible_out/CHECKPOINT.json` (at run time) |
| done | 10/10 |
| Observed runtime prompt hash (10/10) | `f9cb83c80271de345fb3b50a08cc9a76b31c66666d2dcb55517bbb7059d21149` (rc3.5) |
| Harness `EXPECTED_HASH` default used | `41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9` (rc3.4) |
| Evidence Package match | 10/10 |
| hallucinations | 0 |
| unauthorized_breakdown | 0 |
| extra/missing/altered subjects | 0 |
| timeout / auth / environment errors | 0 |
| Scorer `product_pass` / `product_fail` | 0 / 10 |

## Cause

All ten `product_fail` labels came **exclusively** from hash mismatch against the harness default rc3.4 `EXPECTED_HASH`. There were no factual failures and no operational (timeout/auth/environment) failures.

## Artefacts

Original run artefacts are **preserved unmodified**. This report only reclassifies the score outcome.
