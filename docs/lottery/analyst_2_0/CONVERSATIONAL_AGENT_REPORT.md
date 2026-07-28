# CONVERSATIONAL_AGENT_REPORT

**Suite:** CONVERSATIONAL_AGENT_50  
**Resultado:** **50 PASS / 0 FAIL**  
**Fecha:** 2026-07-28  
**Modo:** evaluador offline in-process (HermesDecision + Classifier + NaturalResponse + TTL)

## Cobertura

| Bloque | Turnos | Foco |
|--------|--------|------|
| A same_day 78+02 | 10 | loterías, posiciones, anteriores, filtros, explicación |
| B sujeto 35 | 5 | cuándo/dónde/primera/anteriores |
| C compare | 4 | comparación + follow-ups |
| D demostrativos | 8 | esa fecha, esas veces, ambos, los dos… |
| E tema/TTL | 8 | switch, vuelta, reset, expire 10m, renew |
| F natural/parcial | 15 | sin fallback genérico, sin jerga, atributos |

## Criterios verificados

- Conservación de sujetos compuestos en follow-ups de atributo
- `same_day` / evento no se pierde en «¿En cuáles loterías?»
- Reuso de evidencia cuando `last_event` tiene apariciones
- TTL 9 min activo / 10 min expira / renew
- Respuestas parciales con reintento (no «No pude completar…» genérico)
- Sin jerga interna (`same_day`, `metric`, `planner`…)

## Artefactos

- `CONVERSATIONAL_AGENT_50.json`
- `scripts/run_conversational_agent_50.py`
- `/tmp/lottery-agent50/SUMMARY.json`
