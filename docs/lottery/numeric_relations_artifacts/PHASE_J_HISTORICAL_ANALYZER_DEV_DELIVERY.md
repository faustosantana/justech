# J-1…J-6 — Analizador Histórico T1↔T2 — Entrega DEV

**Rama:** `feature/nr-historical-analyzer-j1-j6`  
**Fecha:** 2026-07-24  
**Producción:** **INTACTA** (sin despliegue)

---

## 1. Metodología intacta

| Invariante | Estado |
|------------|--------|
| Fórmulas T1/T2 | Sin cambios (regresión table1/table2 PASS) |
| Rango 1..100 | Intactos |
| Códigos / grupos | Reutiliza `build_catalog()` |
| `mother_code = observed_number` | Confirmado |
| Fortalece candidato T1, no confirmador T2 | `score_delta=+1` → `candidate_strengthened` |
| Identidad = `draw_id` | Sin fusión por fecha |
| IA no inventa estadísticas | Tools solo exponen payloads calculados; `ai_conclusions=null` en APIs |

---

## 2. Modelo de datos final (dominio)

- `ConfirmationWindowConfig` + modos SAME_DRAW / SAME_DATE / SAME_SESSION / HOURS_AFTER / NEXT_DRAW_PER_CONFIRMING_LOTTERY / NEXT_K_DRAWS  
- `LotteryScope` — primary / confirming / follow-up (default follow = primary, visible)  
- `AtomicRelationEvent` — Nivel A: N→C→V  
- `CombinationRelationEvent` — Nivel B: N→C→{V} + `atomic_event_ids`  
- `PosteriorOutcome` — horizontes 1/2/3/5/10 + `censored` / `censored_horizons`  
- `HorizonRate` — numerador, denominador, %, muestra, censurados, tier  
- `CycleStats` — min/max/mean/median/stdev/percentiles/distribución  

Versión: `nr-historical-relations-j1.0.0`

---

## 3. Servicios creados

`backend/app/lottery/numeric_relations/historical/`

| Módulo | Rol |
|--------|-----|
| `confirmation.py` | Ventanas de confirmación |
| `posterior.py` | Seguimiento + censura |
| `conditions.py` | Emisión eventos A/B |
| `rates.py` | Tasas / ciclos |
| `aggregates.py` | Patrones + matriz + pares/tríos |
| `service.py` | Fachada búsqueda |
| `db_universe.py` | Carga solo lectura desde PG |
| `tools_bridge.py` | Bridge tools IA |

---

## 4. APIs (v1 `/analyze` intacto)

Prefijo: `/api/v1/lottery/admin/numeric-relations/history/`

1. `POST /conditions/search`  
2. `POST /posterior/summary`  
3. `POST /combinations`  
4. `POST /matrix`  
5. `POST /patterns/detail`  
6. `POST /evidence/by-draw`  
7. `POST /cycles`  
8. `POST /compare`  

---

## 5. Pantallas Control Center

- `/motor/historico`  
- `/motor/combinaciones`  
- `/motor/patron`  
- `/motor/comparador`  

Formulario con primary / confirming / follow-up explícitos y tasas con numerador/denominador.

---

## 6. Tools IA

- `lottery_historical_relation_conditions`  
- `lottery_candidate_response_summary`  
- `lottery_confirmer_combinations`  
- `lottery_relation_pattern_detail`  
- `lottery_compare_historical_patterns`  

---

## 7–11. Ejemplos / estadísticas / censura / matriz / patrón

Cubiertos por tests controlados J-1/J-2 (catálogo pedagógico 34→{1..5}, candidato 4, confirmadores 6/9/11):

- Múltiples confirmadores → score 3  
- Posterior A1 offset=3; A2 censurado horizon 10  
- Tasas excluyen censurados del denominador  
- Matriz C×V con numerador/denominador  
- Subconjunto {6,9} cuenta contención  

---

## 12. Pruebas

```
22 passed
tests/test_lottery_nr_historical_j1.py
tests/test_lottery_nr_historical_j2.py
tests/test_lottery_nr_historical_j3_schemas.py
tests/test_lottery_nr_historical_j5_tools.py
tests/test_lottery_numeric_relations_table1.py
tests/test_lottery_numeric_relations_table2.py
```

Pendiente en stack DEV con DB real: E2E API/UI/chat/permisos/rendimiento (requiere instancia DEV con histórico cargado).

---

## 13. Rendimiento

- Carga acotada `max_draws=20000` por consulta  
- Agregados en memoria sobre universo filtrado por fechas  
- Riesgo: rangos muy amplios multi-lotería → latencia; mitigar con `date_from`/`date_to` y filtros candidato/confirmador  

---

## 14. Commits

| Fase | Commit |
|------|--------|
| J-1 | `232aa65` |
| J-2 | `fbb24c0` |
| J-3 | `ff73895` |
| J-4 | `43a8aac` |
| J-5 | (este + docs J-6) |

---

## 15. Capturas

No generadas en esta corrida (sin despliegue FE DEV). Reproducir en DEV con las 4 rutas nuevas.

---

## 16. Riesgos

1. `load_universe_from_db` en rangos largos puede ser pesado.  
2. Intent histórico puede solaparse con analyze NR; se prioriza histórico ante señales de ciclo/tasa/combinación.  
3. Router local puede depender de módulos bootstrap no commiteados en otras áreas — el router ya incluía esos imports previamente.  

---

## 17. Pendientes (antes de Prod)

- [ ] Migración opcional de tablas materializadas (hoy on-demand)  
- [ ] E2E DEV con DB + Playwright  
- [ ] Benchmark latencia Leidsa 2015–hoy  
- [ ] Capturas UI  
- [ ] Revisión de permisos admin en endpoints `/history/*`  
- [ ] GO explícito de despliegue  

---

## 18. Producción intacta

Confirmado: **no se desplegó**, no se alteró sync, no se mutó `lottery_draws`.

---

## 19. Veredicto

### GO CONDICIONADO

Listo para validación en **DEV** y revisión.  
**No desplegar a Producción** hasta E2E DEV + autorización expresa.
