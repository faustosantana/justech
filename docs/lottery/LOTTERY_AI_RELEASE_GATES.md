# Lottery IA — Release Gates

## Prompt publish

1. Último benchmark con `p0=0` y `p1=0`
2. Para **v3**: `last_result.v3_activation_gate.activate_v3 == true`
3. `force=true` solo superadmin consciente (no default)

## Activación v3 vs v2

Activar v3 solo si:

- P0 = 0 y P1 = 0
- memory_retention ≥ v2
- reference_resolution ≥ v2
- domain_rejection ≥ v2
- pass_rate ≥ v2
- fallback/p95/tokens dentro de umbral (síntesis remota en UAT online)

Si no: **mantener v2**, v3 queda `draft`.

## Detector / scheduler

- Un solo owner: worker standalone en producción
- Lock Redis `lottery:ai:alert-detector`
- No cron paralelo
- No detector en API cuando `LOTTERY_SYNC_WORKER_STANDALONE=true`

## Sync (fuera de alcance de este closeout)

- Auto-write sigue limitado a loterías con `is_auto_write_enabled`
- Nacional Día sin cambios
- Etapa C no iniciada
