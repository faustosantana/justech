# COMPONENT_SCORE.md

**Método:** score de *autoridad sobre el resultado correcto* en el producto conversacional Lottery Analyst, ponderado por (a) control de decisión, (b) control de verdad factual, (c) frecuencia de uso observada.  
**No es marketing.** Basado en flujo de código + corpora v2452 / Cert200 / Agent50 / Manual30 / smoke.

---

## 1. Score de inteligencia (producto conversacional actual)

| Componente | Score | Qué controla | Base empírica |
|------------|------:|--------------|---------------|
| **Intent + Classifier + Planner (determinista)** | **28%** | Qué tool / kind / params | Sin esto no hay path; dual layers pero autoridad real aquí |
| **Query / Repository (histórico SQL)** | **24%** | Totales, fechas, loterías verdaderas | Caso 35+14: 1893→120 al filtrar scope; verdad vive aquí |
| **HermesDecisionEngine** | **15%** | Research vs reuse vs meta; continuidad 2.0 | Agent50 50/0; smoke reuse; Manual30 continuidad |
| **Huawei ModelArts (síntesis)** | **18%** | Voz final / explicación NL | 35/44 turns v2452; ~12–14 s latencia; no decide tools |
| **Evidence + ActiveInvestigation Session** | **10%** | Memoria estructurada 10 min; reuse | Smoke T2 reuse; invalida scope sucio |
| **Motor Matemático** | **3%** | Señales T1×T2 en analyze/complete | **0%** en same-day coincidence path |
| **Formatter / templates / scope phrasing** | **2%** | Forma mínima si LLM off | Fallback local_template |

**Suma = 100%.**

---

## 2. Score por tipo de pregunta

### A) Coincidencia same-day / last coincidence (núcleo del hotfix)

| Componente | % |
|------------|--:|
| Intent/Planner/Classifier | 30 |
| SQL Query | 35 |
| Hermes | 12 |
| Huawei | 15 |
| Evidence/Session | 6 |
| Motor | **0** |
| Formatter | 2 |

### B) Follow-up «¿En cuáles loterías?»

| Componente | % |
|------------|--:|
| Hermes + Evidence reuse | **55** |
| Session memory | 25 |
| NaturalResponseGenerator | 15 |
| Huawei | **0** (si reuse) |
| SQL | 0 (si reuse) |
| Motor | 0 |

### C) «Analiza 35+14» / complete analysis

| Componente | % |
|------------|--:|
| Motor Matemático | **45** |
| Planner (elige RUN_COMPLETE_ANALYSIS) | 20 |
| Huawei (explica) | 20 |
| Intent | 10 |
| Session | 5 |

---

## 3. Quién aporta más / menos

| Ranking | Componente | Motivo |
|---------|------------|--------|
| **Más inteligencia operativa (decidir + verdad)** | Intent/Planner + SQL | El usuario obtiene la respuesta *correcta* por reglas + DB |
| **Más percepción de “IA”** | Huawei | Tono `**Conclusión:**`, latencia alta |
| **Más continuidad** | Hermes + Evidence | Diferencia Analyst 2.0 vs 2.4.x |
| **Menos en chat coincidencias** | Motor Matemático | Camino explícitamente bloqueado en same_day planner |
| **Menos autoridad de decisión** | Huawei | No elige tool ni scope |

---

## 4. Limitación del score

- Cert200 no persiste `provider_used` → no se puede recalcular score Huawei post-2.0 con n=200 etiquetado.
- No hay corrida instrumentada de 100 conversaciones nuevas (prohibido instrumentar en esta fase).
- Score de Motor sube si el mix de producto se desplaza a análisis completo; hoy el tráfico certificado está sesgado a histórico/continuidad.
