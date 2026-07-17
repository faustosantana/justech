# 11 — Crons, actividades y correos

## Crons fiscales / Justech (DEV)

| ID | Nombre | Active | Freq | lastcall | Efecto |
|---|---|---|---|---|---|
| 89 | Justech NCF: alertas internas consolidadas | t | 1 day | 2026-07-16 | Baseline — actividades internas |
| 57 | FISCAL SEQUENCE: Expire sequences | t | 1 day | 2026-07-16 | Adel — puede afectar secuencias LATAM |
| 85 | Justech e-CF: procesar cola | t | 1 min | continuo | e-CF queue |
| 87 | Justech: actualizar padrón DGII | **f** | 1 hour | — | padrón |
| 84 | Justech Audit: limpieza retención | t | 1 day | — | logs |
| 88 | Justech Fees: generar documentos | t | 1 day | — | recurring fees (no NCF audit core) |

## Alertas NCF (baseline)

- Método: `model._cron_process_ncf_range_alerts()`
- Actividades abiertas NCF: **0**
- `mail.mail` NCF: **0**
- **NO TOCAR**

## Riesgos

| ID | Riesgo |
|---|---|
| FISC-AUD-004 | Cron Adel expire sequences activo junto a motor Justech |
| FISC-AUD-021 | e-CF cron 1/min — carga; verificar idempotencia en remediación |

No se desactivó ningún cron.
