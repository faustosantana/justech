# Lottery IA P1 — posición primaria + multi-query (2026-07-23)

## Causa del intent incorrecto

1. «¿Cuándo salió…?» no se enrutaba de forma fiable a `GET_LAST_OCCURRENCE` (colisionaba con rutas de fecha/próxima aparición).
2. No existía parser de consultas compuestas (dos números / dos alcances de lotería).
3. Sin posición implícita → el runtime no filtraba por primera posición.
4. El renderer mostraba JSON + nombre interno de tool (`lottery_calculate_frequencies`), amplificando el error percibido.

## Cambios

| # | Ítem | Estado |
|---|------|--------|
| 1 | Causa intent | Documentada arriba |
| 2 | Regla posición = 1ro por defecto | `compound_occurrence.resolve_effective_position` + prefs |
| 3 | Preferencia configurable | `default_number_position_scope`, `default_primary_position` (Justech: first_position) |
| 4 | Parser compuesto | `parse_compound_last_occurrence` → `multi_last_occurrence` |
| 5 | «otra lotería» | `all_except_previous` + excluded |
| 6 | Tools | `GET_LAST_OCCURRENCE` (+ multi executor); **no** frequencies |
| 7 | UAT | Pendiente post-deploy |
| 8 | Benchmark | `tests/test_compound_last_occurrence.py` (10 passed) |
| 9 | JSON oculto | `_public_structured` + renderer sin JSON; tool_trace solo developer_mode |
| 10–11 | Prompt v2 | Reglas posición/compuesto/otra; hotpatch body DB sin cambiar versión activa |
| 12 | Commits | Ver git |
| 13–14 | Imágenes / Deploy | Tag bake `lottery-position-multi-20260723` |
| 15 | Sync auto-write | **No tocado** |
| 16 | Nacional Día | **No tocado** |
| 17 | Etapa C | **No iniciada** |

## Query UAT

```
¿Cuándo salió el 35 en Leidsa y el 44 en cualquier otra lotería?
```

Esperado: intent `multi_last_occurrence`, position=1, tools last_occurrence (no frequency), tabla 44 excluyendo Leidsa, sin JSON.

Follow-ups: «¿Y en cualquier posición?» → any_position; «Ahora hazlo con el 57 y el 62.» → mismos alcances, nuevos números.
