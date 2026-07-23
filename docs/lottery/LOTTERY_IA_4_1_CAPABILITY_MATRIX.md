# Lottery IA 4.1 — Matriz de capacidades

Fecha: 2026-07-23  
Prompt base: `lottery_assistant_system_v1` (v1) / candidate `v2`  
Pipeline: ConversationState → understand → planner → typed tools → síntesis ModelArts

Leyenda: **FULL** | **PARTIAL** | **NONE**

| Categoría | Intent | Entidades | Tools | Soporte | Respuesta esperada | Limitaciones |
|-----------|--------|-----------|-------|---------|-------------------|--------------|
| Resultados por fecha | `result_by_date` | lottery, date | `GET_RESULT_BY_DATE` | FULL | Números del sorteo | Sin game ambiguo |
| Anteriores (días) | `draw_sequence` | lottery, date, days | `GET_PREVIOUS_DAYS` | FULL | Días calendario | ≠ sorteos |
| Anteriores (sorteos) | `draw_sequence` | lottery, date, count | `GET_PREVIOUS_DRAWS` | FULL | N sorteos previos | Requiere fecha base |
| Siguientes (días) | `draw_sequence` | lottery, date, days | `GET_FOLLOWING_DAYS` | FULL | Días calendario | Idem |
| Siguientes (sorteos) | `draw_sequence` | lottery, date, count | `GET_FOLLOWING_DRAWS` | FULL | N sorteos | Idem |
| Última aparición | `last_occurrence` | number, lottery\|all | `GET_LAST_OCCURRENCE` (+ multi) | FULL | Fecha + posición + muestra | Scope all limitado a 8 |
| Primera aparición | `first_occurrence` | number, lottery | `GET_NUMBER_OCCURRENCES` ASC | PARTIAL | Primer hit en ASC | Sin tool dedicada |
| Historial de número | `number_history` | number, lottery | `GET_NUMBER_OCCURRENCES` | FULL | Conteos + fechas | Paginado |
| Frecuencias | `frequency` | lottery, period | `CALCULATE_FREQUENCIES` | FULL | Top frecuencias | Requiere lotería/período |
| Calientes | `hot_numbers` | lottery, window | `GET_HOT_COLD` focus=hot | FULL | Frecuencia relativa | Ventana N sorteos |
| Fríos (frecuencia) | `cold_numbers` | lottery, window | `GET_HOT_COLD` cold_frequency | FULL | Baja frecuencia | No confundir con atrasado |
| Atrasados (intervalo) | `overdue_numbers` | lottery, window | `GET_HOT_COLD` / `GET_OVERDUE` | FULL | Días sin aparecer | Threshold configurable |
| Repeticiones | `repeated_numbers` | lottery, range | `FIND_REPETITIONS` | FULL | Números ×count | No combinaciones |
| Coincidencias | `cross_lottery_matches` | lotteries, range | `GET_COINCIDENCES` | PARTIAL | Matches same-date | Intent regex limitado |
| Comparaciones loterías | `compare_lotteries` | lotteries | `COMPARE_LOTTERIES` | FULL | Tabla comparativa | — |
| Comparar número períodos | `compare_number_periods` | number, lottery, periods | `COMPARE_NUMBER_PERIODS` | FULL (4.1) | Freq relativa A vs B | Años calendario |
| Comparar número loterías | `compare_numbers` | number, lotteries | multi last / COMPARE | FULL | Fechas por lotería | Máx 8 |
| Cobertura | `data_coverage` | — | `GET_COVERAGE` | FULL | Conteos globales | — |
| Calidad | `data_quality` | lottery | `GET_DATA_QUALITY` | FULL | Dupes/vacíos | Admin-ish perms |
| Completitud | `data_completeness` | lottery? | `GET_DATA_COMPLETENESS` | FULL (4.1) | Completeness score | — |
| Faltantes hoy | `missing_results` | — | `GET_MISSING_TODAY` | FULL | Sync-enabled missing | Solo sync on |
| Expected vs received | `expected_vs_received` | — | `GET_EXPECTED_VS_RECEIVED` | PARTIAL (4.1) | Hoy esperado/recibido | Sin calendario futuro |
| Sincronización | `sync_status` | — | `GET_SYNC_STATUS` | FULL | Flags + trio AW | — |
| Fuentes | `source_health` | — | `GET_SOURCE_HEALTH` | FULL | Health rows | — |
| Por posición | `position_analysis` | lottery, number? | `GET_POSITION_DISTRIBUTION` | FULL (4.1) | Dist por posición | Ventana requerida |
| Por período / mes | `monthly_trend` | lottery | `GET_MONTHLY_TREND` | FULL (4.1) | Serie mensual | Últimos 12m default |
| Resumen lotería | `lottery_summary` | lottery | `GET_LOTTERY_SUMMARY` | FULL (4.1) | Snapshot operativo | — |
| Última fecha disponible | `latest_date` | lottery? | `GET_LATEST_AVAILABLE_DATE` | FULL (4.1) | last_draw_date | — |
| Explicar método | `explain_metric` | metric? | `EXPLAIN_ANALYSIS_METHOD` | FULL (4.1) | Definiciones | — |
| Gaps / intervalos | `gap_stats` | number, lottery | `GET_INTERVAL_STATISTICS` | PARTIAL | avg/min/max gaps | Sin stdev en tool |
| Rachas (streaks) | — | — | — | NONE | — | Gap 4.1 |
| Combinaciones repetidas | — | — | — | NONE | — | Gap 4.1 |
| Predicción | `unsupported` | — | refuse | FULL (guardrail) | Rechazo | — |
| Seguimiento contextual | `follow_up` | state | varios | FULL | Slot fill | Pronombres limitados |

## Gaps prioritarios post-4.1
1. Streaks / combinaciones — no implementados (NONE).
2. Expected vs received sin calendario de sorteos futuros.
3. LLM open-intent classification aún no sustituye regex (híbrido rules-first).
4. Coincidencias “ayer” requieren fecha relativa robusta.

## Confirmaciones
- Etapa C: no iniciada.
- Nacional Día: sin cambios de sync/mapping.
- Hermes: no orquestador (ver `HERMES_EVALUATION_4_1.md`).
