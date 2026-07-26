# Complete Analysis Engine

**Version:** `complete-analysis-engine-j1.0.0`  
**Methodology tables:** `nr-historical-relations-j1.0.0`  
**Branch:** `feature/nr-complete-analysis-prediction-engine`

## Principle

ANALIZAR TODO → DESCUBRIR CANDIDATOS → COMPARAR → ELEGIR AL FINAL.

Never select a fuerte from the first T1 match. Pipeline:

1. Normalize inputs (default position = first)
2. Build complete relationship graph (all observed × T1 × T2)
3. Apply derivations (depth ≤ 2)
4. Collect evidence (deduped fingerprints)
5. Discover candidates **after** `graph.complete`
6. Rank with explainable components + configurable profiles
7. Assign analytical confidence (structural backing, not win probability)
8. Emit experimental signals + optional cases/chains

## Package

`backend/app/lottery/numeric_relations/analysis_engine/`

## Acceptance

`35,14` → FUERTE_PRINCIPAL **54** only after full analysis.
