# 06 — Reportes DGII (606 / 607 / 608 / 609 / 623)

## Implementación

| Reporte | Modelo exporter | Mapping | Estado código |
|---|---|---|---|
| 606 | `justech.do.dgii.606.exporter` | `dgii_606_mapping.json` | instalado |
| 607 | `justech.do.dgii.607.exporter` | `dgii_607_mapping.json` | instalado |
| 608 | `justech.do.dgii.608.exporter` | `dgii_608_mapping.json` | instalado |
| 609 | `justech.do.dgii.609.exporter` | `dgii_609_mapping.json` | instalado |
| 623 | `justech.do.dgii.623.exporter` | `dgii_623_mapping.json` | instalado |

Framework: `dgii_exporter_mixin`, `justech.do.fiscal.report`, period, review/approval, tax classifier.

## Uso en BD DEV

| Tipo | Observado |
|---|---|
| 606 | Varios `validated` + `generated` (jul 2026, co 1) |
| 607 | 1 `validated` (jun 2026) |
| 623 | 3 `draft` |
| 608 / 609 | Sin filas recientes en muestra top |

## Riesgos (sin corregir)

1. Exporters leen campos Justech + LATAM vía FDP — **dependen de verdad dual** (FISC-AUD-001).
2. Prefijos inconsistentes en moves pueden entrar a TXT (FISC-AUD-002).
3. Cobertura de prueba reports existe (phase19–21) pero no se ejecutó en esta fase (solo inventario).
4. 608/609 con poca evidencia operativa DEV → **requiere reproducción** en remediación.

## Veredicto por reporte (auditoría estática + datos)

| Reporte | Veredicto auditoría |
|---|---|
| 606 | **AUDITADO** — código+datos; riesgo dual-stack |
| 607 | **AUDITADO** — código+1 run validado |
| 608 | **AUDITADO (código)** — datos insuficientes |
| 609 | **AUDITADO (código)** — datos insuficientes |
| 623 | **AUDITADO** — drafts presentes; retenciones instaladas |

No se generaron archivos nuevos ni se alteraron reportes.
