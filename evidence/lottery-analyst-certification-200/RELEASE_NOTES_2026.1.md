# Release Notes — Lottery Analyst 2026.1

**Status:** CERTIFIED (frozen baseline)  
**Version:** `lottery-ia-ux-v2.4.5.4-certified`  
**Date (UTC):** 2026-07-28  

## Summary

Official conversational certification of the Lottery Analyst chat on production. The release closes the blocked baseline (175 PASS / 25 FAIL) and freezes **200 PASS / 0 FAIL** as `LOTTERY_ANALYST_CERTIFIED_2026_1`.

## Identity

| Field | Value |
|-------|-------|
| Product release | `2026.1` |
| Git tag | `lottery-ia-ux-v2.4.5.4-certified` |
| Commit | `9b440c3b51b9684bf48e6f31bbc23226b2994b6e` |
| Docker image | `jaios-app-backend:lottery-ia-ux-v2.4.5.4-de` |
| Image ID | `sha256:a6204913747cc2472f2dfec4cd125b95f73fe1fd55439d6d1255c9342780af24` |
| Aliases | `lottery-ia-ux-v2.4.5.4`, `lottery-analyst-certified-2026.1` |
| Question bank seed | `20260727` |
| Question bank SHA-256 | `6d056978809140eee4af23299cbd0c78a8bae9537fbbbcd62ad50bd18c6d7931` |
| Audit run | `cert200-20260728T151731Z-40ca7b78` |

## What changed (relative to blocked freeze `v2.4.5.3`)

Root-cause conversational fixes only (groups A–E). No Prompt Maestro, Hermes, or mathematical motor changes.

| Group | Cause | Fix area |
|-------|-------|----------|
| A | Limit digit ↔ subject swap | `turn_policy` subject/limit hygiene |
| B | Missing Spanish number words | Spanish ball words |
| C | «Última del» / «cuándo apareció» routing | `intent_resolver` / `question_classifier` |
| D | Bare resume / compare / filter refine without locked clarify or subject continuity | Understanding bare compare lock; last_n continuity; local templates on filter-only refinements |
| E | Sticky `lottery_explicit` (Nacional) on unscoped last_* | Clear sticky lottery on subject switch / unscoped last_* |

## Certification gate

| Metric | Result |
|--------|--------|
| PASS / FAIL | **200 / 0** |
| Exactitud factual (mean) | **5.0** |
| Contradictions | 0 |
| Internal jargon | 0 |
| HTTP 500 | 0 |
| Invented data | 0 |
| Wrong subject | 0 |
| Repeatability | 20 / 20 equivalent |
| Concurrency unique IDs | true |
| Level | **CERTIFIED** |

Prior blocked run under freeze `v2.4.5.3`: 175 PASS / 25 FAIL.

## Explicit non-goals (honored)

- No question-bank mutations for the certified run lock
- No seed change (`20260727`)
- No evaluator criteria change
- No Prompt Maestro / Hermes / mathematical motor edits for certification closeout

## Artifacts

- `RELEASE_PACKAGE/VERSION_MANIFEST.json`
- `RELEASE_PACKAGE/CERTIFICATION_REPORT_FINAL.md`
- `evidence/lottery-analyst-certification-200/audit-certified-20260728/`
- Restore: `RELEASE_PACKAGE/RESTORE.md` + `RELEASE_PACKAGE/verify_restore.sh`

## Restore

```bash
git checkout lottery-ia-ux-v2.4.5.4-certified
bash RELEASE_PACKAGE/verify_restore.sh
# runtime: redeploy jaios-app-backend:lottery-ia-ux-v2.4.5.4-de
```

This tag is frozen. Later baselines must use a new tag.
