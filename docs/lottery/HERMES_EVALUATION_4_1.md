# Lottery IA 4.1 — Evaluación Hermes

## Pregunta
¿Debemos integrar `hermes-service` (u orquestación Hermes) en Lottery IA?

## Qué problema resolvería
- Orquestación genérica de agentes / memoria larga / tools dinámicas fuera de Lottery.
- Análisis documental (DGCP) y copilot de plataforma — ya cubiertos en otros módulos.

## ¿Duplicaría ConversationState?
**Sí.** Lottery ya tiene `ConversationState` tipado por sesión (`conversation_v4`) con slots, loterías activas, métricas y pending intent. Una memoria Hermes paralela crearía dos fuentes de verdad.

## ¿Duplicaría el planner?
**Sí.** Lottery tiene `build_plan()` acotado (máx 8 tools) sobre tools tipadas. Hermes como planner añadiría doble planificación y riesgo de SQL/tools no tipadas.

## ¿Aportaría memoria o tools?
- **Memoria:** no necesaria si el estado tipado funciona (UAT 4.0 A–D PASS).
- **Tools:** Lottery ya ejecuta SQLAlchemy tipado con permisos; Hermes no debe emitir SQL libre.

## Impacto operativo / latencia / riesgo / mantenimiento
| Factor | Evaluación |
|--------|------------|
| Latencia | + hop de red a hermes-service |
| Riesgo | Doble fallback, trazas ambiguas, fallos de import (ya visto en overlays) |
| Costo | Segundo contrato de prompts/memoria/tools |
| Beneficio demostrable en Lottery | **No** (síntesis ModelArts ya vía `HERMES_MODEL_API_*`) |

## Decisión 4.1
**No integrar Hermes como orquestador.** Mantener:
- Conversation Manager + planner tipado
- Huawei ModelArts solo para síntesis
- `hermes-service` fuera del path de `/lottery/chat`

Revisar solo si aparece un requisito de memoria cross-módulo demostrable con benchmark.
