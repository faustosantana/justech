"""DGCP API DGCP — consumo real de Compras Públicas RD."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from integrations.dgcp.config import DGCPConfig
from integrations.dgcp.schemas import DGCPPaginatedResponse, DGCPProcesoRecord


class DGCPClient:
    def __init__(self, config: DGCPConfig | None = None):
        self.config = config or DGCPConfig()
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def _throttle(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            min_interval = 60.0 / self.config.rate_limit_per_minute
            elapsed = now - self._last_request
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request = asyncio.get_event_loop().time()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        await self._throttle()
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.config.api_key:
            headers["X-API-KEY"] = self.config.api_key
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                raise RuntimeError(
                    f"DGCP API returned non-JSON ({content_type}) from {url}. "
                    f"Check DGCP_API_BASE_URL includes /api-dgcp/v1"
                )
            data = response.json()
        if data.get("hasError"):
            raise RuntimeError(f"DGCP API error: {data}")
        return data

    async def fetch_procesos(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        estado_proceso: str | None = "Proceso publicado",
        objeto_proceso: str | None = None,
    ) -> DGCPPaginatedResponse:
        params: dict[str, Any] = {"page": page, "limit": limit}
        if estado_proceso:
            params["estado_proceso"] = estado_proceso
        if objeto_proceso:
            params["objeto_proceso"] = objeto_proceso
        data = await self._get("procesos", params)
        payload = data.get("payload", {})
        content = [DGCPProcesoRecord.from_api(item) for item in payload.get("content", [])]
        return DGCPPaginatedResponse(
            content=content,
            page=data.get("page", page),
            limit=data.get("limit", limit),
            total_results=data.get("totalResults", 0),
            pages=data.get("pages", 0),
        )

    async def health_check(self) -> dict[str, Any]:
        try:
            result = await self.fetch_procesos(page=1, limit=1)
            return {
                "reachable": True,
                "total_procesos": result.total_results,
                "base_url": self.config.base_url,
            }
        except Exception as exc:
            return {"reachable": False, "error": str(exc), "base_url": self.config.base_url}
