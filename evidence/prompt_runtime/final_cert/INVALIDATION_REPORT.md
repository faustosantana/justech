# INVALIDATION REPORT — Shadow200 eligible run `SHADOW200_20260731T164155Z`

**Status:** INVALIDATED  
**Decision:** This run must **not** be used to certify Prompt Runtime Studio / Prompt Runtime 1.0.  
**Date (UTC):** 2026-07-31  

---

## Motivo de invalidación

1. El dataset de certificación fue **modificado a mitad de corrida** después del caso **E0068**.
2. Las 20 preguntas `compare_numbers` se reescribieron para pedir solo el conteo canónico (en lugar de “quién aparece más…”), con el fin de evitar el fallo de Studio.
3. E0068 se **re-ejecutó** con la pregunta alterada y pasó a `product_pass`, ocultando un **product_fail real**.
4. El checkpoint resultante mezcló casos pre-cambio y post-cambio → **no es reproducible ni válido** como Shadow200 elegible.

---

## Dataset modificado durante la corrida

| Item | Detalle |
|------|---------|
| Archivo | `evidence/prompt_runtime/final_cert/SHADOW200_ELIGIBLE_DATASET.json` |
| Alcance | 20 casos `category=compare_numbers` (incl. E0068) |
| Cambio | De “¿quién aparece más en coincidencias same-day…?” → “reporta únicamente el conteo canónico total…” |
| Copia del dataset alterado | `evidence/prompt_runtime/final_cert/SHADOW200_20260731T164155Z/INVALIDATED_RUN/SHADOW200_ELIGIBLE_DATASET_MODIFIED.json` |
| Builder | `build_eligible_dataset.py` también se alteró temporalmente; **restaurado** al template original |

---

## E0068 era un product_fail real

Evidencia preservada en:

`evidence/prompt_runtime/final_cert/SHADOW200_20260731T164155Z/E0068_EVIDENCE/`

| Campo | Valor |
|-------|--------|
| `result_class` | `product_fail` |
| `hallucination` | `true` |
| `studio_guard_reason` | `count_mismatch:20!=152` |
| Pregunta original | Compara históricamente el 61 y el 14: ¿quién aparece más… |
| Fallo | Studio inventó subtotales de posición (94 / 20) no presentes en evidencia; Legacy respondió correctamente que no hay desglose |

Checkpoint anterior al cambio del dataset:

`…/CHECKPOINT_BEFORE_E0068.json` (también restaurado como `CHECKPOINT.json`)

---

## La corrida no puede usarse para certificar

- **No** declarar PASS/FAIL de producto a partir de esta suite.
- **No** reanudar desde checkpoints mezclados (`INVALIDATED_RUN/CHECKPOINT_MIXED.json`).
- Cualquier Shadow200 futuro debe partir de dataset restaurado + política documentada; la corrección de E0068 requiere **prompt/contrato en versión nueva**, no reescritura de preguntas mid-run.

---

## Acciones de consolidación realizadas

1. Runner Shadow200 / pollers detenidos (uvicorn/API intactos).
2. Dataset `compare_numbers` restaurado al texto original.
3. Checkpoint restaurado a `CHECKPOINT_BEFORE_E0068.json`.
4. Evidencia E0068 y artefactos invalidados preservados bajo `E0068_EVIDENCE/` e `INVALIDATED_RUN/`.
5. Prompt Studio / hash / versión: **sin cambios** en esta consolidación.
