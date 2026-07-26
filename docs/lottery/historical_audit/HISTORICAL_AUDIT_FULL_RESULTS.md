# Historical Audit — Full results index

## Artifacts

| File | Contents |
|------|----------|
| `evidence/audit_summary.json` | Full summary, metrics, baselines, gates |
| `evidence/audit_population_metrics.json` | Population aggregates |
| `evidence/audit_baselines.json` | Fair random baselines |
| `evidence/audit_sample_10_plus.json` | 11 case cards (JSON) |
| `evidence/audit_sample_cases.csv` | Sample CSV |

## Reproduction

```bash
cd backend
. .venv-prej11a/bin/activate
python -B scripts/run_historical_manual_logic_audit.py
```

DSN: DEV only (`jaios_lottery_dev` @ `127.0.0.1:5433`).  
`production_forbidden=true`. Idempotent given same DB snapshot + seed `20260726`.

## Population headline

- Dates: **4214**
- With fuerte: **2073 / 4214**
- Next-day hit (official fuertes): **536 / 2073** = 0.258562
- Lift vs random same-k: **0.9728**

## Sample headline (11)

| ID | Label | Date | Verdict |
|----|-------|------|---------|
| HIST-001 | C1 | 2026-06-21 | FALLO (geometry 29 OK; windows miss) |
| HIST-002 | C3 | 2026-06-21 | FALLO (multi {22,35}; windows miss) |
| HIST-003 | C4 | 2026-06-23 | ACIERTO_EXACTO 54 |
| HIST-004 | C5 | 2026-07-22 | ACIERTO_EXACTO 54 |
| HIST-005…010 | seeded full-day | various | mix hit/fail/none/t2 |
| HIST-011 | C2 | 2026-06-21 | DIRECT_T2_RECHAZADO |

Detailed cards: `HISTORICAL_AUDIT_10_CASES.md`.

## Motor / tables

`motor_modified=false`, `tables_modified=false`, FEATURED_SEVEN=7.
