# HUAWEI_AUDIT.md

**Componente:** Huawei ModelArts (DeepSeek-V3.2) vía `_synthesize_via_hermes`  
**Archivo:** `backend/app/services/lottery_chat_service.py` (`_synthesize`, `_synthesize_via_hermes`)  
**Provider label en traces:** `huawei_modelarts`  
**Prompt activo:** Analyst v6 (`lottery_analyst_system_v6`)

---

## 1. Qué hace Huawei realmente

Orden oficial en `_synthesize`:

1. Si `assistant_synthesis_enabled=False` → plantilla local (sin LLM)
2. `LLMRouter.complete` (si `assistant_synthesis_provider` configurado)
3. Else → **`_synthesize_via_hermes`** (HTTP ModelArts)
4. Fallback → `local_template`

Entrada típica: `question` + **`template` ya factual** (fechas, totales, loterías) + facts/context.  
Salida: texto natural reescrito. Guardrails posteriores pueden **forzar vuelta a plantilla** si el LLM pierde fechas (`send_message` date-preservation).

---

## 2. Matriz de capacidades (con evidencia)

| Capacidad | ¿Lo hace? | Evidencia |
|-----------|-----------|-----------|
| Interpreta contexto | **Parcial** — recibe contexto recortado (`active_numbers`, `last_analysis`…) | `_synthesize` ctx_public |
| Toma decisiones de tool | **No** | Tools ya ejecutados antes de `_synthesize` |
| Elige lottery scope | **No** | `OFFICIAL_LOTTERY_SCOPE` / query service |
| Resume evidencia | **Sí** — reformula el template | Respuestas con `**Conclusión:**` |
| Explica | **Sí, estilo** — no inventa el hecho base si guardrails agarran | Prompt Maestro + template |
| Compara | **Solo reescribe** comparación ya calculada por tools | Compare tools → template → LLM |
| Responde | **Sí** — voz final al usuario en ~80% turns pre-2.0 audit | v2452: 35/44 huawei |
| Solo reescribe texto | **Principalmente sí** | Código: template-first synthesis |

---

## 3. Métricas reales (proxies — sin instrumentación nueva)

### Corpus A — conversation-audit v2452 (44 turns)

Fuente: `evidence/lottery-analyst-conversation-audit-20260727/raw_results_v2452.json`

| `provider_used` | n | Latencia LLM mediana |
|-----------------|--:|---------------------:|
| `huawei_modelarts` | **35** | ~13 495 ms |
| `local_template` | **8** | ~169 ms |
| (greeting null) | 1 | — |

- `model_used`: `deepseek-v3.2`
- `prompt_version`: `v6`
- Fallback reasons: `meta_continuity_local_template` (7), `clarify_number_slot_locked` (1)
- **Tokens:** no persistidos en ningún artifact auditado

### Corpus B — Cert200 Analyst 2.0

- 200/0 PASS; latency mean ≈ 12 355 ms  
- **No** guarda `provider_used` en `raw_results.json`  
- Estilo ~93/200 con «Conclusión» (proxy de síntesis LLM, no atribución dura)

### Corpus C — Prod smoke Analyst 2.0

- `providers_seen`: `huawei_modelarts`, `evidence_reuse`  
- Follow-up loterías: **sin** Huawei (`evidence_reuse`)

### Instrumentación «100 conversaciones»

**No existe.** Esta auditoría **no instrumentó** producción (mandato: no modificar código).  
Proxies disponibles: ~44 (v2452) + 200 (cert, sin provider) + 30 manual + 50 agent offline + smoke.

---

## 4. Ejemplos (sin chain-of-thought)

### Huawei reescribe hechos (v2452)

**Usuario:** ¿Han salido el 55 y el 24 el mismo día?  
**Provider:** `huawei_modelarts` · ~16 s  
**Respuesta (extracto):** `**Conclusión:** Sí, el **55** y el **24**…` + total de coincidencias.

Los números/totales vienen del tool; el LLM aporta formato y tono.

### Local template (sin Huawei)

**Usuario:** ¿Cuándo salió?  
**Provider:** `local_template` · `clarify_number_slot_locked` · ~54 ms  
**Respuesta:** `¿La última vez de cuál número?`

### Evidence reuse (sin Huawei)

**Usuario:** ¿En cuáles loterías? (tras 78+02)  
**Provider:** `evidence_reuse`  
**Respuesta:** lista de loterías del `last_event` ya guardado.

---

## 5. ¿Infrautilizado?

| Vista | Conclusión |
|-------|------------|
| Como **decisor** | Infrautilizado a propósito — y correcto: no decide tools. |
| Como **escritor** | **Muy utilizado** en turns con research (~80% v2452). |
| Como **analista matemático** | No usado — Motor aparte. |
| Costo | Domina latencia (p50 ~13–14 s vs <0.4 s template). |

**Huawei no está “apagado”; está acotado a presentación.**  
Si se busca más “inteligencia LLM”, hoy **no** vive ahí en decisiones — viviría en mover planning al LLM (no recomendado sin rediseño).

---

## 6. Veredicto Huawei

Huawei **reescribe, explica en lenguaje natural y embellece** evidencias ya calculadas.  
No planifica, no consulta histórico, no elige el alcance de 7 loterías, no decide reuse.
