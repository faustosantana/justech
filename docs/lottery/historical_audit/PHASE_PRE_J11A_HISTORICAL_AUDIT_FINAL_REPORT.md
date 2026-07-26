# PHASE PRE-J11A — Historical Manual Logic Audit — Final Report

**Stop point:** Informe final emitido. **No se inicia J-11A.** Esperar autorización explícita.

## Isolation

| Field | Value |
|-------|--------|
| Branch | `feature/nr-historical-manual-logic-audit` |
| Base commit | `47192af` |
| Worktree | `/Users/faustosantana/Projects/justech-historical-manual-audit` |
| DEV | `jaios_lottery_dev` @ `127.0.0.1:5433` |
| Draws | 91,941 |
| FEATURED_SEVEN | **7** |
| production_forbidden | **true** |
| Motor/tables modified | **false** |

## Acceptance checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Histórico auditado automáticamente | PASS |
| 2 | ≥10 casos documentados | PASS (11) |
| 3 | C1, C3, C4, C5 reproducidos (geometría) | PASS |
| 4 | ≥6 casos nuevos por seed | PASS |
| 5 | Aciertos y fallos | PASS |
| 6 | Cada caso explica T1/T2/confirmación | PASS |
| 7 | C2 permanece rechazado | PASS (HIST-011) |
| 8 | Look-ahead bloqueado en selección | PASS |
| 9 | Comparación contra azar | PASS (fair baselines) |
| 10 | Numeradores/denominadores | PASS |
| 11 | FEATURED_SEVEN = 7 | PASS |
| 12 | Metodología sin cambios | PASS |
| 13 | Motor/tablas intactos | PASS |
| 14 | Producción intacta | PASS |
| 15 | Pruebas | PASS (19 unit tests) |

## Geometry reproduction (partner cases)

| Case | Observados | Manual | Motor fuerte | Ventanas |
|------|------------|-------:|--------------|----------|
| C1 | 41×70 (+Nacional 41 si existe) | 29 | **29** | FALLO bajo ventanas A–D |
| C2 | 41×62 | 75 | none (T2 directa) | DIRECT_T2_RECHAZADO |
| C3 | 49×44×70 | 35 | **{22,35}** | FALLO (no único; no hit ventanas) |
| C4 | 35×14 | 54 | **54** | ACIERTO (día siguiente) |
| C5 | 35×14 (NY 2:30 × Nacional) | 54 | **54** | ACIERTO (Gana Más 54-19-77, ref 226103) |

## Population signal (next calendar day)

- Official: **536 / 2072** = 0.258687  
- Random same k: **551 / 2072** = 0.265927  
- Lift official vs random-k: **0.9728**  
- Absolute diff: **−0.72 pp**

Beats random-one (lift 1.41) but **fails equal-k control**.

## Verdicts

### Lógica histórica

**D. LÓGICA RECHAZADA** (como regla predictiva con ventaja sobre azar controlado por \(k\))

Código interno: `D_RECHAZADA`.

Motivo: tras eliminar bias de look-ahead en el baseline, el lift vs selección aleatoria con igual cantidad de candidatos es ≈1 (de hecho 0.97). No se afirma valor predictivo.

La geometría manual del socio **sí se reproduce** (C1/C3/C4/C5). Eso valida consistencia del motor con el método manual, **no** edge estadístico en la ventana next-day.

### Gate J-11A

**NO-GO PARA J-11A**

No iniciar J-11A hasta autorización explícita que acepte:

1. Geometría confirmada, y/o  
2. Redefinición de hipótesis/ventana/unidad, **sin** cambiar fórmulas T1×T2 automáticamente.

## Deliverables

- Spec, methodology, 10 cases, full results, statistics, random baseline, failure analysis (this folder)
- Evidence JSON/CSV under `evidence/`
- API + UI Historical Audit
- Tests: `backend/tests/test_nr_historical_manual_audit.py`

## Disclaimer

Esta auditoría **no** es garantía predictiva. C2 permanece señal experimental rechazada.
