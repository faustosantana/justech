# Lottery IA — Alerting Runbook

> Versión: 2.0 | Detector continuo en `lottery-sync-worker` (sin cron paralelo)

## Arquitectura

Producción usa `LOTTERY_SYNC_WORKER_STANDALONE=true`. El API **no** arranca APScheduler.

El detector vive en el mismo proceso worker:

```
python -m app.lottery.sync.worker
  └── loop 60s (sync tick)
        └── maybe_run_detector_tick()   # cadence independiente
              └── LotteryAiAlertDetector.run()
                    └── Redis lock: lottery:ai:alert-detector
```

| Setting | Default |
|---------|---------|
| `LOTTERY_AI_ALERT_DETECTOR_ENABLED` | `true` |
| `LOTTERY_AI_ALERT_DETECTOR_INTERVAL_SECONDS` | `300` (clamp 60–3600) |
| `LOTTERY_AI_ALERT_LOCK_TTL_SECONDS` | `240` |

Si el lock está ocupado: skip silencioso (debug), **sin** alerta `lock_busy`.

`POST /lottery/admin/ai/alerts/detector/run-now` usa el mismo lock (no paraleliza).

Si algún día `standalone=false`, se podría añadir un `add_job` en `lottery_scheduler.py` — **nunca** ambos owners a la vez.

## Ciclo de vida

`open` → `acknowledged` / `silenced` → `resolved` (o `reopened`)

Auto-resolve: cuando la condición desaparece → `resolved` + `auto_resolved=true` (historial conservado).

## Endpoints

- `GET /alerts` (filtros status/severity/code)
- `GET /alerts/{id}`
- `POST /alerts/{id}/acknowledge|resolve|silence|reopen`
- `POST /alerts/detector/run-now`

## Reglas mínimas

PROVIDER_DOWN, MODEL_DEGRADED, FALLBACK_HIGH, TOOL_FAILURE_HIGH, CONTEXT_LOSS,
MEMORY_PERSISTENCE_FAILURE, OUT_OF_DOMAIN_FAILURE, TECHNICAL_LEAK, BENCHMARK_DEGRADED,
UNNECESSARY_CLARIFICATION_HIGH, TOKEN_USAGE_HIGH, NO_SUCCESSFUL_CALL, JSON_VISIBLE

Umbrales versionados: tabla `lottery_ai_alert_thresholds` + defaults en
`app/lottery/ai/alert_thresholds.py`.
