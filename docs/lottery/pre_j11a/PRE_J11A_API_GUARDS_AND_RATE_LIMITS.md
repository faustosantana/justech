# Pre-J11A — API Guards y Rate Limits (TD-003 / TD-006)

## Endpoints protegidos

| Router | Prefijo | Protecciones |
|--------|---------|--------------|
| `lottery_nr_historical.py` | `/lottery/admin/numeric-relations/history/*` | Rate limit + date/scope/page/numbers bounds |
| `lottery_numeric_relations.py` | `/lottery/admin/numeric-relations/*` (incl. `/analyze`) | Rate limit + max lotteries en analyze |

## Valores (Settings / env)

| Setting | Env | Default | Justificación |
|---------|-----|---------|---------------|
| `lottery_nr_rate_limit_per_minute` | `LOTTERY_NR_RATE_LIMIT_PER_MINUTE` | **90** | FE hace varias llamadas por pantalla; 90/min/usuario no bloquea uso normal |
| `lottery_nr_max_range_days` | `LOTTERY_NR_MAX_RANGE_DAYS` | **15000** (~41 años) | Cubre histórico real; evita rangos abiertos patológicos cuando hay fechas |
| `lottery_nr_max_lotteries_per_request` | | **7** | FEATURED_SEVEN |
| `lottery_nr_max_numbers_list` | | **20** | Comparaciones/listas |
| `lottery_nr_max_page_size` | | **100** | Paginación |
| `lottery_nr_default_page_size` | | **20** | Default UI |
| `lottery_nr_request_timeout_seconds` | | **45** | Reservado / documentado para runtime futuro |

## Comportamiento de fechas

- `date_from > date_to` → 400
- Rango > max days → 400
- Solo `date_to` sin `date_from` → 400
- Ambos `None` → permitido (histórico completo del universo activo, acotado por FEATURED_SEVEN + rate limit) — **no cambia metodología**

## Rate limiting

- Implementación: sliding window in-process (`app/lottery/api_guards.py`)
- Clave: `user_id + route`
- Respuesta 429 con `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- Multi-worker Redis: diferido a J-11A+ (misma interfaz)

## Errores

Mensajes en español, HTTP 400/429 claros.

## Pruebas

`backend/tests/test_pre_j11a_api_guards.py`
