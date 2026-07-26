# Validation Lab Spec — Motor Validation Lab

## Purpose

Explain-only audit surface that reconstructs NR geometry for multi-observation same-day inputs and compares to an optional manual “Fuerte”.

**Must never** modify:

- Tabla 1 / Tabla 2 generators
- `analyze_observed_number`
- scoring / confirmation formulas
- Production data

## Route

- UI: `/lottery/admin/control-center/motor/validation-lab`
- API: `POST /api/v1/lottery/admin/numeric-relations/validation-lab`
- Permissions: same AI/admin NR permissions as other numeric-relations admin routes

## Request

```json
{
  "date": "2026-06-23",
  "manual_fuerte": 54,
  "observations": [
    { "lottery_name": "Loteria Nacional", "number": 35 },
    { "lottery_name": "Quiniela Loteka", "number": 14 }
  ]
}
```

## Response (fields)

| Field | Meaning |
|-------|---------|
| `tables_per_number` | Tabla1 companions, Tabla2 neighbors/group per number |
| `crosses_and_intersections` | Hypotheses A/F/B/E/D with `produced` sets |
| `mathematical_ranking` | Evidence-weighted ranking (not `/analyze` score) |
| `motor_shaped_result` | Output of hypothesis F |
| `manual_fuerte` | Oracle |
| `coincidence` | `SI` / `SI_CON_OTROS_CANDIDATOS` / `PARCIAL_RELACION_ALTERNATIVA` / `NO` |
| `explanation` | Structured detail when F hits the manual fuerte |
| `methodology_version` | `nr-historical-relations-j1.0.0` |
| `modifies_motor` | always `false` |

## UI requirements

- Inputs: date, lottery labels, observed numbers, manual fuerte
- Presets for the five manual cases
- Shows: tables, crosses, ranking, motor result, manual result, coincidence SI/NO
- Single AppShell (Control Center layout)

## Implementation map

| Piece | Path |
|-------|------|
| Core | `backend/app/lottery/numeric_relations/validation_lab.py` |
| API | `lottery_numeric_relations.py` → `/validation-lab` |
| Tests | `backend/tests/test_nr_validation_lab.py` |
| Batch runner | `backend/scripts/nr_manual_cases_validation.py` |
| FE page | `frontend/.../motor/validation-lab/page.tsx` |
| Nav | `registry.ts` → Validation Lab |

## Non-goals

- Chat / Agent Runtime
- Changing `/analyze` contracts
- Encoding manual cases into production logic
