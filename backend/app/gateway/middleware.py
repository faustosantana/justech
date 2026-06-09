import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.tenant import TENANT_HEADER, set_tenant_context


class GatewayMiddleware(BaseHTTPMiddleware):
    """Application-level gateway: request ID, timing, tenant propagation."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()

        tenant_header = request.headers.get(TENANT_HEADER)
        if tenant_header:
            try:
                set_tenant_context(tenant_id=uuid.UUID(tenant_header))
            except ValueError:
                pass

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response
