"""Aislamiento de API para rol lottery_client."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import verify_access_token
from app.services.lottery_permissions import (
    LOTTERY_CLIENT_ALLOWED_API_PREFIXES,
    LOTTERY_CLIENT_ROLE,
)


def path_allowed_for_lottery_client(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in LOTTERY_CLIENT_ALLOWED_API_PREFIXES)


class LotteryClientIsolationMiddleware(BaseHTTPMiddleware):
    """Bloquea APIs no autorizadas para usuarios con rol lottery_client."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = verify_access_token(auth[7:])
            role = (payload or {}).get("role")
            if role == LOTTERY_CLIENT_ROLE and path.startswith("/api/"):
                if not path_allowed_for_lottery_client(path):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Rol Lottery Client: acceso restringido al módulo Resultados de Loterías",
                        },
                    )
        return await call_next(request)
