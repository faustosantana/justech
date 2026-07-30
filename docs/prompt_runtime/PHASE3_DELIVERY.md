# Phase 3 Delivery — Subjects, Verbosity, Guard (pre-Shadow200)

**Branch:** `feature/lottery-prompt-runtime-integration-1.0`  
**Base commit (start of phase):** `8894480`  
**Estado:** **PASS** (Shadow200 authorized on DEV only)

## Exact cause of `extra_subjects` (rc2)

| Layer | Verdict |
|-------|---------|
| A. Studio RAW | **YES** — invented related balls (51/60/83) and later first-position subtotals |
| B. Guard parser | **PARTIAL** — pre-Phase-3 global digit scrape false-positives |
| C. Formatter | NO |
| D. Valid in Evidence | NO |
| E. Conversation memory | NO |

Additional failure mode fixed in Phase 3: LLM payload exposed `dates[:40]` → Studio said “40 fechas…” (`count_mismatch`). Mitigated by trimming LLM date sample to 5 + `response_contract` sample notes.

## Canonical allowed subjects

`AllowedSubjectSet.from_evidence_package` — subjects / rows / comparison / optional `response_contract.allowed_subjects`; related only if authorized. Normalizes 7/07.

## Guard

Contextual `subject_guard` + date/count/lottery checks. Unit tests: `backend/tests/lottery/prompt_runtime/test_subject_guard_rc3.py`.

## Prompt rc3.4

| | |
|--|--|
| Version | `7.0.0-rc3.4` |
| ID | `c41ec4c5-1bd5-430f-85c5-e9546e176709` |
| Hash | `41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9` |
| Chars / tokens | 4055 / ~1014 |
| vs rc2 | ~92% fewer tokens (50477 → 4055) |

## Suites

| Suite | Result |
|-------|--------|
| Subject50 | **50/50** · 0 extra/missing/altered subjects |
| Prompt50 | **PASS** · studio_guard 5/5 on shadowed Huawei turns · 0 extras · routing mix OK |

## Verbosity / latency (Subject50 rc3.4)

| | Legacy visible | Studio shadow |
|--|----------------|---------------|
| avg words | ~163 | ~101 |
| avg latency | ~31.5 s wall (dual-call path) | ~8.1 s studio-only |

## DEV

- Port **8022**, image `prompt-runtime-1.0-shadow-phase3`
- `MODE=shadow`, studio enabled, shadow LLM true, forensics **off**
- Rollback proved: **rc3.3 ↔ rc3.4** (rc2 UUID not present on this local DEV DB)
- **PROD untouched**

## Decision

**Autorizado para Shadow200** (solo DEV, mode=shadow, legacy visible).  
No activar Studio visible. No PROD.
