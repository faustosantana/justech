# 08 — Auditoría multiempresa

## Empresas

| ID | Nombre | RNC (partner.vat) | Fiscal enabled | Umbrales P/C/E |
|---|---|---|---|---|
| 1 | JUSTECH S.R.L. | 131828061 | t | 20/5/15 |
| 2 | PlugSafe SRL | 132902904 | t | 20/5/15 |
| 3 | Just Office SRL | 133399581 | t | 20/5/15 |
| 4 | Omni Solutions SRL | 132993276 | t | 20/5/15 |

## Rangos por empresa

Todas tienen ≥1 rango B01 activo. JUSTECH tiene set amplio (B01/B04/B11/B13/B14/B15).  
Sin solapes intra-empresa.

## Record rules

Reglas company en document types, ranges, consumption, reports, ecf, fiscal_admin (conteo por módulo en SQL).

## Hallazgos

| ID | Tema | Evidencia |
|---|---|---|
| FISC-AUD-020 | Umbrales idénticos clonados | Puede ser intencional |
| FISC-AUD-003 | Responsables fiscales no asignados por grupo | 0 users en fiscal_manager/user |
| — | Secuencias compartidas accidentales | No evidenciado en rangos Justech |
| — | Reportes mezclan compañías | Framework company_id en `justech_do_fiscal_report` (muestras co=1) |

## Alertas

Baseline multiempresa: una actividad/empresa; sin cruces en UAT previo. DEV sin actividades abiertas.
