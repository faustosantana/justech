"""n8n REST API client stub — Phase 1 architecture only."""

from typing import Any

import httpx

from app.config import settings
from integrations.n8n.config import N8nConfig


class N8nClient:
    def __init__(self, tenant_id: str, config: N8nConfig | None = None):
        self.tenant_id = tenant_id
        self.config = config or N8nConfig(
            base_url=settings.n8n_webhook_url,
            api_key=settings.n8n_api_key,
        )

    @staticmethod
    def health() -> dict[str, str]:
        return {"status": "ready", "connector": "n8n", "version": "0.1.0"}

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-N8N-API-KEY"] = self.config.api_key
        return headers

    async def trigger_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/webhook/{workflow_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"tenant_id": self.tenant_id, **payload},
                headers=self._headers(),
            )
            return {
                "workflow_id": workflow_id,
                "status_code": response.status_code,
                "triggered": response.is_success,
            }

    async def list_workflows(self) -> list[dict]:
        """Placeholder — requires n8n API key with full access."""
        raise NotImplementedError("n8n workflow management is Phase 2+")
