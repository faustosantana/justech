"""Guards de API NR — rate limit, rangos de fecha y tamaños (Pre-J11A TD-003/006).

No altera fórmulas ni metodología. Solo limita abuso y cargas accidentales.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from typing import Any, Deque
from uuid import UUID

from fastapi import HTTPException, Request, Response

from app.config import settings


class RateLimitExceeded(HTTPException):
    def __init__(self, *, retry_after: int, detail: str):
        super().__init__(
            status_code=429,
            detail=detail,
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.lottery_nr_rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )


class _SlidingWindowLimiter:
    """Limiter in-process por clave (usuario+ruta). Suficiente para DEV/single-worker.

    Producción multi-worker deberá respaldarse con Redis en J-11A+; la interfaz permanece.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> tuple[int, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                retry = int(window_seconds - (now - q[0])) + 1 if q else window_seconds
                raise RateLimitExceeded(
                    retry_after=max(1, retry),
                    detail=(
                        f"Límite de solicitudes alcanzado ({limit}/min). "
                        f"Reintente en {max(1, retry)} s."
                    ),
                )
            q.append(now)
            remaining = max(0, limit - len(q))
            return limit, remaining


_LIMITER = _SlidingWindowLimiter()


def enforce_nr_rate_limit(
    *,
    user_id: UUID | str | None,
    route: str,
    response: Response | None = None,
    limit_per_minute: int | None = None,
) -> None:
    limit = int(
        limit_per_minute
        if limit_per_minute is not None
        else settings.lottery_nr_rate_limit_per_minute
    )
    if limit <= 0:
        return
    key = f"nr:{user_id or 'anon'}:{route}"
    lim, remaining = _LIMITER.check(key, limit=limit)
    if response is not None:
        response.headers["X-RateLimit-Limit"] = str(lim)
        response.headers["X-RateLimit-Remaining"] = str(remaining)


def reset_rate_limiter_for_tests() -> None:
    with _LIMITER._lock:
        _LIMITER._hits.clear()


def validate_date_range(
    date_from: date | None,
    date_to: date | None,
    *,
    max_days: int | None = None,
) -> None:
    max_days = int(max_days if max_days is not None else settings.lottery_nr_max_range_days)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="La fecha inicial no puede ser posterior a la fecha final.",
        )
    if date_from and date_to:
        span = (date_to - date_from).days
        if span > max_days:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El rango de fechas excede el máximo permitido ({max_days} días). "
                    f"Rango solicitado: {span} días."
                ),
            )
    # Si solo hay un extremo, acotar contra "hoy" / extremo opuesto implícito
    today = date.today()
    if date_from and not date_to:
        if (today - date_from).days > max_days:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"date_from está demasiado atrás sin date_to "
                    f"(máximo {max_days} días hasta hoy)."
                ),
            )
    if date_to and not date_from:
        # open start — exigir from para cargas históricas grandes
        raise HTTPException(
            status_code=400,
            detail="Debe indicar date_from cuando envía date_to (rango histórico acotado).",
        )


def validate_lottery_id_count(ids: list[Any], *, field: str = "lottery_ids") -> None:
    max_n = int(settings.lottery_nr_max_lotteries_per_request)
    uniq = {str(x) for x in ids if x is not None}
    if len(uniq) > max_n:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Demasiadas loterías en {field}: {len(uniq)} "
                f"(máximo {max_n}; universo activo FEATURED_SEVEN)."
            ),
        )


def validate_numbers_list(numbers: list[int] | None, *, field: str = "numbers") -> None:
    if not numbers:
        return
    max_n = int(settings.lottery_nr_max_numbers_list)
    if len(numbers) > max_n:
        raise HTTPException(
            status_code=400,
            detail=f"Demasiados números en {field}: {len(numbers)} (máximo {max_n}).",
        )
    for n in numbers:
        if not isinstance(n, int) or n < 1 or n > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Número inválido en {field}: {n}. Debe estar entre 1 y 100.",
            )


def validate_page_size(page_size: int | None) -> int:
    max_ps = int(settings.lottery_nr_max_page_size)
    default = int(settings.lottery_nr_default_page_size)
    ps = default if page_size is None else int(page_size)
    if ps < 1:
        raise HTTPException(status_code=400, detail="page_size debe ser ≥ 1.")
    if ps > max_ps:
        raise HTTPException(
            status_code=400,
            detail=f"page_size excede el máximo ({max_ps}).",
        )
    return ps


def validate_nr_body_bounds(body: Any) -> None:
    """Aplica bounds comunes a bodies NR con scope / fechas / listas."""
    date_from = getattr(body, "date_from", None)
    date_to = getattr(body, "date_to", None)
    validate_date_range(date_from, date_to)

    scope = getattr(body, "scope", None)
    if scope is not None:
        primary = list(getattr(scope, "primary_lottery_ids", None) or [])
        confirming = list(getattr(scope, "confirming_lottery_ids", None) or [])
        follow = list(getattr(scope, "follow_up_lottery_ids", None) or [])
        validate_lottery_id_count(primary + confirming + follow, field="scope")

    for field in ("candidates", "confirmers", "confirmers_watch", "strengthened_candidates", "confirmer_watch"):
        validate_numbers_list(getattr(body, field, None), field=field)

    if hasattr(body, "page_size"):
        validate_page_size(getattr(body, "page_size", None))

    follow_ids = getattr(body, "follow_up_lottery_ids", None)
    if follow_ids is not None:
        validate_lottery_id_count(list(follow_ids), field="follow_up_lottery_ids")
