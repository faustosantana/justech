# Historical Audit — Statistics

Source: `evidence/audit_summary.json` / `evidence/audit_population_metrics.json`  
Audit id: see evidence (latest run). Seed: `20260726`.

## Scope

| Metric | Value |
|--------|------:|
| Featured lotteries | 7 |
| All draws (DEV) | 91,941 |
| Featured draws loaded | 27,230 |
| Dates analyzed (≥2 first numbers) | 4,214 |
| Population cases | 4,214 |
| Official strengthened instances | 3,401 |
| T1 companion slots scanned | 27,668 |
| Avg candidates / case | 0.8071 |

## Cases with / without fuerte

| Class | n | denom |
|-------|--:|------:|
| With ≥1 fuerte | 2,073 | 4,214 |
| Multi fuerte | 875 | 4,214 |
| Sin fuerte | 2,141 | 4,214 |
| DIRECT_T2_RECHAZADO | 2,140 | 4,214 |

Coverage (cases with fuerte): \(2073/4214 = 0.4922\).

## Window precision (denom = cases with fuerte = 2073)

| Window | hits | denom | precision | Wilson 95% CI |
|--------|-----:|------:|----------:|---------------|
| next_chronological_draw | 105 | 2073 | 0.050651 | [0.042015, 0.06095] |
| same_day_other_draws | 0 | 2073 | 0.0 | structural empty for full-day unit |
| next_calendar_day | 536 | 2073 | 0.258562 | [0.240173, 0.277845] |
| next_7_featured_draws | 557 | 2073 | 0.268693 | [0.250051, 0.28819] |

## Population verdict counts

| Verdict | n |
|---------|--:|
| DIRECT_T2_RECHAZADO | 2140 |
| FALLO | 1516 |
| ACIERTO_NO_UNICO | 352 |
| ACIERTO_EXACTO | 205 |
| SIN_CONFIRMACION | 1 |

## Sample (11 cases)

Quotas: hits=5, fails=3, multi=3, sin_fuerte=2, direct_t2=2 (C2 forced), total=11.

Includes anchors C1, C3, C4, C5 + C2 rejected + 6 seeded population cases.
