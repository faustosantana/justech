# Lottery Analyst 2.1 — Entrega DEV (Analyst Reasoning Layer)

**Fecha:** 2026-07-28 / 2026-07-29  
**Branch:** `feature/nr-complete-analysis-prediction-engine`  
**Commit tip:** `0c192b7`  
**Tag DEV:** `lottery-analyst-2.1.0-reasoning-dev`  
**Imagen DEV:** `jaios-app-backend:lottery-analyst-2.1.0-reasoning-dev`  
**Producción:** **no promovida** (Beta 2.0 / official-scope hotfix sigue fuera de este pin)

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
- Mensajes truncados incompletos → clarify (sin research)

**ANALYST_REASONING_40:** 32/40 invoke (80%) / 8 skip (20%) — diseño de modos del banco.

---

## Suites obligatorias

| Suite | Resultado |
|-------|-----------|
| ANALYST_REASONING_40 | **47/47** unit |
| Official Scope | **PASS** (pack 65 con reasoning) |
| Agent50 | **50/0** |
| Manual30 | **30/0** |
| Cert200 | **200/0 CERTIFIED** (`cert200-20260728T233306Z-4f4e5d11`) |
| A/B 20 | **B_ACCEPT** (18 B / 0 A / 1 tie; 0 regressions de exactitud) |

---

## Smoke DEV (35+14)

| Turno | Resultado |
|-------|-----------|
| ¿Cuántas veces coincidieron el 35 y el 14? | **120**; si Huawei inventa total → Guard rechaza → fallback interpretativo (misma fecha ≠ misma lotería) |
| ¿En cuáles loterías? | `evidence_reuse` / sin Huawei |
| Explícame la coincidencia… | Huawei `explain_evidence`, guard OK, 120 + interpretación |
| Mensaje cortado: ¿cuándo salió el | Clarify: «¿La última vez de cuál número?» |

---

## Telemetría (`agent_trace.analyst_reasoning`)

`reasoning_mode`, `provider_used`, `model_used`, `evidence_hash`, `prompt_version` (`analyst-reasoning-v1.1`), `latency_ms`, tokens (a menudo `null` en ModelArts), `guard_passed`, `rejection_reason`, `fallback_used`.

**Observado:** latencia Huawei ~19–24 s; rechazos típicos `count_mismatch` cuando el modelo inventa totales alternos — fallback seguro conserva exactitud y la narrativa interpretativa.

No se registra chain-of-thought.

---

## Costo / latencia (DEV smoke)

- Turnos attribute / reuse: <1–4 s, sin Huawei  
- Turnos reasoning: ~20–25 s Huawei + SQL previo  
- Objetivo cumplido: menos llamadas inútiles; más valor cuando se llama; Guard evita invención

---

## Restricciones respetadas

- Motor matemático, histórico, OFFICIAL_LOTTERY_SCOPE (7), Prompt Maestro v6, Cert200/semilla/evaluadores: sin cambio de contrato  
- Hermes DecisionEngine conservado (+ `reasoning_mode`)  
- Sin auto-deploy a producción  

---

## Veredicto

# LISTO PARA BETA 2.1

Condición: imagen/tag DEV anteriores; **promoción a prod requiere paso manual explícito** (no automático).
