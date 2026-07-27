# Analista IA + Research Engine — Fase A / A.1 / B

Capa conversacional e investigación inteligente sobre el motor Lottery IA.
**No modifica** Tabla 1, Tabla 2, Ranking, tiebreak, histórico matemático,
Hermes/Huawei, Prompt Maestro Oficial v5 ni otros módulos JAIOS.

## Arquitectura (Fase B)

```
Usuario
  → Understanding + IntentResolver + ConversationBrain
  → QuestionClassifier
  → ResearchEngine (planes dinámicos)
  → DynamicResearchPlanner
  → ToolOrchestrator (+ cache / dedupe)
  → LotteryToolExecutor (histórico existente)
  → EvidenceEngine + Confidence (Alta/Media/Baja)
  → format_research_response
  → ResearchTrace / research_audit
```

Discovery Engine (`discovery_engine.py`) permanece **deshabilitado**
(`ENABLED=False`) para una fase futura.

## Research Engine v2.0

- Clasifica preguntas abiertas (`what_usually_happens_after`, comparaciones,
  case search, temporal, confirmaciones, etc.).
- Construye estrategia **antes** de responder.
- Ejecuta multi-tool / multi-etapa acotado por Admin (`max_tools`, `max_steps`,
  `timeout`, `analysis_depth`, `investigation_mode`).
- Nunca inventa datos ni muta el motor.

## Planner dinámico

`DynamicResearchPlanner` compone pasos en runtime (sin flujos fijos únicos):
ocurrencias → posiciones → frecuencias → D+1/3/7/15/30 → confirmaciones →
equivalentes → comparaciones.

## Módulos

| Módulo | Rol |
|--------|-----|
| `question_classifier` | Detecta kind de investigación |
| `dynamic_planner` | Plan multi-paso |
| `temporal_analysis` | Antes/después / D+N / períodos |
| `case_search` | Equivalentes / similares / parciales |
| `historical_comparator` | 54 vs 94, loterías, posiciones, años |
| `evidence_engine` | Evidencia + confianza cualitativa |
| `research_cache` | Reuso / dedupe de tools |
| `discovery_engine` | Stub futuro |

## Respuesta profesional

Resumen Ejecutivo → Resultado → Evidencias → Comparaciones → Cronología →
Conclusión → Limitaciones → Sugerencias relacionadas.

## Fase C — Analyst Experience (v2.1.0)

Solo presentación. **No modifica** Research Engine, Planner ni Conversation Brain.

- Estructura: Resumen Ejecutivo → Hallazgos → HECHOS → ANÁLISIS → OBSERVACIONES → Evidencias → Limitaciones → Próximas investigaciones
- Separación estricta hechos / análisis / observaciones / limitaciones
- ASCII bars (`render_bar` / `render_ranking_bars`)
- Modos: `short` | `full` | `report` | `delta` (seguimiento sin repetir informe)
- Comparaciones con Similitudes / Diferencias / Conclusiones

## Fase D — Discovery Engine (v2.2.0)

Hallazgos **observacionales** automáticos sobre evidencia histórica.

- Tipos: frecuencia, secuencias, repeticiones, confirmaciones, cambios año/lotería/posición, equivalentes, únicos
- Niveles: Muy Alto / Alto / Medio / Bajo / Insuficiente
- Validador descarta evidencia débil o lenguaje predictivo
- Historial en `discovery_store` (no escribe sorteos ni ranking)
- API: `POST /lottery/ia/discovery/run`, `GET /lottery/ia/discovery/history`

**No modifica** Research Engine, Planner ni Conversation Brain.

## Validaciones

- Motor: `35+14 → 54`, `39+58 → 94`
- Prompt Maestro v5 intacto
- Alembic producción: **061**
- Deploy selectivo Lottery únicamente
