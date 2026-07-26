# PHASE PRE-J11A — Four-Year Seven-Lottery Audit — Informe final

**Stop:** auditoría, pruebas, exportaciones y veredictos listos. **No se inicia J-11A.** Esperar autorización.

## Isolation

| | |
|--|--|
| Branch | `feature/nr-four-year-seven-lottery-audit` |
| Base | `814a8e9` |
| Worktree | `/Users/faustosantana/Projects/justech-four-year-audit` |
| FEATURED_SEVEN | 7 |
| production_forbidden | true |
| Rango | 2022-07-26 → 2026-07-23 |
| Fechas analizadas | 1457 |
| audit_id | `2e523103-fcf9-439e-b6d4-2db0f1e47a40` |

## Veredictos

| Tipo | Valor |
|------|-------|
| Matemático | **GEOMETRIA_CORRECTA** |
| Estadístico | **SIN_VENTAJA** |

### Preguntas claras

| Pregunta | Respuesta |
|----------|-----------|
| ¿Supera el azar (same-k, umbral 1.10)? | **No** (lift=1.066, cerca de 1) |
| ¿Ventana principal? | W3 día calendario siguiente |
| ¿Hit rate / n? | 0.284635 sobre 794 |
| ¿IC95? | [0.254343, 0.317001] |
| ¿Walk-forward? | 4 pasos |
| ¿Estable por año? | ver YEARLY_STABILITY (tasas ~0.25–0.33) |

### J-11A

- **GO_PARA_J11A_SOLO_COMO_COPILOTO_ANALITICO**
- **NO_GO_PARA_J11A_PREDICTIVO**

## Artefactos

- `artifacts/four_year_audit/executive_report.html`
- `artifacts/four_year_audit/statistics.json`
- `artifacts/four_year_audit/summary.csv`
- `artifacts/four_year_audit/relationships.csv`
- `artifacts/four_year_audit/number_profiles.csv`
- `artifacts/four_year_audit/cases.json`

## Pruebas

`pytest tests/test_nr_four_year_audit.py` (+ historical) — ver CI local.

Motor / Tabla 1 / Tabla 2 / Producción: **intactos**.
