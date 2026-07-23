# Lottery IA — Benchmark ≥300

Suite offline versionada en `backend/app/lottery/ai/benchmark.py`  
(shim: `benchmark_300.py`).

## Totales

- Casos: **350** (≥250 requerido, margen sobre 300)
- Evaluación: understanding + domain + memoria (sin LLM remoto de síntesis)
- Gate publicación: `publish_blocked` si P0>0 o P1>0

## Distribución mínima

| Categoría | Objetivo | En suite |
|-----------|----------|----------|
| Memoria multi-turn | 50 | 50 |
| Referencias / pronombres | 30 | 30 |
| Días posteriores | 30 | 30 |
| Sorteos posteriores | 30 | 30 |
| Multilotería | 30 | 30 |
| Cambio de número + contexto | 25 | 25 |
| Fuera de dominio | 25 | 25 |
| Técnicos restringidos | 20 | 20 |
| Predicción | 20 | 20 |
| Análisis proactivo | 30 | 30 |
| Preferencias / profundidad | 20 | 20 |
| Provider / fallback | 20 | 20 |
| UI / JSON / Markdown | 20 | 20 |

## Severidades

- **P0:** inventado / fuga / OOD / predicción como certeza / aislamiento  
- **P1:** contexto perdido / fecha-lotería / tool incorrecta / memoria sobrescrita  
- **P2:** aclaración innecesaria / insight irrelevante / formato  
- **P3:** tono / estilo  

## Cómo ejecutar

```bash
cd backend && PYTHONPATH=. python -c \
  "from app.lottery.ai.benchmark import compare_v2_v3, write_evaluation_docs; write_evaluation_docs(compare_v2_v3())"
```

API Admin:

- `POST /lottery/admin/ai/benchmarks/run-300`
- `POST /lottery/admin/ai/benchmarks/compare-v2-v3`
