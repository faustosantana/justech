from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.config import settings
from integrations.dgcp.client import DGCPClient
from integrations.dgcp.config import DGCPConfig
from integrations.n8n import N8nClient
from integrations.microsoft365 import M365Client
from integrations.microsoft365.config import M365Config
from integrations.odoo import OdooClient

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/status")
async def integrations_status(_: CurrentUser, __: TenantCtx) -> dict:
    """Health check for integration connectors (no business logic)."""
    ctx = require_tenant_context()
    return {
        "tenant_id": str(ctx.tenant_id),
        "integrations": {
            "odoo": OdooClient.health(),
            "n8n": N8nClient.health(),
            "dgcp": {"base_url": settings.dgcp_api_base_url_resolved},
            "m365": await M365Client(
                M365Config(
                    tenant_id=settings.m365_tenant_id,
                    client_id=settings.m365_client_id,
                    client_secret=settings.m365_client_secret,
                    redirect_uri=settings.m365_redirect_uri,
                    read_only=settings.m365_read_only,
                )
            ).health(),
        },
    }


@router.post("/odoo/test-connection")
async def test_odoo_connection(db: DbSession, _: CurrentUser, __: TenantCtx) -> dict:
    ctx = require_tenant_context()
    client = OdooClient(tenant_id=str(ctx.tenant_id))
    return await client.test_connection()


@router.post("/n8n/trigger/{workflow_id}")
async def trigger_n8n_workflow(workflow_id: str, _: CurrentUser, __: TenantCtx) -> dict:
    ctx = require_tenant_context()
    client = N8nClient(tenant_id=str(ctx.tenant_id))
    return await client.trigger_workflow(workflow_id, payload={})


@router.get("/dgcp/health")
async def dgcp_health(_: CurrentUser, __: TenantCtx) -> dict:
    client = DGCPClient(
        DGCPConfig(
            base_url=settings.dgcp_api_base_url_resolved,
            api_key=settings.dgcp_api_key,
        )
    )
    return await client.health_check()
