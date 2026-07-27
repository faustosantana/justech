# Re-auditoría conversacional — v2.4.4

**Fecha:** 2026-07-27T23:28Z–23:37Z  
**Imagen:** `jaios-app-backend:lottery-ia-ux-v2.4.4`  
**Commit:** `3a1e7b4`  
**Mismas preguntas / mismos bloques que auditoría v2.4.3**  
**Resultado:** **BLOQUEADO** (no 44/44 PASS)

## Conversation IDs (nueva corrida)

| Bloque | ID |
|--------|-----|
| A | `336e9f92-73f7-4b8a-8dbf-69318b68a8b6` |
| B | `b9640f26-02d4-4ee2-ba16-1e63647b5954` |
| C | `91cbb121-f668-4277-a219-2e3a4d9e5317` |
| D | `8db1170b-9fa5-46cb-adf7-363d0547ceab` |
| E | `0df99842-51eb-4830-8dd7-e9bb97f68a8b` |
| F | `8c789195-437f-4285-9355-f94a6cf3f617` |
| G | `8ac7417f-ef7f-45de-8d0c-e247c5d6a39d` |
| H | `639c8d74-cbb9-4879-ab21-ac1e44c7a6b5` |

Raw: `raw_results_v244.json`

## Resumen cuantitativo (auditoría humana Cursor)

| Métrica | v2.4.3 | v2.4.4 |
|---------|--------|--------|
| Turnos | 44 | 44 |
| PASS (estimado auditor) | 12 | ~28–32 |
| FAIL (estimado auditor) | 32 | ~12–16 |
| Exactitud factual | ~38% | ~75% (aún <100%) |
| Continuidad | ~34% | ~70% |
| Naturalidad | 3.4 | ~4.0 |
| Interpretación | 2.8 | ~3.6 |
| Jerga interna visible | sí | casi 0 en prosa |
| Contradicciones | ≥6 | ≥3 |
| HTTP 500 | sí | 0 (soft-fail) |

**Umbral 44 PASS / 0 FAIL / factual 100% → no alcanzado → BLOQUEADO.**

## FAIL corregidos vs v2.4.3 (origen)

- A.7 sujeto 04→**35** + items reales
- E.1 sujeto 05→**54** + items reales  
- A.5/C.6 jerga `last_n_occurrences` → etiquetas humanas + listado de apariciones
- A.6 «dos anteriores» ejecuta last_n con offset (ya no pide el número)
- B.1 Nacional+primera completa (alias Nacional→source 4)
- H.4 «me refiero al 97» reconsulta última aparición
- Soft-fail en chat (sin HTTP 500 al cliente)

## FAIL pendientes (bloquean)

1. **A.2 / H.1 — última del 22:** responde 2026-06-04 Nacional 3ª; repo default scope tiene **2026-07-20 Gana Más 2ª**. Cadena: merge last_n / resolución alias Gana Más incompleta para ese número en el paso primario.
2. **C.1–C.4 — same_day 55+24:** «No pude completar» (tool same_day no entrega éxito estable).
3. **B.2 — hereda Nacional:** últimas 3 del 35 salen all-lotteries pos1 (Real/Nacional/Real) en vez de solo Nacional.
4. **B.3 — aclaración innecesaria** al pedir todas las posiciones.
5. **D.2–D.4 — continuidad de comparación** 54/94 (pide número / no aplica año-posición limpio).
6. **E.2 — ventana D+1..D+3:** soft-fail sin anclas/calendario.
7. **F.2 — El 44:** fecha inventada/alias La Primera Tarde (2025-04-18) vs última real ~2026-07-20 Leidsa.
8. **H.5–H.9 — meta-continuación** sigue disculpándose por 22 vs 97 en lugar de re-servir el dato del 97.

## Causas raíz restantes (agrupadas)

| Grupo | Primera capa |
|-------|----------------|
| Último 22 incorrecto | tool last_n merge / alias «Gana Más» no aporta fila → mejor ancla incorrecta |
| Same-day incompleto | tool `same_day_number_coincidences` + orchestrator empty lead |
| Herencia Nacional en last_n pos1 | classifier/planner inheritance incompleta en follow-up B.2 |
| Compare follow-ups | estado `compare_active` / clarificación gana sobre re-ejecución |
| After-window | contrato date/lottery por ancla de items |
| Pending «El 44.» | resume aún puede caer en alias ambiguo / síntesis |
| Meta H | replay de corrección no ancla el hilo a «última del sujeto activo» |

## Producción / Hermes

- Backend: `jaios-app-backend:lottery-ia-ux-v2.4.4` healthy  
- Hermes: healthy (sin cambios de proveedor)  
- Backup: `/var/jaios/backups/pre_lottery-ia-ux-v2.4.4_20260727_231613.dump`
