# J-11A / Engine Test Report

**Date:** 2026-07-26  
**Branch:** `feature/nr-complete-analysis-prediction-engine`

## Command

```bash
cd backend
.venv-prej11a/bin/python -m pytest tests/lottery/analysis_engine tests/lottery/j11a -q
```

## Result

**34 passed**, 0 failed.

Includes §27 coverage: non-greedy selection, T1/T2 labeling, manual cases M1–M5, signal close, same-day reanalysis, J-11A no-table-math, fallback without LLM, Huawei credential reuse marker, production-not-modified marker.
