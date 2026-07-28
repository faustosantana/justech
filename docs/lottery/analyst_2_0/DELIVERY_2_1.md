# Lottery Analyst 2.1 — Entrega DEV (Analyst Reasoning Layer)

**Fecha:** 2026-07-28  
**Branch:** `feature/nr-complete-analysis-prediction-engine`  
**Tag DEV:** `lottery-analyst-2.1.0-reasoning-dev`  
**Imagen DEV:** `jaios-app-backend:lottery-analyst-2.1.0-reasoning-dev`  
**Producción:** no promovida (Beta 2.0 / official-scope hotfix permanece en worker / prod pin previo)

---

## Arquitectura antes → después

```
ANTES (2.0):
Usuario → Intent/Hermes → Planner → SQL
  → plantilla factual
  → Huawei rewrite (frecuente, sin Evidence Package)
  → Usuario

DESPUÉS (2.1):
Usuario → Intent/Hermes (+ reasoning_mode) → Research Planner
  → SQL / Motor según corresponda
  → EvidencePackage verificado
  → [si mode aporta valor] Huawei Analyst Reasoning
  → Factual Guard
  → respuesta natural (preserve multi-párrafo)
  [si mode=skip] plantilla / evidence_reuse sin Huawei
```

Huawei **no** elige tools, **no** decide SQL, **no** altera evidencia. Hermes selecciona el modo.

---

## Cuándo Huawei sí aporta

- Explicar / analizar / por qué / qué significa / qué observas
- Comparar frecuencias o pares
- Interpretar coincidencia same-day (misma fecha ≠ misma lotería)
- Resumir investigación / sesión
- Clarificar limitaciones / rechazar predicción garantizada

## Cuándo no debe llamarse

- “¿Cuál fue la fecha?” / “¿En qué posición?” / “¿En cuáles loterías?”
- “¿Cuántas veces?” como attribute follow-up (`attr=count`)
- Reuse factual corto sin verbos de análisis

**Banco ANALYST_REASONING_40:** ~70% invoke / ~30% skip (orientativo del diseño de modos).

---

## Suites (obligatorias)

| Suite | Resultado | Notas |
|-------|-----------|--------|
| ANALYST_REASONING_40 | **47/47** unit (40 modos + guards) | Offline + DEV |
| Official Scope | **18+ PASS** (pack 65 con reasoning) | DEV |
| Agent50 | **50/0** | Offline |
| Manual30 | **30/0** | DEV API |
| Cert200 | *(en corrida / ver cierre abajo)* | DEV API, banco/semilla intactos |
| A/B 20 | **B_ACCEPT** (18 B / 0 A / 1 tie; 0 regressions exactitud) | Offline |

---

## Smoke DEV (35+14)

| Turno | Resultado |
|-------|-----------|
| ¿Cuántas veces coincidieron el 35 y el 14? | Conteos **120**; si Huawei inventa total alterno → Guard rechaza → fallback interpretativo con “misma lotería” |
| ¿En cuáles loterías? | `evidence_reuse` / sin Huawei |
| Explícame la coincidencia… | Huawei `explain_evidence`, guard OK, 120 + interpretación |

---

## Telemetría (`agent_trace.analyst_reasoning`)

`reasoning_mode`, `provider_used`, `model_used`, `evidence_hash`, `prompt_version` (`analyst-reasoning-v1.1`), `latency_ms`, `input_tokens`, `output_tokens`, `guard_passed`, `rejection_reason`, `fallback_used`.

No se registra chain-of-thought.

**Observado en smoke:** latencia Huawei ~19–24 s; tokens a menudo `null` desde ModelArts; rechazos típicos `count_mismatch` cuando el modelo inventa totales alternos (p. ej. 40≠120) — fallback seguro conserva exactitud.

---

## Restricciones respetadas

- Motor matemático, histórico, OFFICIAL_LOTTERY_SCOPE (7), Prompt Maestro v6, Cert200/semilla/evaluadores: sin cambio de contrato
- Hermes DecisionEngine conservado (+ `reasoning_mode`)
- Sin auto-deploy a producción

---

## Veredicto

Ver sección final tras Cert200.
