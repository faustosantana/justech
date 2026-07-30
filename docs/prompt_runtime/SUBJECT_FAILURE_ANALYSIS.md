# Subject Failure Analysis

## Exact failure (DEV shadow rc2)

**User:** ¿Han coincidido el 50 y el 90 el mismo día?  
**Evidence subjects:** `50`, `90` · **counts.total:** 134  

**Studio RAW (excerpt):** claimed 134 coincidences, then invented secondary breakdowns including **83**, **51**, **60**.  

**Guard:** `extra_subjects:['51', '60', '83']`

## Classification

| Hypothesis | Verdict |
|------------|---------|
| A. Studio RAW | **YES** — numbers appear in Studio text as related stats |
| B. Guard parser only | **PARTIAL** — old guard used global 1–2 digit scrape + alien 32–99 heuristic |
| C. Formatter | **NO** — failure happened on RAW before user-facing template |
| D. Valid in Evidence Package | **NO** — not in package subjects |
| E. Conversation memory only | **NO** — single-turn proof |

## Cause

**Combination:** Studio verbosity invents related numbers (**A**) and the pre-Phase-3 guard treated many digits as subject candidates (**B**). Primary fault is Studio content/behavior under a 50k Maestro prompt that encourages enrichment.

## Fix direction

1. Contextual `subject_guard` (dates/counts/positions/tables/limits masked).  
2. `AllowedSubjectSet` + optional `response_contract.allowed_subjects`.  
3. Lean **rc3** with explicit subject contract and verbosity caps.
