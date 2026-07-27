# Analista IA — Fase A / A.1

Capa conversacional profesional sobre el motor Lottery IA.
**No modifica** Tabla 1, Tabla 2, Ranking, tiebreak, histórico matemático,
Hermes/Huawei, Prompt Maestro Oficial v5 ni otros módulos JAIOS.

## Arquitectura

```
Usuario → Understanding → IntentResolver → ConversationBrain
        → ResearchPlanner → ToolOrchestrator → LotteryToolExecutor (histórico)
        → ResponseFormatter → Síntesis (tokens desde Admin)
        → ResearchTrace
```

El **Research Engine** (`research_engine.py`) está preparado como stub
(`ENABLED = False`) para descubrimiento automático futuro. No está activo.

## Planner (`ResearchPlanner`)

- Modos: `quick` | `deep` | `auto` (desde Admin `research.mode` / `investigation_mode`)
- Profundidad: `light` | `standard` | `deep` (`analysis_depth`)
- Plan multi-paso reutiliza `LotteryToolName` existentes:
  ocurrencias, posiciones, loterías, frecuencias, coincidencias,
  comparación de períodos, D+1/D+3/D+7, casos equivalentes,
  confirmaciones cruzadas, ventanas before/after.
- Límites efectivos: `effective_max_tools()` / `effective_max_steps()`.

## Conversation Brain

Memoria conversacional estructurada:

- `active_numbers`, `active_pair`, `active_lotteries`, `active_filters`
- `focus_stack` (retorno a números previos)
- `current_primary_candidate`, `current_alternatives`
- `current_research` + último trace compacto
- No re-pregunta slots ya conocidos

## Intent Resolver

Resuelve referencias naturales sin perder contexto:

`ese`, `esa`, `esas veces`, `el anterior`, `el otro`, `aquellos`, `allí`,
`después`, `antes`, `solamente ahí`, `ese grupo`, `esa pareja`,
`compáralo con el otro`, `última vez`, `primera vez`, filtros de lotería/posición/año.

## Tool Orchestrator

Ejecuta solo herramientas autorizadas vía `LotteryToolExecutor`.
Respeta timeout, max_tools, max_steps y guardrails.
Nunca inventa datos ni muta ranking/motor.

## Modo Investigación

Cuando el plan es `deep` / multi-paso:

1. UI muestra **«Estoy investigando…»**
2. Se ejecuta el plan completo
3. Se responde solo al terminar (con evidencia + conclusión)

## Trace (`ResearchTrace`)

Cada turno registra:

- intención detectada
- contexto utilizado
- filtros aplicados
- herramientas y pasos
- evidencia encontrada
- duración
- snapshot de config Admin
- preview de respuesta

Expuesto en `runtime_trace.research_trace` (detalle completo con diagnostics).

## Configuración Admin → Runtime

| Parámetro | Runtime |
|-----------|---------|
| `max_tools` / `max_tools_per_research` | límite de tools |
| `max_steps` / `max_research_steps` | límite de pasos |
| `max_tokens` | síntesis LLM / Hermes |
| `timeout` / `timeout_seconds` | corte de investigación |
| `analysis_depth` | light/standard/deep |
| `investigation_mode` / `research.mode` | quick/deep/auto |

No deben existir knobs Admin ignorados por el chat.

## Validaciones obligatorias

- Motor: `35+14 → 54`, `39+58 → 94`
- Ranking / Tabla 1 / Tabla 2 intactos
- Prompt Maestro v5 activo e intacto
- Alembic producción: **061** (no aplicar 062)
- Deploy selectivo Lottery únicamente
