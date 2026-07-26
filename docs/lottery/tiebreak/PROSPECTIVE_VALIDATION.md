# Validación prospectiva

## Objetivo

Generar predicción **antes** del sorteo, bloquearla, y evaluar solo con resultado futuro.

## Estados

```
DRAFT → LOCKED → EVALUATED
```

Una predicción `LOCKED` es inmutable.

## Persistencia (DEV)

In-memory: `analysis_engine/prospective_validation.py`  
Artefacto placeholder: `artifacts/tiebreak/prospective_predictions.json`

## Payload guardado

fecha/hora creación, input, candidatos, ranking, regla de desempate (`tiebreak`), versión motor, **hash SHA-256**, fecha/hora de bloqueo, resultado posterior, evaluación.

## Endpoints

| Method | Path |
|--------|------|
| POST | `/api/v1/prospective-validation/predictions` |
| POST | `/api/v1/prospective-validation/predictions/{id}/lock` |
| POST | `/api/v1/prospective-validation/predictions/{id}/evaluate` |
| GET | `/api/v1/prospective-validation/predictions` |
| GET | `/api/v1/prospective-validation/metrics` |

## Reglas

- No editar `LOCKED`.
- Evaluate requiere resultado futuro explícito en el body.
- Hash se calcula al crear (contenido de predicción + motor).
