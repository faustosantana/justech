# E0068 — Root Cause Analysis

**Case:** E0068 (`compare_numbers`)  
**Prompt at fail:** `7.0.0-rc3.4` / hash `41c64a0f…da642ff9`  
**Preserved:** `evidence/prompt_runtime/final_cert/SHADOW200_20260731T164155Z/E0068_EVIDENCE/`  
**Reconstruction hash:** `9a2836f1288f9f5d` (match)

---

## 1. Conversación

| Campo | Valor |
|-------|--------|
| setup | `[]` (sin mensajes previos) |
| user | Compara históricamente el 61 y el 14: ¿quién aparece más… |
| conversation_id (fail) | `2d70e9c9-a3eb-4e70-9b9c-813e1deb3a83` |
| correlation_id (fail) | `0182c28a-d734-4ed3-8513-b3dc23f1a566` |

---

## 2. Intent / routing

| Campo | Valor |
|-------|--------|
| route / provider | `huawei_modelarts` / `deepseek-v3.2` |
| reasoning_mode | `explain_evidence` |
| resolved_intent | `new_investigation` |
| relation | `same_day` |
| eligible_shadow | true |
| fallback | false |

---

## 3–7. Evidence Package / contract / subjects / counts / dimensions

| Campo | Valor |
|-------|--------|
| subjects | `["61","14"]` |
| counts | `{"total": 152}` **solo** |
| positions (labels en filas) | `["1ro","2do","3ro"]` — **sin conteos por posición en `counts`** |
| comparison_data | `{}` |
| dates | muestra truncada (LLM ve ≤5 anchors) |
| canonical_count | 152 |
| allowed_subjects | `["14","61"]` |
| allowed_counts (rc3.4) | **no existía** como lista explícita |
| allowed_dimensions (rc3.4) | **no existía** |

**known_facts (extracto):** único conteo canónico `counts.total=152`; *“No hay desglose por posición/primera posición en el paquete; no lo inventes.”*

**forbidden_claims:** inventar subtotales de posición; tratar tamaño de muestra como total.

### Contradicción crítica del paquete

`factual_answer` (template `summarize_coincidences` / formatter) **sí contiene**:

```
En 1ra posición:
- 94 caso(s) con al menos uno de los números en 1ra (ambos en 1ra: 20).
En otras posiciones:
- 58 caso(s).
```

Esos 94 / 20 / 58 se calculan sobre los 152 ítems del motor, pero **no se publican en `counts`** ni en `response_contract`. El paquete afirma a la vez “no hay desglose” y lo imprime en `factual_answer`.

---

## 8. Prompt Studio rc3.4

Bloques ya prohibían desgloses inventados (`PROHIBIDO inventar desgloses… ambos en primera posición N veces`).  
Studio **no cumplió** de forma estable (falla no determinista: reconstrucción posterior a veces PASS).

---

## 9–12. Respuestas y guard

| Canal | Resultado |
|-------|-----------|
| Legacy RAW | Total 152; **no** decide quién aparece más; pide nuevo desglose |
| Studio RAW (fail) | Afirma que **14 aparece más** usando **94** vs **20** en 1ª posición; menciona total 152 |
| Guard Studio | `passed=false`, `count_mismatch:20!=152`, `hallucination=true` |
| Guard Legacy | `true` |
| same Evidence Package | `true` |
| hash Studio | match rc3.4 |

---

## 13. Frases exactas de invención / mal uso

> «El número 14 aparece más en coincidencias same-day con el 61, con **94** casos en primera posición frente a **20** casos en que ambos coincidieron en primera posición.»

> «…del total de 152 coincidencias same-day, en **94** ocasiones al menos uno… y en solo **20** ocasiones ambos salieron en primera posición…»

Errores compuestos:

1. Usar métricas de posición **no autorizadas en `counts`/contract**.
2. Interpretar `first_related` vs `both_first` como “el 14 aparece más que el 61” — **inferencia falsa** (no son conteos por sujeto).

---

## 14. ¿Dónde aparecen 94 y 20?

| Fuente | 94 | 20 |
|--------|----|----|
| Pregunta | no | no |
| `counts` | no | no |
| `response_contract` rc3.4 | no | no |
| `comparison_data` | no | no |
| Memoria / setup | no | no |
| Prompt rc3.4 | no | no |
| Tools metadata | no como contract | no |
| Filas `occurrences` (muestra) | no como totales | no |
| **`factual_answer` template** | **sí** | **sí** |
| Studio RAW fail | sí | sí |
| Legacy RAW fail | no | no |

---

## 15. Por qué Studio convirtió 152 en subtotales

1. El LLM recibe `factual_answer` con desglose 94/20/58.
2. La pregunta pide un **ganador** (“quién aparece más”).
3. El modelo **reutiliza** cifras del template y las **reinterpreta** como ranking por sujeto.
4. `counts`/`known_facts`/`prompt` contradicen eso, pero el texto narrativo del paquete gana en la práctica.
5. El guard solo ve `20≠152` → `count_mismatch`, sin etiqueta `unauthorized_breakdown`.

---

## Clasificación de causa (prioridad)

| Causa | Aplica |
|-------|--------|
| **Evidence Package ambiguo** | **Primaria** — `factual_answer` vs `counts`/`known_facts` |
| **response_contract incompleto** | **Primaria** — sin `allowed_counts` / `allowed_dimensions` / `forbidden_inferences` |
| **prompt demasiado permisivo (en la práctica)** | Secundaria — reglas existen; el modelo las viola de forma intermitente |
| **factual guard incompleto** | Secundaria — atrapa cifra pero no tipifica breakdown / false ranking |
| formatter | Contribuye al template de `factual_answer` |
| otra | No determinismo del LLM |

---

## Dirección de corrección (post-autopsia)

1. Contrato canónico de dimensiones desde `counts` únicamente.  
2. Payload LLM: no autorizar desgloses ausentes en `counts` (sanitizar `factual_answer` y/o `forbidden_inferences`).  
3. Guard: `unauthorized_breakdown`.  
4. Prompt **rc3.5** (sin editar rc3.4): reglas mínimas de total-only / no inventar desgloses / no decidir ganador sin evidencia por sujeto.  
5. **No** cambiar la pregunta E0068 ni el dataset.
