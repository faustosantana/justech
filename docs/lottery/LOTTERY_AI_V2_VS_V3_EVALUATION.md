# Lottery IA — Evaluación v2 vs v3 (suite 300)

**Activar v3:** `False`
**Razón:** v3 no supera gates vs v2 — mantener v2 activo; v3 draft

## Resumen

| Métrica | v2 | v3 |
|---|---:|---:|
| Total | 350 | 350 |
| Pass rate | 0.66 | 0.66 |
| P0 | 31 | 31 |
| P1 | 88 | 88 |
| P2 | 0 | 0 |
| P3 | 0 | 0 |
| Memory retention | 0.6 | 0.6 |
| Reference resolution | 1.0 | 1.0 |
| Domain rejection | 0.56 | 0.56 |
| Clarification rate | 0.4 | 0.4 |
| Latency p50 ms | 0 | 0 |
| Latency p95 ms | 2 | 7 |

## Distribución de casos

```json
{
  "memory_multiturn": 50,
  "references": 30,
  "calendar_following_days": 30,
  "draw_following": 30,
  "multilottery": 30,
  "number_switch_keep_context": 25,
  "out_of_domain": 25,
  "restricted_technical": 20,
  "prediction": 20,
  "proactive_analysis": 30,
  "preferences_depth": 20,
  "provider_fallback": 20,
  "renderer": 20
}
```

## Nota

Evaluación offline de understanding/domain/memory (sin secretos, sin LLM remoto).
Tokens/fallback de síntesis remota no aplican en este runner local.
