# Lottery Analyst 2.1 — Analyst Reasoning Layer

**Tag propuesto:** `lottery-analyst-2.1.0-reasoning-dev`  
**Estado:** implementación + suite offline; despliegue solo DEV (no prod automático)

## Antes → Después

```
ANTES (2.0):
Usuario → Intent/Hermes → Planner → SQL → template → Huawei rewrite (casi siempre) → Usuario

DESPUÉS (2.1):
Usuario → Intent/Hermes(+reasoning_mode) → Planner → SQL
  → EvidencePackage verificado
  → [si mode aporta] Huawei Analyst Reasoning
  → Factual Guard
  → Usuario
  [si mode=skip] template factual (sin Huawei)
```

## Componentes nuevos

| Módulo | Rol |
|--------|-----|
| `analyst_reasoning/evidence_package.py` | Paquete estructurado de hechos |
| `reasoning_modes.py` | Hermes selecciona modo |
| `reasoning_prompt.py` | Prompt **separado** del Prompt Maestro |
| `reasoning_layer.py` | Orquesta Huawei + telemetría |
| `factual_guard.py` | Rechaza invención / conteos / loterías externas |

## Cuándo sí / no llamar Huawei

**Sí:** explicar, analizar, por qué, qué significa, comparar, resumir, interpret_pattern en same-day completo.  
**No:** fecha / posición / loterías attribute / conteos cortos / skip mode.

## Restricciones respetadas

- Motor, histórico, OFFICIAL_LOTTERY_SCOPE, Prompt Maestro v6, Cert200/semilla: **sin cambios de contrato**.
- Hermes DecisionEngine: **conservado** (+ `reasoning_mode`).
- Huawei: **no** elige tools.

## Suites

- `ANALYST_REASONING_40` (offline): **47 passed** (`test_analyst_reasoning_40.py`)
- Official Scope: PASS (pack con reasoning)
- Agent50: **50/0**
- Manual30: **30/0** (DEV)
- Cert200: ver `DELIVERY_2_1.md`
- A/B 20: **B_ACCEPT** (18 B / 0 A / 1 tie; 0 regressions de exactitud)

## Veredicto

Ver `DELIVERY_2_1.md` (DEV first; sin auto-promoción a prod).
