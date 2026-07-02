# Fase 19.4 — Corrección período y revisión visible

## Problema

El wizard 606 mostraba período `202606` con fechas `30/06 — 30/06` porque `date_from` y `date_to` tomaban `context_today` y `period_code` solo se calculaba desde `date_from`.

## Solución

Nuevo modelo utilitario `justech.do.dgii.period` con:

- `period_bounds_from_code("YYYYMM")` → primer y último día del mes
- Validación de formato, mes 01–12, años 2000–2100
- Febrero con 28/29 según año bisiesto
- `validate_period_dates()` — coherencia período ↔ fechas

El wizard usa `period_code` como entrada principal; `date_from` / `date_to` son de solo lectura y se derivan del período.

## Ejemplos

| Período | Desde | Hasta |
|---------|-------|-------|
| 202606 | 01/06/2026 | 30/06/2026 |
| 202602 | 01/02/2026 | 28/02/2026 |
| 202402 | 01/02/2024 | 29/02/2024 |

## Archivos

- `models/dgii_period.py`
- `wizard/fiscal_report_wizard.py`
- `wizard/fiscal_report_wizard_views.xml`
