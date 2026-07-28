# Lottery Analyst — CERTIFIED

| Field | Value |
|-------|-------|
| **Status** | **CERTIFIED** |
| Audit run | `cert200-20260728T151731Z-40ca7b78` |
| Finished | 2026-07-28T16:11:24Z |
| PASS / FAIL | **200 / 0** |
| Seed | `20260727` (unchanged) |
| Bank SHA-256 | `6d056978809140eee4af23299cbd0c78a8bae9537fbbbcd62ad50bd18c6d7931` |
| Image | `jaios-app-backend:lottery-ia-ux-v2.4.5.4-de` (also tagged `lottery-ia-ux-v2.4.5.4`, `lottery-analyst-certified-2026.1`) |
| Exactitud factual mean | 5.0 |
| Contradictions / jargon / HTTP 500 / invented / wrong subject | 0 |
| Repeatability | 20 / 20 equivalent |
| Concurrency unique IDs | true |

## Prior baseline

Blocked run: 175 PASS / 25 FAIL (`cert200-20260728T104943Z-…`).

## Closure path

1. Root-cause groups A–E (no Grupo F).
2. Residual D/E completion (bare compare clarify lock; sticky same_day/compare cleared on last_n; force local template on «todas las posiciones/loterías»; unscoped lottery clear).
3. Residual4 (`LONG_30`, `G01`, `G20`): 44 PASS / 0 FAIL — including `LONG_30.T29`, `G01.T06`, `G20.T02`, `G20.T06`.
4. Full 200: **CERTIFIED**.

No Prompt Maestro / Hermes / mathematical motor changes. Bank and seed unchanged for this certified run.
