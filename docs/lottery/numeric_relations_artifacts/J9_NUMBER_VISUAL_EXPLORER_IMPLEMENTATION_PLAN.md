# J-9 — Historial del Número (Number Visual Explorer) — Plan de implementación

**Rama:** `feature/nr-number-visual-explorer-j9`  
**Base:** `9aefe9a` (J-6 close)  
**Commits J-1→J-6 verificados:** `232aa65` `fbb24c0` `ff73895` `43a8aac` `3b4e07a` `9aefe9a`  
**Producción:** no tocar  
**Fórmulas / Tabla 1 / Tabla 2 / histórico / `/analyze` v1:** no modificar

---

## 1. Inventario de lo ya disponible (J-1→J-6)

### Dominio

| Capacidad | Módulo | Estado |
|-----------|--------|--------|
| mother_code = N, candidatos T1 | `conditions.py`, `catalog.py` | OK |
| Confirmadores T2 + ventanas | `confirmation.py` | OK |
| Posterior / ciclos / censura | `posterior.py`, `rates.py` | OK (horizonte param.) |
| Atómicos N-C-V + combinaciones | `conditions.py`, `aggregates.py` | OK |
| Universo draw_id | `universe.py`, `db_universe.py` | OK |
| draws_after(k) | `InMemoryDrawUniverse.draws_after` | OK — base para 7 sorteos |
| Explicación lenguaje simple | — | **GAP** (borrador J-7 no en base) |

### APIs `/lottery/admin/numeric-relations/history/*`

| Endpoint | Sirve para J-9 | Gap |
|----------|----------------|-----|
| POST `/conditions/search` | Condiciones + ranking + stats | No perfil agregado del número |
| POST `/posterior/summary` | Tasas/ciclos | OK parcial |
| POST `/combinations` / `/matrix` | Combinaciones | OK |
| POST `/patterns/detail` | Patrón N-C-V | OK |
| POST `/evidence/by-draw` | Por ancla | OK |
| POST `/cycles` | Ciclos | OK |
| POST `/compare` | Compara candidatos/confirmadores | **No** compara dos números observados |

### UI Control Center

| Pantalla | Estado |
|----------|--------|
| Histórico / Matriz / Patrón / Comparador | Técnicos (J-4) |
| Historial del Número (expediente) | **GAP** |
| Árbol / por qué / 7 sorteos / reproductor | **GAP** |

---

## 2. Gaps esenciales J-9 (solo lo necesario)

1. **Servicio `number_profile`** — apariciones del número, distribución lotería/año/mes/día, tasa condición positiva/negativa, sin recalcular fórmulas.
2. **Ocurrencias paginadas** — lista natural + filtros (año, lotería, +/- condición, candidato, confirmador).
3. **Expediente por `draw_id`** — veredicto Sí/No/Parcial + árbol + candidatos + “por qué se fortaleció”.
4. **Next draws** — `count=7` por secuencia real `draw_id`; modo opcional CALENDAR_DAYS separado.
5. **Compare numbers** — 35 vs 40 reutilizando profiles.
6. **Presentación** — veredicto, narrativa, árbol, tarjetas, gráficas data (sin inventar números).
7. **UI “Historial del Número”** — experiencia guiada móvil-friendly.
8. **E2E 50/50** DEV DB.

**No gaps de metodología:** cálculos J-1→J-6 se reutilizan; J-9 orquesta y presenta.

---

## 3. Diseño de APIs nuevas (mínimas)

Prefijo: `/lottery/admin/numeric-relations/history`

| Método | Path | Rol |
|--------|------|-----|
| POST | `/numbers/profile` | Resumen + charts data + condición global |
| POST | `/numbers/occurrences` | Página de apariciones + filtros |
| POST | `/numbers/occurrences/detail` | Expediente de una aparición |
| POST | `/numbers/occurrences/next-draws` | 7 sorteos (o N) posteriores |
| POST | `/numbers/compare` | Comparar number_a vs number_b |
| POST | `/numbers/why-strengthened` | Explicación determinista por candidato |

Todas incluyen: `effective_parameters`, `methodology_version`, sample/censura, `trace_id`.

Reutilizan: `load_universe_from_db`, `HistoricalRelationsService`, `build_events_for_anchor`, `compute_posterior`, `rates_payload`, catálogo T1/T2.

---

## 4. Subfases y commits

| Subfase | Entrega | Commit |
|---------|---------|--------|
| J-9.0 | Este plan | docs |
| J-9.1 | `number_profile` + occurrences list + UI buscador/resumen | feat |
| J-9.2 | detalle aparición + árbol + por qué + tarjetas | feat |
| J-9.3 | next-draws 7 + reproductor | feat |
| J-9.4 | gráficas + lenguaje + accesibilidad | feat |
| J-9.5 | filtros avanzados + comparador | feat |
| J-9.6 | E2E 50/50 + capturas + entrega | docs/test |

---

## 5. Riesgos

- Universo grande en memoria para 2015–hoy → paginar y filtrar por fechas/loterías.
- 7 sorteos ≠ 7 días → UI distingue DRAWS vs CALENDAR_DAYS.
- Solape UI J-4 técnico vs expediente → menú “Historial del Número” como entrada principal.

---

## 6. Criterio de no-ambigüedad metodológica

Confirmado sin decisión pendiente:

- mother_code = observed_number  
- fuerza → candidato T1; confirmador solo evidencia  
- identidad draw_id  
- 7 sorteos = `draws_after(..., k=7)`  

**Producción intacta. No desplegar.**
