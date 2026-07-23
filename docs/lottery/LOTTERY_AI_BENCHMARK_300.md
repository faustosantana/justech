# Lottery IA — Benchmark 300

Suite offline en `backend/app/lottery/ai/benchmark.py`.

## Totales

- Casos generados: **350** (≥300 requerido)
- Seed DB: `Suite 300 closeout` vía `LotteryAiAdminService.ensure_seeded()`

## Distribución mínima

| Categoría | Cantidad |
|-----------|---------:|
| memory_multiturn | 50 |
| references | 30 |
| calendar_following_days | 30 |
| draw_following | 30 |
| multilottery | 30 |
| number_switch_keep_context | 25 |
| out_of_domain | 25 |
| restricted_technical | 20 |
| prediction | 20 |
| proactive_analysis | 30 |
| preferences_depth | 20 |
| provider_fallback | 20 |
| renderer | 20 |

## Severidades

- **P0**: fuga técnica, fuera de dominio, predicción como certeza, tenant/credenciales
- **P1**: contexto/fecha/lotería/tool/cálculo incorrecto
- **P2**: aclaración innecesaria, formato, parámetros
- **P3**: tono/longitud/redacción

Publicación bloqueada con P0 o P1 (`publish_prompt` + `publish_blocked`).

## Ejecución

```bash
cd backend
PYTHONPATH=. python -m app.lottery.ai.benchmark
```

Artefactos: `docs/lottery/LOTTERY_AI_BENCHMARK_300.json`, evaluación v2/v3.
