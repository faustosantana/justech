# Response dimensions contract (additive on `response_contract`)

**Schema change:** none required — extends existing `EvidencePackage.response_contract: dict`.

## Fields

| Field | Meaning |
|-------|---------|
| `allowed_dimensions` | Subset of `{total, lottery, position, date, subject, frequency, percentage, ranking}` derived from keys present in `counts` |
| `allowed_counts` | Integer values present in `counts` (canonical totals / authorized subtotals) |
| `forbidden_inferences` | e.g. `position_breakdown`, `lottery_breakdown`, `date_breakdown`, `subject_subtotals`, `ranking_without_totals` |
| `canonical_count` | Existing — `counts.total` |
| `dimension_note` | Human/LLM reminder |

## Rules

1. A numeric claim is allowed only if its dimension is in `allowed_dimensions` **and** the number is in `allowed_counts` (or an explicit authorized row).
2. When only `total` is present → `requested_operation` prefers `compare_same_day_total` / `report_canonical_total`.
3. `to_llm_payload()` **sanitizes** `factual_answer` to strip template position breakdowns when `position` is not an allowed dimension (fixes E0068 package contradiction).

## Code

- `backend/app/lottery/ai/analyst_reasoning/response_dimensions.py`
- Wired in `EvidencePackageBuilder.build` + `EvidencePackage.to_llm_payload`
- Guard: `FactualGuard` → `unauthorized_breakdown=true` via `text_has_unauthorized_breakdown`
