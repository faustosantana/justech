# Estado del bloque maestro — Administración Justech + e-CF

## ESTADO GENERAL: PASS TÉCNICO / BLOQUEADO POR CERTIFICACIÓN DGII

No se declara PASS total de certificación DGII: faltan credenciales y certificado autorizados.

## Checklist de cierre

| Ítem | Estado |
|---|---|
| UAT visual | PASS |
| Firma real de laboratorio | PASS |
| API versionada `/api/v1/ecf` | PASS |
| Recepción e-CF | PASS |
| Tests (smoke + benches + unit tags) | PASS / ver log |
| Rendimiento 100 / 1k / 10k | Documentado |
| Multiempresa 4/4 | PASS |
| NCF + e-CF coexistencia | PASS |
| Seguridad (hash/auth) | Intacta |
| Histórico / GL | Intactos (unbalanced=0) |
| Certificación DGII real | BLOQUEADA (credenciales externas) |

## Evidencias

- `backup-register.md`
- `dgii-source-register.md`
- `DGII_CERTIFICATION_READINESS.md`
- `LAB_SIGNATURE_PROCEDURE.md`
- `PERFORMANCE_REPORT.md`
- `UAT_VISUAL_REPORT.md`
- `uat/screenshots/`

## Entorno

- erp.justech.do / justech_dev / feature/fiscal-standard-consolidation
- justgroup.app: **no tocada**
