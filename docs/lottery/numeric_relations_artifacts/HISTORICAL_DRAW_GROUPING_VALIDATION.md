# Validación previa obligatoria del histórico (draw_id)

Fecha: 2026-07-23  
Ambiente auditado: `jaios-lottery-pg-dev` / DB `jaios_lottery_dev`  
Volumen: 91 927 sorteos · 388 776 números · 50 loterías

## Veredicto

**APTO para Fases C+D.** El histórico permite reconstruir de forma inequívoca todos los números de un mismo sorteo mediante `lottery_draws.id` (`draw_id`).

La API (`db_history.load_occurrences_from_db`), el motor y el chat **agrupan por `draw_id`**, no por `(lottery_id, draw_date)`.

No se modifica el sincronizador.

---

## Modelo real

### `jaios.lottery_draws`
| Campo | Rol |
|-------|-----|
| `id` (UUID PK) | Identificador único y estable del sorteo |
| `lottery_id` | FK → lotería |
| `draw_date` | Fecha |
| `draw_time` | Hora (nullable) |
| `game_name`, `source_reference` | Desambiguación natural |

### `jaios.lottery_draw_numbers`
| Campo | Rol |
|-------|-----|
| `draw_id` | FK CASCADE → `lottery_draws.id` |
| `position`, `position_label` | Posición |
| `number_value`, `number_raw` | Número (texto, preserva ceros) |

Unicidad números: `uq_lottery_draw_numbers_draw_pos_type (draw_id, position, number_type)`.

---

## Demostración requerida

### 1. Sorteo exacto donde salió N + todos los números del mismo sorteo

Ejemplo real — Quiniela Leidsa, `N=26`:

| Campo | Valor |
|-------|--------|
| `draw_id` | `a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad` |
| Lotería | Quiniela Leidsa |
| Fecha | 2026-06-23 |
| Hora | `NULL` |
| Hit | posición 3 → `26` |

Números del **mismo** `draw_id`:

| pos | label | value |
|-----|-------|-------|
| 1 | 1ro | 29 |
| 2 | 2do | 01 |
| 3 | 3ro | 26 |

### 2. Misma fecha+lotería ≠ mismo sorteo (obligatorio)

Casos `(lottery_id, draw_date)` con **más de un** `draw_id`: **43**.

De ellos:
- **24** tienen **conjuntos de números distintos** → agrupar por fecha mezclaría sorteos reales distintos.
- **19** tienen el mismo set de números (duplicados por `source_reference` distinto; p.ej. Power Ball 2025-08-27).

Ejemplo Power Ball 2025-08-27 (misma fecha, `draw_time` NULL, **dos** `draw_id`):

| draw_id | source_reference | números |
|---------|------------------|---------|
| `9bab8d2d-…` | 198165 | 09,12,22,41,61,25 |
| `b524a604-…` | 204050 | 09,12,22,41,61,25 |

Conclusión: la identidad del sorteo es **`draw_id`**, no fecha+lotería ni siquiera fecha+hora cuando ambas horas son NULL.

### 3. Integridad referencial

| Check | Resultado |
|-------|-----------|
| Números huérfanos (`draw_id` sin draw) | **0** |
| Draws sin números | **0** |

---

## Cómo lo usa el motor (C+D)

En `db_history.py`:

1. `number_occurrences` une `LotteryDraw` ⋈ `LotteryDrawNumber` por `draw_id`.
2. Deduplica ocurrencias con clave `str(draw.id)`.
3. Recarga **todos** los números con `WHERE LotteryDrawNumber.draw_id == draw.id`.
4. Emite `HistoricalOccurrence.draw_id`, `draw_date`, `draw_time`, posiciones.

El scoring / dedupe del análisis incluye `draw_id` en la clave (`lottery_id|draw_id|position|neighbor|companion`).

---

## Riesgo residual (no bloquea agrupación)

Duplicados de sync (mismo contenido, distinto `source_reference`) generan **dos** ocurrencias históricas con el mismo patrón de números. Eso puede **duplicar puntos** si ambos se incluyen en el límite K.

- **No** es fallo de agrupación por `draw_id`.
- **No** se corrige aquí (sync no autorizado).
- Mitigación futura (con autorización): dedupe operativo por `content_hash` o política de fuente primaria.

---

## Pruebas añadidas

`backend/tests/test_lottery_numeric_relations_draw_grouping.py`

- Misma fecha+lotería, dos `draw_id` → sets de números separados.
- Análisis no cruza vecinos entre `draw_id` distintos.
- Evidencia estática de que el adaptador filtra por `draw_id`.

---

## Confirmación Fases C+D

| Criterio | Estado |
|----------|--------|
| Recuperar sorteo exacto de N | Sí (`draw_id`) |
| Todos los números del mismo sorteo | Sí (FK `draw_id`) |
| Lotería / fecha / hora / posición | Sí |
| ID estable | `lottery_draws.id` UUID |
| Sin inventar asociaciones | Sí |
| Sync no tocado | Sí |

**Fases C+D pueden considerarse completas respecto a agrupación histórica real.**
