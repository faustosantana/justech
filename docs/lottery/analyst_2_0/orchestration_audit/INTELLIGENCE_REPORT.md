# INTELLIGENCE_REPORT.md

**Pregunta central:** ¿Quién toma realmente las decisiones inteligentes del sistema?  
**Respuesta corta:** Las **decisiones** las toman capas **deterministas** (intent + Hermes + planner). La **verdad** la da el **histórico SQL**. La **voz** la da **Huawei**. El **Motor** decide señales matemáticas solo en rutas de análisis completo.

---

## FASE 2 — Responsabilidades (resumen)

| Componente | ¿Decide? | ¿Calcula? | ¿Consulta? | Rol real |
|------------|----------|-----------|------------|----------|
| **Motor Matemático** | Señales/ranking en analyze | **Sí** T1×T2 | Datos de draws vía su pipeline | Inteligencia numérica de producto “análisis” — **ausente** en coincidencia same-day chat |
| **Hermes (DecisionEngine)** | **Sí** turno/reuse | No | State/investigation | Orquestador de continuidad |
| **Huawei** | No tools | No | No histórico | Reescribe / explica NL |
| **Planner** | Steps y params | No | No | Compone el plan de research |
| **Evidence** | No | No | Lee last_event | Memoria estructurada reutilizable |
| **Formatter** | No | No | No | Plantilla → texto usuario |
| **Conversation Session** | Sticky / TTL | No | State store | Recuerda subjects, relation, evidence 10 min |

---

## FASE 3 — Medición real (proxies; sin instrumentar)

Mandato de auditoría: **no modificar código**. No se corrió instrumentación nueva de 100 conversaciones.

| Métrica | Fuente | Valor |
|---------|--------|-------|
| Huawei calls | v2452 | 35/44 |
| Local template | v2452 | 8/44 |
| Evidence reuse | smoke beta20 | 1 follow-up documentado |
| Hermes turn_types etiquetados en prod evidence | smoke | 1 × `attribute_of_last_event` |
| Tokens | — | **No registrados** |
| Cert200 | SUMMARY | 200/0; latency mean ~12.3 s |
| Agent50 | offline Hermes | 50/0 |
| Manual30 | API | 30/0 |
| Motor en same-day | code path | **0 llamadas** |

---

## FASE 4 — Eliminación controlada (simulación)

| Caso | OFF | Qué deja de funcionar | Qué sigue |
|------|-----|----------------------|-----------|
| **A Hermes** | DecisionEngine | Reuse corto; binding attribute follow-ups; meta routing limpio | Intent+SQL+Huawei en preguntas nuevas; más regresiones de continuidad |
| **B Huawei** | ModelArts | Tono `Conclusión`, latencia baja → sube; respuestas más “informe/plantilla” | Hechos correctos vía template; clarify/meta ya usan template |
| **C Evidence** | Aggregator/reuse | Follow-ups de loterías/posiciones sin reconsultar fallan o re-research | Cada turn re-ejecuta tools (más lento, más consistente con SQL) |
| **D Conversation Session** | active_investigation + sticky v4 | Continuidad 10 min; “esas fechas”, “los dos”, subject memory | Cada mensaje es isla; Manual30/Agent50 colapsan |
| **E Planner** | Dynamic/Research planner | Research multi-step y kinds; same_day plan tipado | Legacy `build_plan` + intent tool directo (más pobre) |

---

## FASE 7 — LLM (Huawei) en una frase

**Huawei resume y reescribe evidencia ya calculada; no decide el sistema.**

---

## FASE 8 — Veredicto (10 puntos)

1. **Arquitectura actual:** Pipeline híbrido determinista → SQL → (opcional) LLM rewrite, con sesión de investigación TTL y scope oficial de 7 loterías.

2. **Quién decide realmente:** `resolve_intent` + `QuestionClassifier` + `HermesDecisionEngine` + `DynamicResearchPlanner` (reglas). No el LLM.

3. **Qué aporta más inteligencia (operativa):** Intent/Planner + Query SQL (decidir + verdad).

4. **Qué aporta menos (en el path dominante coincidencias):** Motor Matemático (0% en ese path).

5. **Qué puede simplificarse:** Capas duplicadas de comprensión; legacy planner; naming Hermes; propagación `want_last_only`.

6. **Qué nunca debe tocarse (sin rediseño):** Motor matemático, Prompt Maestro v6, Huawei credentials, banco Cert200/semilla, histórico almacenado, OFFICIAL_LOTTERY_SCOPE como SSOT.

7. **¿Hermes aporta valor real?** **Sí** — continuidad y reuse (probado Agent50/Manual30/smoke). No es LLM.

8. **¿Huawei infrautilizado?** Como decisor: sí (a propósito). Como escritor: **no** (~80% turns v2452).

9. **¿Sobreingeniería?** **Leve-moderada** — muchas capas de “entender” solapadas; naming confuso; dos marcas “Hermes”.

10. **Recomendación final:**  
    **B) Arquitectura correcta pero simplificable.**  
    Antes de la “siguiente generación”, unificar comprensión (2 capas), renombrar Hermes LLM vs DecisionEngine, instrumentar `provider_used`/`hermes_decision` en Cert200 sin cambiar evaluadores, y mantener el contrato: **LLM no decide hechos ni tools**.

---

## Resultado final (letra)

### **B — Arquitectura correcta pero simplificable.**

No A (óptima): sobran capas y hay deuda de naming/medición.  
No C (sobreingenierizada grave): cada capa grande tiene rol demostrado en PASS de continuidad.  
No D (incorrecta): producción beta estable; suites verdes; verdad factual vive en SQL+reglas.
