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

## Resultado UAT productivo (2026-07-23)

**Bake:** `jaios-app-backend:lottery-position-multi-20260723b` + frontend `lottery-position-multi-20260723`  
**Backup:** `/var/jaios/backups/pre_lottery-position-multi-20260723_*.dump`  
**Sesión:** `0280c178-244b-45f7-b88a-e46cc457b487`

| Paso | Resultado |
|------|-----------|
| Q1 compuesto | PASS — 35 Leidsa pos=1 (2026-05-06, `35 · 09 · 71`); 44 `all_except_previous` excl. Leidsa; top = Nacional 2026-07-15; sin frequency; `sc.tool=null` |
| Q2 cualquier posición | PASS — mismos números/alcances; `position=None` / «Cualquier posición»; 35 ahora 2026-07-01 en 2da |
| Q3 57 y 62 | PASS — reemplaza números; conserva layout + any_position |
| Prompt activo | v2 + cuerpo con «POSICIÓN PREDETERMINADA» |
| Sync compose | Solo cambió tag de imagen; env sync gates iguales |
| Nacional Día / Etapa C | Sin cambios de datos; Etapa C no iniciada |

**Commits:** `64a3163`, `f778958` on `feature/lottery-3.0`
